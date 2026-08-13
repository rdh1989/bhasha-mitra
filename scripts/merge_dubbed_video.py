"""
===============================================================================
BHASHA MITRA
Merge Dubbed Video (standalone utility)
===============================================================================

Description:
    Merges a dubbed audio track (and optionally a subtitle file) onto the
    original source video and writes the final video to a specified
    location, using the same FFmpeg-based VideoExporter used by the
    application's export stage.

Usage:
    python scripts/merge_dubbed_video.py ^
        --video "input.mp4" ^
        --audio "dubbed_audio.wav" ^
        --output "dubbed_video.mp4" ^
        [--subtitle "subtitle.srt"]
===============================================================================
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from infrastructure.media.video_exporter import VideoExporter  # noqa: E402


def _resolve_ffmpeg_executable() -> Path:
    """
    Resolve the ffmpeg executable using the same manifest configuration
    the application uses (config/manifest.json -> "ffmpeg.path").
    """

    manifest_path = PROJECT_ROOT / "config" / "manifest.json"

    if not manifest_path.is_file():
        raise FileNotFoundError(
            f"Manifest file not found: {manifest_path}"
        )

    manifest = json.loads(
        manifest_path.read_text(encoding="utf-8")
    )

    ffmpeg_config = manifest.get("ffmpeg")

    if not isinstance(ffmpeg_config, dict) or not ffmpeg_config.get("path"):
        raise RuntimeError(
            "FFmpeg path is not configured in config/manifest.json."
        )

    ffmpeg_directory = Path(ffmpeg_config["path"]).expanduser()

    if not ffmpeg_directory.is_absolute():
        ffmpeg_directory = (PROJECT_ROOT / ffmpeg_directory).resolve()

    return ffmpeg_directory / "ffmpeg.exe"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Merge dubbed audio (and optional subtitles) onto a video."
        )
    )

    parser.add_argument(
        "--video",
        required=True,
        type=Path,
        help="Path to the original source video.",
    )

    parser.add_argument(
        "--audio",
        required=True,
        type=Path,
        help="Path to the dubbed audio file (e.g. dubbed_audio.wav).",
    )

    parser.add_argument(
        "--output",
        required=True,
        type=Path,
        help="Path to write the final dubbed video (.mp4).",
    )

    parser.add_argument(
        "--subtitle",
        type=Path,
        default=None,
        help="Optional subtitle file to embed as a subtitle stream.",
    )

    return parser.parse_args()


def main() -> None:
    args = parse_args()

    ffmpeg_executable = _resolve_ffmpeg_executable()

    exporter = VideoExporter(
        ffmpeg_path=ffmpeg_executable,
    )

    output_video = exporter.export(
        input_video=args.video,
        dubbed_audio=args.audio,
        subtitle_file=args.subtitle,
        output_video=args.output,
    )

    print(f"Dubbed video saved to: {output_video}")


if __name__ == "__main__":
    main()
