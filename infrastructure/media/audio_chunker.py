"""
Audio chunking utility.

Splits audio into 15-minute chunks using configured FFmpeg.
"""

from __future__ import annotations

import logging
import subprocess
from pathlib import Path


logger = logging.getLogger(__name__)


class AudioChunkingError(RuntimeError):
    """Raised when audio chunking fails."""


class AudioChunker:
    """
    Splits audio into 15-minute chunks when required.
    """

    CHUNK_SECONDS = 15 * 60

    def __init__(
        self,
        ffmpeg_path: Path,
    ) -> None:
        self._ffmpeg = ffmpeg_path

    def chunk(
        self,
        audio_file: Path,
        output_directory: Path,
    ) -> list[Path]:
        """
        Return audio chunks.

        If audio is 15 minutes or shorter, the original file
        is returned.

        If longer, FFmpeg creates 15-minute chunks.
        """

        if not audio_file.is_file():
            raise FileNotFoundError(
                f"Audio file not found: {audio_file}"
            )

        output_directory.mkdir(
            parents=True,
            exist_ok=True,
        )

        duration = self._get_duration(
            audio_file
        )

        if duration <= self.CHUNK_SECONDS:
            return [audio_file]

        pattern = (
            output_directory
            / "audio_chunk_%03d.wav"
        )

        command = [
            str(self._ffmpeg),
            "-y",
            "-i",
            str(audio_file),
            "-f",
            "segment",
            "-segment_time",
            str(self.CHUNK_SECONDS),
            "-reset_timestamps",
            "1",
            "-ac",
            "1",
            "-ar",
            "16000",
            "-c:a",
            "pcm_s16le",
            str(pattern),
        ]

        logger.info(
            "Splitting audio into 15-minute chunks | audio=%s",
            audio_file,
        )

        try:

            result = subprocess.run(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                check=False,
            )

        except OSError as exc:

            raise AudioChunkingError(
                "Unable to execute FFmpeg."
            ) from exc

        if result.returncode != 0:

            logger.error(
                "Audio chunking failed | error=%s",
                result.stderr[-2000:],
            )

            raise AudioChunkingError(
                "FFmpeg audio chunking failed."
            )

        chunks = sorted(
            output_directory.glob(
                "audio_chunk_*.wav"
            )
        )

        if not chunks:
            raise AudioChunkingError(
                "FFmpeg completed but no audio chunks were created."
            )

        logger.info(
            "Audio chunking completed | chunks=%s",
            len(chunks),
        )

        return chunks

    def _get_duration(
        self,
        audio_file: Path,
    ) -> float:
        """
        Get audio duration in seconds using FFmpeg.
        """

        command = [
            str(self._ffmpeg),
            "-i",
            str(audio_file),
        ]

        try:

            result = subprocess.run(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                check=False,
            )

        except OSError as exc:

            raise AudioChunkingError(
                "Unable to execute FFmpeg."
            ) from exc

        duration = self._parse_duration(
            result.stderr
        )

        if duration is None:
            raise AudioChunkingError(
                "Unable to determine audio duration."
            )

        return duration

    @staticmethod
    def _parse_duration(
        output: str,
    ) -> float | None:
        """
        Parse FFmpeg duration output.
        """

        import re

        match = re.search(
            r"Duration:\s*(\d{2}):(\d{2}):(\d{2}(?:\.\d+)?)",
            output,
        )

        if match is None:
            return None

        hours = int(match.group(1))
        minutes = int(match.group(2))
        seconds = float(match.group(3))

        return (
            hours * 3600
            + minutes * 60
            + seconds
        )