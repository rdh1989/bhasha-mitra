"""
===============================================================================
BHASHA MITRA
===============================================================================

Module:
    audio_extractor.py

Layer:
    Infrastructure / Media

Description:
    Extracts audio from uploaded video files using the configured FFmpeg
    runtime.

Responsibilities:
    - Resolve FFmpeg from configuration
    - Extract audio for a translation job
    - Store the generated audio on disk
    - Return the generated audio path

FFmpeg is an external bundled runtime and must not be hardcoded.

===============================================================================
"""

from __future__ import annotations

import logging
import subprocess
from pathlib import Path

from infrastructure.filesystem.path_manager import (
    PathManager,
)

logger = logging.getLogger(__name__)


class AudioExtractionError(RuntimeError):
    """
    Raised when audio extraction fails.
    """


class AudioExtractor:
    """
    Extracts audio from video using FFmpeg.
    """

    def __init__(
        self,
        ffmpeg_path: Path,
        path_manager: PathManager,
    ) -> None:

        self._ffmpeg = ffmpeg_path
        self._paths = path_manager

        if not self._ffmpeg.is_file():

            raise FileNotFoundError(
                f"FFmpeg executable not found: "
                f"{self._ffmpeg}"
            )

    def extract(
        self,
        input_file: Path,
        video_name: str,
        job_id: str,
    ) -> Path:
        """
        Extract audio from a video file.

        Returns:
            Path to the extracted WAV file.
        """

        if not input_file.is_file():

            raise FileNotFoundError(
                f"Input video not found: "
                f"{input_file}"
            )

        audio_file = self._paths.audio_path(
            video_name,
            job_id,
        )

        command = [
            str(self._ffmpeg),
            "-y",
            "-i",
            str(input_file),
            "-vn",
            "-ac",
            "1",
            "-ar",
            "16000",
            "-c:a",
            "pcm_s16le",
            str(audio_file),
        ]

        logger.info(
            "Starting audio extraction | "
            "job_id=%s | input=%s",
            job_id,
            input_file,
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

            logger.exception(
                "Unable to execute FFmpeg | job_id=%s",
                job_id,
            )

            raise AudioExtractionError(
                "Unable to execute FFmpeg."
            ) from exc

        if result.returncode != 0:

            logger.error(
                "FFmpeg audio extraction failed | "
                "job_id=%s | return_code=%s | error=%s",
                job_id,
                result.returncode,
                result.stderr[-2000:],
            )

            raise AudioExtractionError(
                f"FFmpeg audio extraction failed "
                f"with exit code {result.returncode}."
            )

        if not audio_file.is_file():

            raise AudioExtractionError(
                "FFmpeg completed but the extracted audio "
                "file was not created."
            )

        logger.info(
            "Audio extraction completed | "
            "job_id=%s | audio=%s",
            job_id,
            audio_file,
        )

        return audio_file