"""
FFmpeg implementation of the Video Provider.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

from app.providers.video.base_video_provider import (
    BaseVideoProvider,
)


class FFmpegVideoProvider(BaseVideoProvider):
    """
    Video processing implementation using FFmpeg.
    """

    def extract_audio(
        self,
        video_file: Path,
        output_audio: Path,
    ) -> Path:
        """
        Extract audio from a video.

        Output:
            WAV PCM 16kHz Mono
        """

        command = [
            "ffmpeg",
            "-y",
            "-i",
            str(video_file),
            "-vn",
            "-ac",
            "1",
            "-ar",
            "16000",
            "-acodec",
            "pcm_s16le",
            str(output_audio),
        ]

        subprocess.run(
            command,
            check=True,
            capture_output=True,
        )

        return output_audio

    def merge_audio(
        self,
        video_file: Path,
        audio_file: Path,
        output_video: Path,
    ) -> Path:
        """
        Replace original audio with translated audio.
        """

        command = [
            "ffmpeg",
            "-y",
            "-i",
            str(video_file),
            "-i",
            str(audio_file),
            "-map",
            "0:v:0",
            "-map",
            "1:a:0",
            "-c:v",
            "copy",
            "-shortest",
            str(output_video),
        ]

        subprocess.run(
            command,
            check=True,
            capture_output=True,
        )

        return output_video

    def add_subtitles(
        self,
        video_file: Path,
        subtitle_file: Path,
        output_video: Path,
    ) -> Path:
        """
        Burn subtitles into video.
        """

        command = [
            "ffmpeg",
            "-y",
            "-i",
            str(video_file),
            "-vf",
            f"subtitles={subtitle_file}",
            str(output_video),
        ]

        subprocess.run(
            command,
            check=True,
            capture_output=True,
        )

        return output_video