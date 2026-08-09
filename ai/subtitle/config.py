"""
===============================================================================
Bhasha Mitra - AI Framework
-------------------------------------------------------------------------------
Module      : config.py
Purpose     : Subtitle Configuration

Description:
    Provider/format-independent configuration for subtitle generation.

    Subtitle formats are resolved through configuration. The service does not
    contain format-specific logic.

Author:
    Bhasha Mitra AI Team

Version:
    1.0
===============================================================================
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import yaml


@dataclass(slots=True)
class SubtitleFormatConfig:
    """
    Configuration for one subtitle format.
    """

    enabled: bool = True

    implementation: str = ""


@dataclass(slots=True)
class SubtitleConfig:
    """
    Framework-level subtitle configuration.
    """

    # ------------------------------------------------------------------
    # Default format
    # ------------------------------------------------------------------

    default_format: str = ""

    # ------------------------------------------------------------------
    # Output
    # ------------------------------------------------------------------

    encoding: str = "utf-8"

    overwrite_existing: bool = True

    # ------------------------------------------------------------------
    # Timestamp
    # ------------------------------------------------------------------

    include_timestamps: bool = True

    timestamp_precision: int = 3

    # ------------------------------------------------------------------
    # Text formatting
    # ------------------------------------------------------------------

    max_characters_per_line: int = 42

    max_lines_per_subtitle: int = 2

    preserve_line_breaks: bool = True

    # ------------------------------------------------------------------
    # Formats
    # ------------------------------------------------------------------

    formats: dict[str, SubtitleFormatConfig] = field(
        default_factory=dict
    )

    # ------------------------------------------------------------------
    # Runtime
    # ------------------------------------------------------------------

    verbose: bool = False

    @classmethod
    def from_yaml(cls, path: Path) -> "SubtitleConfig":
        """Load the subtitle section from the provider configuration file."""

        with path.open("r", encoding="utf-8") as config_file:
            document = yaml.safe_load(config_file) or {}

        subtitle = document.get("subtitle")
        if not isinstance(subtitle, dict):
            raise ValueError(
                f"Subtitle configuration is missing from '{path}'."
            )

        default_format = subtitle.get("default_format")
        formats = subtitle.get("formats")

        if not isinstance(default_format, str) or not default_format.strip():
            raise ValueError("Subtitle 'default_format' must be a non-empty string.")

        if not isinstance(formats, dict) or not formats:
            raise ValueError("Subtitle 'formats' must be a non-empty mapping.")

        parsed_formats: dict[str, SubtitleFormatConfig] = {}
        for format_name, format_settings in formats.items():
            if not isinstance(format_name, str) or not isinstance(format_settings, dict):
                raise ValueError("Each subtitle format must have a mapping configuration.")

            implementation = format_settings.get("implementation")
            if not isinstance(implementation, str):
                raise ValueError(
                    f"Subtitle format '{format_name}' must define an implementation."
                )

            parsed_formats[format_name.strip().lower()] = SubtitleFormatConfig(
                enabled=bool(format_settings.get("enabled", True)),
                implementation=implementation.strip(),
            )

        return cls(
            default_format=default_format.strip().lower(),
            encoding=str(subtitle.get("encoding", "utf-8")),
            overwrite_existing=bool(subtitle.get("overwrite_existing", True)),
            include_timestamps=bool(subtitle.get("include_timestamps", True)),
            timestamp_precision=int(subtitle.get("timestamp_precision", 3)),
            max_characters_per_line=int(
                subtitle.get("max_characters_per_line", 42)
            ),
            max_lines_per_subtitle=int(subtitle.get("max_lines_per_subtitle", 2)),
            preserve_line_breaks=bool(subtitle.get("preserve_line_breaks", True)),
            formats=parsed_formats,
            verbose=bool(subtitle.get("verbose", False)),
        )
