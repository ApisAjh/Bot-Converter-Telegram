"""
Helper untuk mengelola file temporary selama proses konversi.

Setiap job konversi mendapat sub-folder unik di dalam TEMP_DIR, dan folder
tersebut (beserta seluruh isinya) SELALU dihapus begitu proses selesai —
baik berhasil maupun gagal — lewat context manager `temp_job_dir()`.
"""
from __future__ import annotations

import shutil
import uuid
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from app.config import TEMP_DIR


@contextmanager
def temp_job_dir() -> Iterator[Path]:
    """Membuat folder temporary unik untuk satu job konversi, lalu
    menghapusnya otomatis (recursive) setelah selesai dipakai."""
    job_dir = TEMP_DIR / uuid.uuid4().hex
    job_dir.mkdir(parents=True, exist_ok=True)
    try:
        yield job_dir
    finally:
        shutil.rmtree(job_dir, ignore_errors=True)


def cleanup_dir(path: Path) -> None:
    """Hapus folder/file secara paksa, tanpa melempar error jika tidak ada."""
    if path.is_dir():
        shutil.rmtree(path, ignore_errors=True)
    elif path.exists():
        path.unlink(missing_ok=True)


def has_valid_extension(filename: str, allowed: list[str]) -> bool:
    ext = Path(filename).suffix.lower()
    return ext in allowed


def human_size(num_bytes: int) -> str:
    size = float(num_bytes)
    for unit in ("B", "KB", "MB", "GB"):
        if size < 1024:
            return f"{size:.1f}{unit}"
        size /= 1024
    return f"{size:.1f}TB"
