"""ffmpeg-backed media helpers (audio extraction, time-stretch, muxing).

Prefers the full ffmpeg build under models/third_party/ffmpeg (see
app/config.py's FFMPEG_EXE) over the older binary bundled by imageio-ffmpeg,
falling back to imageio-ffmpeg automatically if that folder isn't present -
either way no system-wide ffmpeg install is required.
"""
from __future__ import annotations

import logging
import subprocess

from app.config import FFMPEG_EXE as _CONFIGURED_FFMPEG_EXE

logger = logging.getLogger(__name__)

if _CONFIGURED_FFMPEG_EXE:
    FFMPEG_EXE = _CONFIGURED_FFMPEG_EXE
    logger.info("Using ffmpeg from %s", FFMPEG_EXE)
else:
    import imageio_ffmpeg

    FFMPEG_EXE = imageio_ffmpeg.get_ffmpeg_exe()
    logger.info("models/third_party/ffmpeg not found - using imageio-ffmpeg's bundled ffmpeg from %s", FFMPEG_EXE)


def _run(args: list[str]) -> None:
    logger.debug("Running ffmpeg %s", " ".join(args))
    try:
        proc = subprocess.run(
            [FFMPEG_EXE, "-y", "-hide_banner", "-loglevel", "error", *args],
            capture_output=True,
            text=True,
        )
    except OSError as exc:
        logger.exception("Failed to launch ffmpeg")
        raise RuntimeError(f"Could not launch ffmpeg: {exc}") from exc
    if proc.returncode != 0:
        logger.error("ffmpeg failed (exit %d): %s\n%s", proc.returncode, " ".join(args), proc.stderr)
        raise RuntimeError(f"ffmpeg failed: {' '.join(args)}\n{proc.stderr}")


def extract_audio(video_path: str, audio_out_path: str, sample_rate: int = 16000) -> None:
    _run(["-i", video_path, "-vn", "-ac", "1", "-ar", str(sample_rate), audio_out_path])


def _atempo_chain(factor: float) -> str:
    """ffmpeg's atempo filter only accepts [0.5, 2.0]; chain multiple stages
    for factors outside that range."""
    if factor <= 0:
        factor = 1.0
    stages = []
    remaining = factor
    while remaining < 0.5 or remaining > 2.0:
        stage = 2.0 if remaining > 2.0 else 0.5
        stages.append(stage)
        remaining /= stage
    stages.append(remaining)
    return ",".join(f"atempo={s:.6f}" for s in stages)


def time_stretch_audio(in_path: str, out_path: str, speed_factor: float) -> None:
    """speed_factor > 1 speeds audio up (shortens it); < 1 slows it down."""
    speed_factor = max(0.3, min(3.0, speed_factor))
    _run(["-i", in_path, "-filter:a", _atempo_chain(speed_factor), out_path])


def mux_video_with_audio(video_path: str, audio_path: str, out_path: str, subtitle_path: str | None = None) -> None:
    inputs = ["-i", video_path, "-i", audio_path]
    maps = ["-map", "0:v:0", "-map", "1:a:0"]
    codecs = ["-c:v", "copy", "-c:a", "aac", "-b:a", "192k"]
    if subtitle_path:
        # Embedded as a soft (selectable) subtitle track - no video re-encode
        # needed, so muxing stays fast and lossless for the picture.
        inputs += ["-i", subtitle_path]
        maps += ["-map", "2:s:0"]
        codecs += ["-c:s", "mov_text"]
    _run([*inputs, *maps, *codecs, "-shortest", out_path])
