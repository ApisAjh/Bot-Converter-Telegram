"""
Entry point FastAPI untuk Vercel Serverless Function (webhook-only, no polling).

Vercel akan meng-import module ini dan memanggil object `app` (ASGI) untuk
setiap request. Application python-telegram-bot dibuat sekali di level
module supaya bisa dipakai ulang selama function instance masih "warm"
(baca README bagian "Batasan Serverless & ConversationHandler" untuk
penjelasan kenapa ini penting).
"""
from __future__ import annotations

import logging
import sys
from pathlib import Path

# Supaya `import app.xxx` bekerja saat Vercel menjalankan file ini langsung.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fastapi import FastAPI, Request, Response, HTTPException
from telegram import Update
from telegram.ext import (
    Application,
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ConversationHandler,
    filters,
)

from app.config import BOT_TOKEN, WEBHOOK_SECRET
from app.handlers.start import start_command, cancel_command
from app.handlers.menu import category_selected, action_selected, back_to_categories
from app.handlers.conversation import file_received, param_received, finish_multi_file
from app.handlers.states import (
    CHOOSING_CATEGORY,
    CHOOSING_ACTION,
    WAITING_FILE,
    WAITING_MORE_FILES,
    WAITING_PARAM,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("filebot")

if not BOT_TOKEN:
    logger.warning("BOT_TOKEN belum di-set! Set environment variable BOT_TOKEN.")

# ── Bangun PTB Application (dipakai ulang antar-request selama warm) ────────
telegram_app: Application = ApplicationBuilder().token(BOT_TOKEN or "invalid-token").build()

_INCOMING_FILE_FILTER = filters.Document.ALL | filters.PHOTO | filters.VIDEO | filters.AUDIO | filters.VOICE

conversation_handler = ConversationHandler(
    entry_points=[CommandHandler("start", start_command)],
    states={
        CHOOSING_CATEGORY: [
            CallbackQueryHandler(category_selected, pattern=r"^cat:"),
        ],
        CHOOSING_ACTION: [
            CallbackQueryHandler(action_selected, pattern=r"^act:"),
            CallbackQueryHandler(back_to_categories, pattern=r"^back:categories$"),
        ],
        WAITING_FILE: [
            MessageHandler(_INCOMING_FILE_FILTER, file_received),
        ],
        WAITING_MORE_FILES: [
            CommandHandler("selesai", finish_multi_file),
            MessageHandler(_INCOMING_FILE_FILTER, file_received),
        ],
        WAITING_PARAM: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, param_received),
        ],
    },
    fallbacks=[CommandHandler("cancel", cancel_command), CommandHandler("start", start_command)],
    per_user=True,
    per_chat=True,
    name="filebot_conversation",
)

telegram_app.add_handler(conversation_handler)
telegram_app.add_handler(CommandHandler("cancel", cancel_command))


async def _global_error_handler(update: object, context) -> None:
    logger.exception("Unhandled error saat memproses update", exc_info=context.error)


telegram_app.add_error_handler(_global_error_handler)

# ── FastAPI app ───────────────────────────────────────────────────────────
app = FastAPI(title="Telegram File Converter Bot")

_initialized = False


async def _ensure_initialized() -> None:
    global _initialized
    if not _initialized:
        await telegram_app.initialize()
        _initialized = True


@app.get("/")
@app.get("/api/webhook")
async def health_check() -> dict:
    return {"status": "ok", "service": "telegram-file-converter-bot"}


@app.post("/api/webhook")
async def telegram_webhook(request: Request) -> Response:
    if WEBHOOK_SECRET:
        header_secret = request.headers.get("X-Telegram-Bot-Api-Secret-Token")
        if header_secret != WEBHOOK_SECRET:
            raise HTTPException(status_code=401, detail="Invalid secret token")

    await _ensure_initialized()

    data = await request.json()
    update = Update.de_json(data, telegram_app.bot)
    await telegram_app.process_update(update)

    return Response(status_code=200)
