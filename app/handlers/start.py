"""Handler untuk perintah /start dan tampilan menu kategori utama."""
from __future__ import annotations

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes

from app.config import CATEGORIES

WELCOME_TEXT = (
    "👋 *Selamat datang di File Converter Bot!*\n\n"
    "Saya bisa mengonversi berbagai jenis file langsung di Telegram:\n"
    "PDF, Image, Video, Audio, dan Document.\n\n"
    "Pilih kategori converter di bawah ini untuk mulai 👇"
)


def main_menu_keyboard() -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton(label, callback_data=f"cat:{key}")]
        for key, label in CATEGORIES.items()
    ]
    return InlineKeyboardMarkup(buttons)


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    # Reset state percakapan sebelumnya (kalau ada) supaya alur selalu bersih.
    context.user_data.clear()
    await update.message.reply_text(
        WELCOME_TEXT,
        parse_mode="Markdown",
        reply_markup=main_menu_keyboard(),
    )


async def cancel_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    context.user_data.clear()
    await update.message.reply_text(
        "❌ Proses dibatalkan. Ketik /start untuk mulai lagi.",
    )
