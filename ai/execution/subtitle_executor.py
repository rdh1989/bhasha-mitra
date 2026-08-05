"""
===============================================================================
Bhasha Mitra - AI Framework
-------------------------------------------------------------------------------
Module      : subtitle_executor.py
Purpose     : Subtitle Execution Engine

Description
-----------
Generates subtitle files from ASR results.

Responsibilities
----------------
• Convert ASR segments into subtitle format
• Generate SRT/VTT files
• Return framework response

Author:
    Bhasha Mitra AI Team

Version:
    1.0
===============================================================================
"""

from __future__ import annotations

from pathlib import Path

from ai.asr.models import ASRResult
from ai.subtitle.models import (
    SubtitleRequest,
    SubtitleResult,
)


class SubtitleExecutor:
    """
    Executes subtitle generation.
    """

    def generate(
        self,
        request: SubtitleRequest,
    ) -> SubtitleResult:
        """
        Generate subtitle file.
        """

        output_path = Path(request.output_path)

        if request.subtitle_format.lower() == "srt":
            self._write_srt(
                request.transcription,
                output_path,
            )
        else:
            raise NotImplementedError(
                f"Subtitle format '{request.subtitle_format}' "
                "is not supported."
            )

        return SubtitleResult(
            subtitle_path=output_path,
            subtitle_format=request.subtitle_format,
            segment_count=len(request.transcription.segments),
        )

    # -------------------------------------------------------------------------
    # SRT
    # -------------------------------------------------------------------------

    def _write_srt(
        self,
        transcription: ASRResult,
        output_path: Path,
    ) -> None:
        """
        Write SRT subtitle file.
        """

        with output_path.open(
            "w",
            encoding="utf-8",
        ) as file:

            for index, segment in enumerate(
                transcription.segments,
                start=1,
            ):

                file.write(f"{index}\n")

                file.write(
                    f"{self._format_time(segment.start)} --> "
                    f"{self._format_time(segment.end)}\n"
                )

                file.write(f"{segment.text.strip()}\n\n")

    # -------------------------------------------------------------------------
    # Helpers
    # -------------------------------------------------------------------------

    @staticmethod
    def _format_time(
        seconds: float,
    ) -> str:
        """
        Convert seconds to SRT timestamp.
        """

        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        millis = int((seconds - int(seconds)) * 1000)

        return (
            f"{hours:02}:{minutes:02}:{secs:02},{millis:03}"
        )