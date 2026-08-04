"""
Piper Text-to-Speech Provider.

Offline speech synthesis using Piper.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

from app.providers.tts.base_tts_provider import (
    BaseTTSProvider,
)


class PiperTTSProvider(BaseTTSProvider):
    """
    Offline Text-to-Speech implementation using Piper.
    """

    def __init__(
        self,
        executable: Path,
        model: Path,
        config: Path,
    ) -> None:
        self._executable = executable
        self._model = model
        self._config = config

    def synthesize(
        self,
        text: str,
        language: str,
        output_file: Path,
    ) -> Path:
        """
        Generate speech audio.

        Args:
            text:
                Text to synthesize.

            language:
                ISO language code (reserved for future
                multi-model support).

            output_file:
                Destination WAV file.

        Returns:
            Generated audio file.
        """

        output_file.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        process = subprocess.run(
            [
                str(self._executable),
                "--model",
                str(self._model),
                "--config",
                str(self._config),
                "--output_file",
                str(output_file),
            ],
            input=text.encode("utf-8"),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True,
        )

        return output_file

    def available(self) -> bool:
        """
        Verify Piper executable exists.
        """

        return self._executable.exists()