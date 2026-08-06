"""Converter Audio: MP3<->WAV, OGG->MP3, Trim — via ffmpeg subprocess async."""
from __future__ import annotations

import asyncio
from pathlib import Path

from app.converters.video import FFmpegError  # reuse exception & subprocess pattern


async def _run_ffmpeg(args: list[str]) -> None:
    process = await asyncio.create_subprocess_exec(
        "ffmpeg", "-y", *args,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    _, stderr = await process.communicate()
    if process.returncode != 0:
        raise FFmpegError(stderr.decode(errors="ignore")[-1500:])


async def convert_audio(input_path: Path, output_path: Path) -> None:
    await _run_ffmpeg(["-i", str(input_path), str(output_path)])


async def trim_audio(input_path: Path, output_path: Path, start_sec: float, end_sec: float) -> None:
    duration = end_sec - start_sec
    if duration <= 0:
        raise ValueError("Waktu selesai harus lebih besar dari waktu mulai.")
    await _run_ffmpeg([
        "-i", str(input_path),
        "-ss", str(start_sec), "-t", str(duration),
        str(output_path),
    ])
