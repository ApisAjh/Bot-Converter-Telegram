"""
Konfigurasi utama bot.
Semua nilai sensitif diambil dari environment variable (.env saat lokal,
Vercel Project Settings > Environment Variables saat production).
"""
import os
from pathlib import Path

# ── Kredensial & endpoint ────────────────────────────────────────────────
BOT_TOKEN: str = os.getenv("BOT_TOKEN", "")
WEBHOOK_SECRET: str = os.getenv("WEBHOOK_SECRET", "")  # untuk header X-Telegram-Bot-Api-Secret-Token
WEBHOOK_URL: str = os.getenv("WEBHOOK_URL", "")  # contoh: https://namaproject.vercel.app/api/webhook

# ── Batasan file ──────────────────────────────────────────────────────────
# Bisa diubah lewat env var MAX_FILE_SIZE_MB. Ingat: Telegram Bot API biasa
# hanya bisa MENGUNDUH file hingga 20MB, dan Vercel serverless function
# punya limit ukuran payload/waktu eksekusi sendiri (lihat README).
MAX_FILE_SIZE_MB: int = int(os.getenv("MAX_FILE_SIZE_MB", "20"))
MAX_FILE_SIZE_BYTES: int = MAX_FILE_SIZE_MB * 1024 * 1024

# ── Direktori temporary ────────────────────────────────────────────────────
# Vercel serverless function hanya boleh menulis ke /tmp. Di lingkungan lokal
# kita pakai folder temp/ di root project supaya mudah diperiksa saat debug.
IS_VERCEL: bool = os.getenv("VERCEL") == "1"
if IS_VERCEL:
    TEMP_DIR = Path("/tmp/filebot_temp")
else:
    TEMP_DIR = Path(__file__).resolve().parent.parent / "temp"
TEMP_DIR.mkdir(parents=True, exist_ok=True)

# ── Metadata converter ─────────────────────────────────────────────────────
# key = action_id (dipakai sebagai callback_data & routing di conversation handler)
# category   : kategori menu (pdf/image/video/audio/document)
# label      : label tombol
# extensions : ekstensi file input yang diterima (untuk validasi)
# multi_file : True jika aksi butuh >1 file input sebelum diproses (mis. merge pdf)
# needs_param: True jika aksi butuh input teks tambahan setelah file dikirim
# param_hint : teks instruksi untuk parameter tambahan
ACTIONS: dict[str, dict] = {
    # ── PDF ──
    "pdf_word2pdf": {"category": "pdf", "label": "📄 Word → PDF", "extensions": [".docx"]},
    "pdf_image2pdf": {"category": "pdf", "label": "🖼 Image → PDF", "extensions": [".jpg", ".jpeg", ".png", ".webp"]},
    "pdf_pdf2image": {"category": "pdf", "label": "📄 PDF → Image", "extensions": [".pdf"]},
    "pdf_merge": {"category": "pdf", "label": "🔗 Merge PDF", "extensions": [".pdf"], "multi_file": True},
    "pdf_split": {
        "category": "pdf", "label": "✂️ Split PDF", "extensions": [".pdf"],
        "needs_param": True,
        "param_hint": "Kirim nomor halaman yang ingin dipisah (contoh: 1,3,5-7).\nAtau ketik `all` untuk memisah setiap halaman menjadi file sendiri.",
    },
    "pdf_compress": {"category": "pdf", "label": "🗜 Compress PDF", "extensions": [".pdf"]},
    # ── IMAGE ──
    "img_jpg2png": {"category": "image", "label": "JPG → PNG", "extensions": [".jpg", ".jpeg"]},
    "img_png2jpg": {"category": "image", "label": "PNG → JPG", "extensions": [".png"]},
    "img_png2webp": {"category": "image", "label": "PNG → WEBP", "extensions": [".png"]},
    "img_webp2png": {"category": "image", "label": "WEBP → PNG", "extensions": [".webp"]},
    "img_webp2jpg": {"category": "image", "label": "WEBP → JPG", "extensions": [".webp"]},
    "img_jpg2webp": {"category": "image", "label": "JPG → WEBP", "extensions": [".jpg", ".jpeg"]},
    "img_resize": {
        "category": "image", "label": "📐 Resize", "extensions": [".jpg", ".jpeg", ".png", ".webp"],
        "needs_param": True, "param_hint": "Kirim ukuran baru dalam format `lebar x tinggi`, contoh: `800x600`.",
    },
    "img_compress": {"category": "image", "label": "🗜 Compress", "extensions": [".jpg", ".jpeg", ".png", ".webp"]},
    # ── VIDEO ──
    "vid_mp42avi": {"category": "video", "label": "MP4 → AVI", "extensions": [".mp4"]},
    "vid_avi2mp4": {"category": "video", "label": "AVI → MP4", "extensions": [".avi"]},
    "vid_mp42gif": {"category": "video", "label": "MP4 → GIF", "extensions": [".mp4"]},
    "vid_compress": {"category": "video", "label": "🗜 Compress Video", "extensions": [".mp4", ".avi", ".mov", ".mkv"]},
    "vid_extract_audio": {"category": "video", "label": "🎵 Extract Audio", "extensions": [".mp4", ".avi", ".mov", ".mkv"]},
    # ── AUDIO ──
    "aud_mp32wav": {"category": "audio", "label": "MP3 → WAV", "extensions": [".mp3"]},
    "aud_wav2mp3": {"category": "audio", "label": "WAV → MP3", "extensions": [".wav"]},
    "aud_ogg2mp3": {"category": "audio", "label": "OGG → MP3", "extensions": [".ogg", ".oga"]},
    "aud_trim": {
        "category": "audio", "label": "✂️ Trim Audio", "extensions": [".mp3", ".wav", ".ogg", ".oga"],
        "needs_param": True, "param_hint": "Kirim rentang waktu dalam detik, format `mulai-selesai`, contoh: `10-30`.",
    },
    # ── DOCUMENT ──
    "doc_docx2pdf": {"category": "document", "label": "DOCX → PDF", "extensions": [".docx"]},
    "doc_xlsx2pdf": {"category": "document", "label": "XLSX → PDF", "extensions": [".xlsx"]},
    "doc_pptx2pdf": {"category": "document", "label": "PPTX → PDF", "extensions": [".pptx"]},
    "doc_txt2pdf": {"category": "document", "label": "TXT → PDF", "extensions": [".txt"]},
}

CATEGORIES: dict[str, str] = {
    "pdf": "📄 PDF",
    "image": "🖼 Image",
    "video": "🎥 Video",
    "audio": "🎵 Audio",
    "document": "📁 Document",
}
