"""
Module:
    video_exporter.py

Layer:
    Infrastructure / Media

Description:
    Creates the final translated video by combining the original video,
    dubbed audio, and generated subtitles using FFmpeg.

Responsibilities:
    - Validate input media files
    - Validate FFmpeg
    - Execute FFmpeg
    - Generate the final translated video
    - Return the generated output path

The exporter does not:
    - Perform translation
    - Perform subtitle generation
    - Perform dubbing
    - Manage TranslationJob state
    - Decide the application output directory
    - Use a fallback output directory
"""

from __future__ import annotations

import logging
import os
import subprocess
from pathlib import Path

logger = logging.getLogger(__name__)


class VideoExporter:
    """
    Creates the final translated video using FFmpeg.
    """

    def __init__(
        self,
        ffmpeg_path: Path,
    ) -> None:

        self._ffmpeg_path = (
            Path(ffmpeg_path)
            .expanduser()
            .resolve()
        )

    def export(
        self,
        input_video: Path,
        dubbed_audio: Path,
        output_video: Path,
        subtitle_file: Path | None = None,
    ) -> Path:
        """
        Create the final translated video.

        The original video is retained as the video stream.
        Dubbed audio replaces the original audio.
        Subtitle file is embedded as a subtitle stream when provided.

        The caller is responsible for supplying the configured
        output path.
        """

        input_video = Path(
            input_video
        ).expanduser()

        dubbed_audio = Path(
            dubbed_audio
        ).expanduser()

        subtitle_file = (
            Path(subtitle_file).expanduser()
            if subtitle_file is not None
            else None
        )

        output_video = Path(
            output_video
        ).expanduser()

        # =====================================================================
        # Validate input files
        # =====================================================================

        self._validate_file(
            input_video,
            "Input video",
        )

        self._validate_file(
            dubbed_audio,
            "Dubbed audio",
        )

        if subtitle_file is not None:

            self._validate_file(
                subtitle_file,
                "Subtitle file",
            )

        # =====================================================================
        # Validate FFmpeg
        # =====================================================================

        if not self._ffmpeg_path.is_file():

            raise FileNotFoundError(
                "FFmpeg executable not found: "
                f"{self._ffmpeg_path}"
            )

        # =====================================================================
        # Validate output location
        # =====================================================================

        self._validate_output_location(
            output_video
        )

        # =====================================================================
        # FFmpeg command
        # =====================================================================

        command = [
            str(self._ffmpeg_path),

            "-y",

            # Original video
            "-i",
            str(input_video),

            # Dubbed audio
            "-i",
            str(dubbed_audio),
        ]

        if subtitle_file is not None:

            command += [
                "-i",
                str(subtitle_file),
            ]

        command += [
            # Video stream
            "-map",
            "0:v:0",

            # Dubbed audio stream
            "-map",
            "1:a:0",
        ]

        if subtitle_file is not None:

            command += [
                # Subtitle stream
                "-map",
                "2:0",
            ]

        command += [
            # Preserve original video encoding
            "-c:v",
            "copy",

            # Encode dubbed audio
            "-c:a",
            "aac",
        ]

        if subtitle_file is not None:

            command += [
                # MP4 subtitle format
                "-c:s",
                "mov_text",
            ]

        command += [
            # Stop when the shortest stream ends
            "-shortest",

            str(output_video),
        ]


        logger.info(
            "Starting video export | "
            "input=%s | output=%s",
            input_video,
            output_video,
        )

        try:

            result = subprocess.run(
                command,
                check=True,
                capture_output=True,
                text=True,
            )

        except FileNotFoundError as exc:

            logger.exception(
                "FFmpeg executable could not be started."
            )

            raise RuntimeError(
                "Unable to start FFmpeg."
            ) from exc

        except subprocess.CalledProcessError as exc:

            logger.error(
                "FFmpeg video export failed | "
                "return_code=%s | stderr=%s",
                exc.returncode,
                exc.stderr,
            )

            raise RuntimeError(
                "Video export failed."
            ) from exc

        if result.stderr:

            logger.debug(
                "FFmpeg output | %s",
                result.stderr,
            )

        # =====================================================================
        # Validate generated video
        # =====================================================================

        if not output_video.is_file():

            raise RuntimeError(
                "FFmpeg completed but output video "
                "was not created."
            )

        if output_video.stat().st_size == 0:

            raise RuntimeError(
                "FFmpeg created an empty output video."
            )

        logger.info(
            "Video export completed | output=%s",
            output_video,
        )

        return output_video

    @staticmethod
    def _validate_file(
        file_path: Path,
        description: str,
    ) -> None:
        """
        Validate that an input file exists and is readable.
        """

        if not file_path.is_file():

            raise FileNotFoundError(
                f"{description} not found: "
                f"{file_path}"
            )

        if not os.access(
            file_path,
            os.R_OK,
        ):

            raise PermissionError(
                f"{description} is not readable: "
                f"{file_path}"
            )

    @staticmethod
    def _validate_output_location(
        output_video: Path,
    ) -> None:
        """
        Validate the supplied output location.

        The exporter never chooses another location if this one
        is unavailable.
        """

        if output_video.suffix.lower() != ".mp4":

            raise ValueError(
                "Translated video output must be an MP4 file."
            )

        parent = output_video.parent

        if not parent.exists():

            raise FileNotFoundError(
                "Configured output directory does not exist: "
                f"{parent}"
            )

        if not parent.is_dir():

            raise RuntimeError(
                "Configured output path is not a directory: "
                f"{parent}"
            )

        if not os.access(
            parent,
            os.W_OK,
        ):

            raise PermissionError(
                "Configured output directory is not writable: "
                f"{parent}"
            )