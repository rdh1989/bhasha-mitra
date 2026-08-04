"""
SRT Subtitle Provider.

Generates standard SubRip (.srt) subtitle files.
"""

from __future__ import annotations

from datetime import timedelta
from pathlib import Path

from app.providers.subtitle.base_subtitle_provider import (
    BaseSubtitleProvider,
)


class SRTSubtitleProvider(BaseSubtitleProvider):
    """
    Subtitle provider for generating SRT files.
    """

    def generate(
        self,
        text: str,
        output_file: Path,
    ) -> Path:
        """
        Generate a simple subtitle file.

        NOTE
        ----
        This implementation creates a single subtitle block.

        Timestamp-aware subtitles should use ASR segment
        timestamps in a future implementation.
        """

        output_file.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        content = "\n".join(
            [
                "1",
                f"{self._format_time(0)} --> {self._format_time(3600)}",
                text.strip(),
                "",
            ]
        )

        output_file.write_text(
            content,
            encoding="utf-8",
        )

        return output_file

    def generate_segments(
        self,
        segments: list[dict],
        output_file: Path,
    ) -> Path:
        """
        Generate subtitles using timestamped ASR segments.

        Expected segment format:

        [
            {
                "start":0.0,
                "end":2.4,
                "text":"Hello"
            }
        ]
        """

        output_file.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        lines: list[str] = []

        for index, segment in enumerate(
            segments,
            start=1,
        ):
            lines.extend(
                [
                    str(index),
                    (
                        f"{self._format_time(segment['start'])}"
                        " --> "
                        f"{self._format_time(segment['end'])}"
                    ),
                    segment["text"].strip(),
                    "",
                ]
            )

        output_file.write_text(
            "\n".join(lines),
            encoding="utf-8",
        )

        return output_file

    @staticmethod
    def _format_time(
        seconds: float,
    ) -> str:
        """
        Convert seconds into SRT timestamp.

        Example:
            00:01:12,350
        """

        duration = timedelta(seconds=seconds)

        total_seconds = int(duration.total_seconds())

        milliseconds = int(
            (duration.total_seconds() - total_seconds)
            * 1000
        )

        hours = total_seconds // 3600

        minutes = (
            total_seconds % 3600
        ) // 60

        secs = total_seconds % 60

        return (
            f"{hours:02d}:"
            f"{minutes:02d}:"
            f"{secs:02d},"
            f"{milliseconds:03d}"
        )