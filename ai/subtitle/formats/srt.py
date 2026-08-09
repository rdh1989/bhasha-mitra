"""SubRip (SRT) subtitle formatter."""

from __future__ import annotations

from ai.subtitle.config import SubtitleConfig
from ai.subtitle.models import SubtitleRequest, SubtitleResult
from ai.subtitle.utils import seconds_to_srt_time


class SRTFormatter:
    """Write timestamped subtitle segments in the SRT format."""

    def __init__(self, config: SubtitleConfig) -> None:
        self._config = config

    def generate(self, request: SubtitleRequest) -> SubtitleResult:
        output_path = request.output_path
        output_path.parent.mkdir(parents=True, exist_ok=True)

        if output_path.exists() and not self._config.overwrite_existing:
            raise FileExistsError(
                f"Subtitle output already exists: '{output_path}'."
            )

        with output_path.open(
            "w",
            encoding=self._config.encoding,
            newline="\n",
        ) as subtitle_file:
            for index, segment in enumerate(request.segments, start=1):
                subtitle_file.write(f"{index}\n")
                subtitle_file.write(
                    f"{seconds_to_srt_time(segment.start)} --> "
                    f"{seconds_to_srt_time(segment.end)}\n"
                )
                subtitle_file.write(f"{segment.text.strip()}\n\n")

        return SubtitleResult(
            subtitle_path=output_path,
            subtitle_format="srt",
            segment_count=len(request.segments),
        )
