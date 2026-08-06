"""
Handler inti alur percakapan converter:
menerima file -> (opsional minta parameter) -> konversi -> kirim hasil ->
hapus file temporary.

Menggunakan ConversationHandler (per_user=True, per_chat=True secara default)
supaya alur setiap pengguna terisolasi satu sama lain.
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

from telegram import Update, InputFile
from telegram.ext import ContextTypes, ConversationHandler

from app.config import ACTIONS, MAX_FILE_SIZE_BYTES, MAX_FILE_SIZE_MB, TEMP_DIR
from app.handlers.states import WAITING_FILE, WAITING_MORE_FILES, WAITING_PARAM, CHOOSING_CATEGORY
from app.utils.file_utils import has_valid_extension, cleanup_dir, human_size

from app.converters import pdf as pdf_conv
from app.converters import image as image_conv
from app.converters import video as video_conv
from app.converters import audio as audio_conv
from app.converters import document as document_conv

logger = logging.getLogger(__name__)


# ── Helper: ambil file dari message apapun jenisnya ─────────────────────────
def _get_incoming_file(message):
    """Mengembalikan (telegram_file_obj, nama_file_default) dari message,
    mendukung document, photo, video, audio, dan voice note."""
    if message.document:
        return message.document, message.document.file_name or "file"
    if message.photo:
        photo = message.photo[-1]
        return photo, "photo.jpg"
    if message.video:
        return message.video, message.video.file_name or "video.mp4"
    if message.audio:
        return message.audio, message.audio.file_name or "audio.mp3"
    if message.voice:
        return message.voice, "voice.ogg"
    return None, None


def _job_dir(context: ContextTypes.DEFAULT_TYPE) -> Path:
    path_str = context.user_data.get("job_dir")
    if path_str is None:
        import uuid
        job_dir = TEMP_DIR / uuid.uuid4().hex
        job_dir.mkdir(parents=True, exist_ok=True)
        context.user_data["job_dir"] = str(job_dir)
        return job_dir
    return Path(path_str)


async def _end_and_cleanup(context: ContextTypes.DEFAULT_TYPE) -> None:
    job_dir = context.user_data.get("job_dir")
    if job_dir:
        cleanup_dir(Path(job_dir))
    context.user_data.clear()


# ── Menerima file (state WAITING_FILE / WAITING_MORE_FILES) ─────────────────
async def file_received(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    message = update.message
    action_id = context.user_data.get("action")
    meta = ACTIONS.get(action_id or "")
    if meta is None:
        await message.reply_text("⚠️ Sesi tidak valid. Ketik /start untuk mengulang.")
        await _end_and_cleanup(context)
        return ConversationHandler.END

    tg_file_obj, filename = _get_incoming_file(message)
    if tg_file_obj is None:
        await message.reply_text("⚠️ Saya tidak mengenali jenis file itu. Kirim sebagai dokumen/foto/video/audio ya.")
        return WAITING_MORE_FILES if meta.get("multi_file") else WAITING_FILE

    if not has_valid_extension(filename, meta["extensions"]):
        ext_hint = ", ".join(meta["extensions"])
        await message.reply_text(f"⚠️ Format tidak didukung untuk *{meta['label']}*.\nKirim salah satu: {ext_hint}", parse_mode="Markdown")
        return WAITING_MORE_FILES if meta.get("multi_file") else WAITING_FILE

    file_size = getattr(tg_file_obj, "file_size", None)
    if file_size and file_size > MAX_FILE_SIZE_BYTES:
        await message.reply_text(f"⚠️ File terlalu besar. Maksimum {MAX_FILE_SIZE_MB}MB.")
        return WAITING_MORE_FILES if meta.get("multi_file") else WAITING_FILE

    job_dir = _job_dir(context)
    files_so_far = context.user_data.setdefault("files", [])
    dest_path = job_dir / f"{len(files_so_far)}_{Path(filename).name}"

    try:
        tg_file = await tg_file_obj.get_file()
        await tg_file.download_to_drive(custom_path=str(dest_path))
    except Exception:
        logger.exception("Gagal mengunduh file dari Telegram")
        await message.reply_text("⚠️ Gagal mengunduh file. Coba kirim ulang.")
        return WAITING_MORE_FILES if meta.get("multi_file") else WAITING_FILE

    files_so_far.append(str(dest_path))

    if meta.get("multi_file"):
        await message.reply_text(
            f"✅ File diterima ({len(files_so_far)} file terkumpul).\n"
            "Kirim file lain, atau ketik /selesai untuk memproses."
        )
        return WAITING_MORE_FILES

    if meta.get("needs_param"):
        await message.reply_text(meta["param_hint"], parse_mode="Markdown")
        return WAITING_PARAM

    return await _run_and_finish(update, context)


# ── /selesai untuk aksi multi-file (mis. merge PDF) ─────────────────────────
async def finish_multi_file(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    action_id = context.user_data.get("action")
    meta = ACTIONS.get(action_id or "")
    files = context.user_data.get("files", [])
    if meta is None:
        await update.message.reply_text("⚠️ Sesi tidak valid. Ketik /start untuk mengulang.")
        await _end_and_cleanup(context)
        return ConversationHandler.END
    if len(files) < 2:
        await update.message.reply_text("⚠️ Minimal kirim 2 file sebelum /selesai.")
        return WAITING_MORE_FILES
    return await _run_and_finish(update, context)


# ── Menerima parameter tambahan (state WAITING_PARAM) ────────────────────────
async def param_received(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["param"] = update.message.text.strip()
    return await _run_and_finish(update, context)


# ── Dispatcher konversi ───────────────────────────────────────────────────
async def _dispatch_conversion(action_id: str, input_paths: list[Path], job_dir: Path, param: Optional[str]) -> list[Path]:
    """Menjalankan converter yang sesuai dan mengembalikan list path hasil."""
    single = input_paths[0] if input_paths else None

    if action_id == "pdf_word2pdf":
        out = job_dir / "hasil.pdf"
        pdf_conv.word_to_pdf(single, out)
        return [out]
    if action_id == "pdf_image2pdf":
        out = job_dir / "hasil.pdf"
        pdf_conv.image_to_pdf(input_paths, out)
        return [out]
    if action_id == "pdf_pdf2image":
        return pdf_conv.pdf_to_images(single, job_dir)
    if action_id == "pdf_merge":
        out = job_dir / "merged.pdf"
        pdf_conv.merge_pdfs(input_paths, out)
        return [out]
    if action_id == "pdf_split":
        return pdf_conv.split_pdf(single, job_dir, param or "all")
    if action_id == "pdf_compress":
        out = job_dir / "compressed.pdf"
        pdf_conv.compress_pdf(single, out)
        return [out]

    if action_id == "img_jpg2png":
        out = job_dir / "hasil.png"; image_conv.convert_format(single, out); return [out]
    if action_id == "img_png2jpg":
        out = job_dir / "hasil.jpg"; image_conv.convert_format(single, out); return [out]
    if action_id == "img_png2webp":
        out = job_dir / "hasil.webp"; image_conv.convert_format(single, out); return [out]
    if action_id == "img_webp2png":
        out = job_dir / "hasil.png"; image_conv.convert_format(single, out); return [out]
    if action_id == "img_webp2jpg":
        out = job_dir / "hasil.jpg"; image_conv.convert_format(single, out); return [out]
    if action_id == "img_jpg2webp":
        out = job_dir / "hasil.webp"; image_conv.convert_format(single, out); return [out]
    if action_id == "img_resize":
        w, h = _parse_dimensions(param or "")
        out = job_dir / f"resized{single.suffix}"
        image_conv.resize_image(single, out, w, h)
        return [out]
    if action_id == "img_compress":
        out = job_dir / f"compressed{single.suffix}"
        image_conv.compress_image(single, out)
        return [out]

    if action_id == "vid_mp42avi":
        out = job_dir / "hasil.avi"; await video_conv.convert_container(single, out); return [out]
    if action_id == "vid_avi2mp4":
        out = job_dir / "hasil.mp4"; await video_conv.convert_container(single, out); return [out]
    if action_id == "vid_mp42gif":
        out = job_dir / "hasil.gif"; await video_conv.mp4_to_gif(single, out); return [out]
    if action_id == "vid_compress":
        out = job_dir / f"compressed{single.suffix}"; await video_conv.compress_video(single, out); return [out]
    if action_id == "vid_extract_audio":
        out = job_dir / "audio.mp3"; await video_conv.extract_audio(single, out); return [out]

    if action_id == "aud_mp32wav":
        out = job_dir / "hasil.wav"; await audio_conv.convert_audio(single, out); return [out]
    if action_id == "aud_wav2mp3":
        out = job_dir / "hasil.mp3"; await audio_conv.convert_audio(single, out); return [out]
    if action_id == "aud_ogg2mp3":
        out = job_dir / "hasil.mp3"; await audio_conv.convert_audio(single, out); return [out]
    if action_id == "aud_trim":
        start, end = _parse_range(param or "")
        out = job_dir / f"trimmed{single.suffix}"
        await audio_conv.trim_audio(single, out, start, end)
        return [out]

    if action_id == "doc_docx2pdf":
        out = job_dir / "hasil.pdf"; document_conv.docx_to_pdf(single, out); return [out]
    if action_id == "doc_xlsx2pdf":
        out = job_dir / "hasil.pdf"; document_conv.xlsx_to_pdf(single, out); return [out]
    if action_id == "doc_pptx2pdf":
        out = job_dir / "hasil.pdf"; document_conv.pptx_to_pdf(single, out); return [out]
    if action_id == "doc_txt2pdf":
        out = job_dir / "hasil.pdf"; document_conv.txt_to_pdf(single, out); return [out]

    raise ValueError(f"Aksi tidak dikenali: {action_id}")


def _parse_dimensions(param: str) -> tuple[int, int]:
    try:
        w_str, h_str = param.lower().replace(" ", "").split("x")
        return int(w_str), int(h_str)
    except Exception as exc:
        raise ValueError("Format ukuran salah. Gunakan contoh: `800x600`.") from exc


def _parse_range(param: str) -> tuple[float, float]:
    try:
        start_str, end_str = param.replace(" ", "").split("-")
        return float(start_str), float(end_str)
    except Exception as exc:
        raise ValueError("Format rentang waktu salah. Gunakan contoh: `10-30`.") from exc


# ── Eksekusi konversi + kirim hasil + cleanup ────────────────────────────────
async def _run_and_finish(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    chat_id = update.effective_chat.id
    action_id = context.user_data.get("action")
    meta = ACTIONS.get(action_id or "", {})
    job_dir = _job_dir(context)
    input_paths = [Path(p) for p in context.user_data.get("files", [])]
    param = context.user_data.get("param")

    status_msg = await context.bot.send_message(chat_id, "⏳ Sedang memproses...")
    await context.bot.send_chat_action(chat_id, action="upload_document")

    try:
        output_paths = await _dispatch_conversion(action_id, input_paths, job_dir, param)
        if not output_paths:
            raise ValueError("Konversi tidak menghasilkan file apa pun.")

        for out_path in output_paths:
            with open(out_path, "rb") as f:
                await context.bot.send_document(
                    chat_id=chat_id,
                    document=InputFile(f, filename=out_path.name),
                    caption=f"✅ {meta.get('label', 'Hasil konversi')} — {human_size(out_path.stat().st_size)}",
                )
        await status_msg.delete()
    except Exception as exc:
        logger.exception("Konversi gagal untuk aksi %s", action_id)
        await status_msg.edit_text(f"❌ Konversi gagal: {exc}\n\nKetik /start untuk mencoba lagi.")
    finally:
        await _end_and_cleanup(context)

    return ConversationHandler.END
