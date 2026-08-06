"""Converter Image: format conversion, resize, compress — memakai Pillow."""
from __future__ import annotations

from pathlib import Path
from PIL import Image

_FORMAT_MAP = {
    ".jpg": "JPEG",
    ".jpeg": "JPEG",
    ".png": "PNG",
    ".webp": "WEBP",
}


def convert_format(input_path: Path, output_path: Path) -> None:
    target_ext = output_path.suffix.lower()
    fmt = _FORMAT_MAP.get(target_ext)
    if fmt is None:
        raise ValueError(f"Format tujuan tidak didukung: {target_ext}")
    img = Image.open(input_path)
    if fmt == "JPEG" and img.mode in ("RGBA", "P"):
        img = img.convert("RGB")
    img.save(output_path, fmt)


def resize_image(input_path: Path, output_path: Path, width: int, height: int) -> None:
    img = Image.open(input_path)
    resized = img.resize((width, height), Image.LANCZOS)
    resized.save(output_path)


def compress_image(input_path: Path, output_path: Path, quality: int = 60) -> None:
    img = Image.open(input_path)
    ext = input_path.suffix.lower()
    if ext in (".jpg", ".jpeg"):
        if img.mode in ("RGBA", "P"):
            img = img.convert("RGB")
        img.save(output_path, "JPEG", quality=quality, optimize=True)
    elif ext == ".png":
        img.save(output_path, "PNG", optimize=True)
    elif ext == ".webp":
        img.save(output_path, "WEBP", quality=quality)
    else:
        img.save(output_path)
