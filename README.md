# Telegram File Converter Bot

Bot Telegram untuk konversi file (PDF, Image, Video, Audio, Document) —
Python 3.12, python-telegram-bot v22+, FastAPI, **webhook only**, **tanpa
database**. Siap deploy ke Vercel.

## Struktur Project

```
api/
    webhook.py          # entry point FastAPI + wiring PTB Application
app/
    handlers/
        start.py         # /start, menu utama
        menu.py           # navigasi kategori -> aksi
        conversation.py   # terima file/param, jalankan converter, kirim hasil
        states.py         # state ConversationHandler
    converters/
        pdf.py
        image.py
        video.py
        audio.py
        document.py
    utils/
        file_utils.py     # kelola folder temp, cleanup otomatis
    config.py             # env vars, batasan file, registry aksi converter
temp/                    # dipakai hanya untuk dev lokal (lihat catatan di bawah)
requirements.txt
vercel.json
.env.example
```

## Menjalankan secara lokal

```bash
python3.12 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

cp .env.example .env
# isi BOT_TOKEN, dst.

uvicorn api.webhook:app --reload --port 8000
```

Untuk testing lokal tanpa domain publik, gunakan tunnel (ngrok/cloudflared)
lalu `setWebhook` ke URL tunnel tersebut (lihat langkah di bawah).

## Deploy ke Vercel

1. Push project ini ke repo GitHub/GitLab/Bitbucket.
2. Import repo di [vercel.com](https://vercel.com/new).
3. Di **Project Settings → Environment Variables**, isi:
   - `BOT_TOKEN`
   - `WEBHOOK_URL` (contoh: `https://nama-project.vercel.app/api/webhook`)
   - `WEBHOOK_SECRET` (opsional, disarankan)
   - `MAX_FILE_SIZE_MB` (opsional)
4. Deploy.
5. Set webhook Telegram ke URL Vercel kamu:

```bash
curl -X POST "https://api.telegram.org/bot<BOT_TOKEN>/setWebhook" \
  -H "Content-Type: application/json" \
  -d '{
        "url": "https://nama-project.vercel.app/api/webhook",
        "secret_token": "isi-sama-dengan-WEBHOOK_SECRET-kalau-dipakai"
      }'
```

6. Cek status webhook:

```bash
curl "https://api.telegram.org/bot<BOT_TOKEN>/getWebhookInfo"
```

## Alur Pemakaian

1. `/start` → tampil menu kategori (PDF/Image/Video/Audio/Document) via
   Inline Keyboard.
2. Pilih kategori → pilih jenis konversi.
3. Bot minta file (atau beberapa file untuk Merge PDF, diakhiri `/selesai`).
4. Untuk aksi yang butuh parameter (Resize, Trim, Split), bot minta input
   teks tambahan setelah file diterima.
5. Bot menampilkan indikator "⏳ Sedang memproses...", menjalankan converter,
   lalu mengirim balik file hasil.
6. Folder temporary job tersebut (dan seluruh isinya) langsung dihapus,
   baik saat sukses maupun gagal.
7. `/cancel` bisa dipakai kapan saja untuk membatalkan & membersihkan sesi.

## ⚠️ Batasan Penting (wajib dibaca sebelum production)

### 1. Video & Audio butuh binary `ffmpeg`
Vercel Serverless Function **tidak menyediakan `ffmpeg` secara default**.
Semua fitur di `converters/video.py` dan `converters/audio.py` memanggil
`ffmpeg` lewat subprocess dan hanya akan berjalan jika binary tersebut
tersedia di `PATH` runtime. Untuk produksi, pertimbangkan:
- Menjalankan bot ini di platform yang mendukung custom binary/Docker
  (Railway, Fly.io, Render, VPS biasa), **atau**
- Membundel static binary ffmpeg ke dalam deployment Vercel (kompleks dan
  gampang melebihi limit ukuran function 250MB unzipped Vercel).

### 2. `PDF → Image` pakai `pypdfium2`, bukan `pdf2image`/poppler
`pdf2image` butuh binary sistem `poppler-utils` yang juga tidak tersedia di
Vercel. Implementasi aktual memakai `pypdfium2` (pure-pip, sudah termasuk
binary PDFium) supaya tetap jalan di serverless. `pdf2image` tetap ada di
`requirements.txt` sesuai spesifikasi, namun tidak dipakai langsung oleh
kode inti.

### 3. Konversi Word/Excel/PPTX → PDF tidak memakai LibreOffice
Tanpa LibreOffice (tidak tersedia di Vercel), konversi dilakukan dengan
mengekstrak teks/tabel/slide lalu merender ulang PDF baru memakai
`reportlab`. Ini cocok untuk isi berbasis teks & tabel sederhana, tapi
**tidak mereplikasi 1:1** desain/layout asli (gambar, styling kompleks,
tema slide, dsb).

### 4. Statelessness Vercel & `ConversationHandler`
Vercel Serverless Function pada dasarnya *stateless* antar-invocation.
`ConversationHandler` di kode ini menyimpan state percakapan di memori
(`context.user_data`), yang hanya bertahan selama *function instance*
masih "warm" (dipakai ulang oleh Vercel untuk request berturut-turut dalam
waktu singkat). Jika terjadi *cold start* di tengah alur (misalnya user
diam cukup lama sebelum mengirim file), state bisa hilang dan bot akan
meminta user mengulang dari `/start`. Ini adalah trade-off yang disengaja
untuk memenuhi syarat "tanpa database apa pun" — bukan bug.

### 5. Limit ukuran & durasi Vercel
- Bot API standar hanya bisa **mengunduh file hingga 20MB**.
- Vercel Serverless Function (plan Hobby) punya limit durasi eksekusi
  (default 10 detik, bisa dikonfigurasi hingga 60 detik) — konversi video
  yang berat sangat mungkin timeout. Sesuaikan `MAX_FILE_SIZE_MB` di
  `.env`/Vercel dashboard sesuai kebutuhan, dan pertimbangkan plan Pro atau
  platform lain untuk beban video besar.

### 6. Folder `temp/`
Vercel hanya mengizinkan tulis ke `/tmp`. Kode otomatis mendeteksi environment
(`VERCEL=1`, di-set otomatis oleh Vercel) dan memakai `/tmp/filebot_temp`
saat production, atau folder `temp/` di root project saat dijalankan lokal.
Setiap job konversi mendapat sub-folder unik yang **selalu dihapus** setelah
selesai diproses (sukses maupun gagal).

## Menambah converter baru

1. Tambahkan fungsi konversinya di `app/converters/<kategori>.py`.
2. Daftarkan aksi baru di `ACTIONS` pada `app/config.py` (label, ekstensi
   yang diterima, apakah butuh multi-file/parameter tambahan).
3. Tambahkan cabang baru di `_dispatch_conversion()` pada
   `app/handlers/conversation.py`.
