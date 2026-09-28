"""Configured FFmpeg-backed media helpers."""
from __future__ import annotations

import logging
import json
import subprocess
from dataclasses import dataclass
from pathlib import Path

from app.config import FFMPEG_EXE as _CONFIGURED_FFMPEG_EXE
from app.config import FFPROBE_EXE as _CONFIGURED_FFPROBE_EXE
from app.config import FFMPEG_RUNTIME_DIR as _CONFIGURED_FFMPEG_RUNTIME_DIR
from app.config import FFMPEG_RUNTIME_ENABLED as _CONFIGURED_FFMPEG_RUNTIME_ENABLED
from app.config import FFPLAY_EXE as _CONFIGURED_FFPLAY_EXE

logger = logging.getLogger(__name__)

FFMPEG_EXE = _CONFIGURED_FFMPEG_EXE
FFPROBE_EXE = _CONFIGURED_FFPROBE_EXE
FFPLAY_EXE = _CONFIGURED_FFPLAY_EXE
logger.info("Configured FFmpeg runtime: %s", _CONFIGURED_FFMPEG_RUNTIME_DIR)


@dataclass(frozen=True)
class MediaProbe:
    format_name: str | None
    duration: float | None
    audio_streams: tuple[dict, ...]
    video_streams: tuple[dict, ...]

    @property
    def has_audio(self) -> bool:
        return bool(self.audio_streams)

    @property
    def has_video(self) -> bool:
        return bool(self.video_streams)


class MediaProbeError(RuntimeError):
    """A safe media inspection/normalization error for API and job handling."""


def _require_runtime_executable(executable: str | None, label: str) -> str:
    if label == "ffprobe" and not executable:
        raise MediaProbeError("FFprobe is unavailable in the configured FFmpeg runtime.")
    if not _CONFIGURED_FFMPEG_RUNTIME_ENABLED or not _CONFIGURED_FFMPEG_RUNTIME_DIR or not executable:
        raise MediaProbeError("FFmpeg runtime is unavailable or incorrectly configured.")
    if not Path(executable).is_file():
        if label == "ffprobe":
            raise MediaProbeError("FFprobe is unavailable in the configured FFmpeg runtime.")
        raise MediaProbeError("FFmpeg runtime is unavailable or incorrectly configured.")
    return executable


def probe_media(input_path: str | Path) -> MediaProbe:
    path = Path(input_path)
    if not path.is_file():
        raise MediaProbeError(f"Input media file does not exist: {path}")
    ffprobe = _require_runtime_executable(FFPROBE_EXE, "ffprobe")
    args = [
        ffprobe, "-v", "error", "-show_entries",
        "format=format_name,duration:stream=index,codec_type,codec_name,sample_rate,channels,duration",
        "-of", "json", str(path),
    ]
    try:
        proc = subprocess.run(args, capture_output=True, text=True)
    except OSError as exc:
        logger.exception("Failed to launch ffprobe for %s", path)
        raise MediaProbeError(f"Could not launch FFprobe: {exc}") from exc
    if proc.returncode != 0:
        logger.error("ffprobe failed for %s: %s", path, proc.stderr.strip())
        raise MediaProbeError("FFprobe could not identify the input media.")
    try:
        payload = json.loads(proc.stdout)
        streams = payload.get("streams", [])
        format_info = payload.get("format", {})
        audio = tuple(stream for stream in streams if stream.get("codec_type") == "audio")
        video = tuple(stream for stream in streams if stream.get("codec_type") == "video")
        duration = float(format_info["duration"]) if format_info.get("duration") else None
        return MediaProbe(
            format_name=format_info.get("format_name"), duration=duration,
            audio_streams=audio, video_streams=video,
        )
    except (ValueError, TypeError, KeyError, json.JSONDecodeError) as exc:
        logger.exception("Invalid ffprobe response for %s", path)
        raise MediaProbeError("FFprobe returned invalid media information.") from exc


def normalize_audio(input_path: str | Path, audio_out_path: str | Path, sample_rate: int = 16000) -> None:
    probe = probe_media(input_path)
    if not probe.has_audio:
        raise MediaProbeError("Input media does not contain an audio stream.")
    _run([
        "-i", str(input_path), "-map", "0:a:0", "-vn", "-ac", "1", "-ar", str(sample_rate),
        "-c:a", "pcm_s16le", "-f", "wav", str(audio_out_path),
    ])


def _run(args: list[str]) -> None:
    ffmpeg = _require_runtime_executable(FFMPEG_EXE, "ffmpeg")
    logger.debug("Running ffmpeg %s", " ".join(args))
    try:
        proc = subprocess.run(
            [ffmpeg, "-y", "-hide_banner", "-loglevel", "error", *args],
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
    normalize_audio(video_path, audio_out_path, sample_rate=sample_rate)


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
    codecs = ["-c:v", "libx264", "-c:a", "aac", "-b:a", "192k"]
    if subtitle_path:
        # Embedded as a soft (selectable) subtitle track - no video re-encode
        # needed, so muxing stays fast and lossless for the picture.
        inputs += ["-i", subtitle_path]
        maps += ["-map", "2:s:0"]
        codecs += ["-c:s", "mov_text"]
    _run([*inputs, *maps, *codecs, "-shortest", out_path])
