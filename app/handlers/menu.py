"""Handler untuk navigasi menu: pilih kategori -> pilih aksi -> minta file."""
from __future__ import annotations

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes

from app.config import ACTIONS, CATEGORIES
from app.handlers.states import CHOOSING_ACTION, WAITING_FILE, WAITING_MORE_FILES, CHOOSING_CATEGORY


def _actions_keyboard(category: str) -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton(meta["label"], callback_data=f"act:{key}")]
        for key, meta in ACTIONS.items()
        if meta["category"] == category
    ]
    buttons.append([InlineKeyboardButton("⬅️ Kembali", callback_data="back:categories")])
    return InlineKeyboardMarkup(buttons)


async def category_selected(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    category = query.data.split(":", 1)[1]
    context.user_data["category"] = category
    label = CATEGORIES.get(category, category)
    await query.edit_message_text(
        f"{label}\n\nPilih jenis konversi:",
        reply_markup=_actions_keyboard(category),
    )
    return CHOOSING_ACTION


async def back_to_categories(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    from app.handlers.start import WELCOME_TEXT, main_menu_keyboard

    query = update.callback_query
    await query.answer()
    context.user_data.clear()
    await query.edit_message_text(
        WELCOME_TEXT, parse_mode="Markdown", reply_markup=main_menu_keyboard()
    )
    return CHOOSING_CATEGORY


async def action_selected(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    action_id = query.data.split(":", 1)[1]
    meta = ACTIONS.get(action_id)
    if meta is None:
        await query.edit_message_text("⚠️ Aksi tidak dikenali. Ketik /start untuk mengulang.")
        return CHOOSING_CATEGORY

    context.user_data["action"] = action_id
    context.user_data["files"] = []
    ext_hint = ", ".join(meta["extensions"])

    if meta.get("multi_file"):
        text = (
            f"📎 *{meta['label']}*\n\n"
            f"Kirim file ({ext_hint}) satu per satu.\n"
            "Setelah selesai mengirim semua file, ketik /selesai untuk memproses, "
            "atau /cancel untuk membatalkan."
        )
        await query.edit_message_text(text, parse_mode="Markdown")
        return WAITING_MORE_FILES

    text = f"📎 *{meta['label']}*\n\nSilakan kirim file dengan format: {ext_hint}"
    await query.edit_message_text(text, parse_mode="Markdown")
    return WAITING_FILE
