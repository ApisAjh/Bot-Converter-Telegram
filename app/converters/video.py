"""
Converter Video: memanggil binary `ffmpeg` lewat subprocess asynchronous
(asyncio.create_subprocess_exec) supaya tidak memblok event loop bot.

PENTING (lihat README): Vercel serverless TIDAK menyediakan binary ffmpeg
secara default. Fitur di file ini hanya akan berfungsi jika ffmpeg
dibundel/tersedia di PATH runtime deployment (mis. lewat custom layer atau
platform lain yang mendukung binary tambahan).
"""
from __future__ import annotations

import asyncio
from pathlib import Path


class FFmpegError(Exception):
    pass


async def _run_ffmpeg(args: list[str]) -> None:
    process = await asyncio.create_subprocess_exec(
        "ffmpeg", "-y", *args,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    _, stderr = await process.communicate()
    if process.returncode != 0:
        raise FFmpegError(stderr.decode(errors="ignore")[-1500:])


async def convert_container(input_path: Path, output_path: Path) -> None:
    """Konversi antar container video (mis. MP4 <-> AVI) tanpa re-encode
    jika memungkinkan, fallback ke re-encode bila codec tidak kompatibel."""
    await _run_ffmpeg(["-i", str(input_path), "-c:v", "libx264", "-c:a", "aac", str(output_path)])


async def mp4_to_gif(input_path: Path, output_path: Path, fps: int = 10, width: int = 480) -> None:
    await _run_ffmpeg([
        "-i", str(input_path),
        "-vf", f"fps={fps},scale={width}:-1:flags=lanczos",
        str(output_path),
    ])


async def compress_video(input_path: Path, output_path: Path, crf: int = 28) -> None:
    await _run_ffmpeg([
        "-i", str(input_path),
        "-vcodec", "libx264", "-crf", str(crf), "-preset", "veryfast",
        "-acodec", "aac", "-b:a", "128k",
        str(output_path),
    ])


async def extract_audio(input_path: Path, output_path: Path) -> None:
    await _run_ffmpeg(["-i", str(input_path), "-vn", "-acodec", "mp3", str(output_path)])
