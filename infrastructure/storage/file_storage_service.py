"""
Local File Storage Service.

Concrete implementation of the StorageService interface using the
local filesystem.
"""

from __future__ import annotations

import shutil
import tempfile
from pathlib import Path

from app.application.interfaces.storage_service import StorageService
from infrastructure.filesystem.atomic_writer import AtomicWriter
from infrastructure.filesystem.path_manager import PathManager
from infrastructure.filesystem.safe_filename import SafeFilename


class FileStorageService(StorageService):
    """
    Local filesystem implementation of StorageService.
    """

    def __init__(
        self,
        path_manager: PathManager,
    ) -> None:
        self._paths = path_manager

    # ==========================================================
    # Upload
    # ==========================================================

    def save_upload(
        self,
        source_file: Path,
    ) -> Path:

        filename = SafeFilename.unique(source_file.name)

        destination = self._paths.upload_file(filename)

        AtomicWriter.copy_file(
            source_file,
            destination,
        )

        return destination

    def get_upload(
        self,
        filename: str,
    ) -> Path:

        return self._paths.upload_file(filename)

    # ==========================================================
    # Output
    # ==========================================================

    def save_output(
        self,
        source_file: Path,
    ) -> Path:

        filename = SafeFilename.unique(source_file.name)

        destination = self._paths.output_file(filename)

        AtomicWriter.copy_file(
            source_file,
            destination,
        )

        return destination

    def get_output(
        self,
        filename: str,
    ) -> Path:

        return self._paths.output_file(filename)

    # ==========================================================
    # Transcript
    # ==========================================================

    def save_transcript(
        self,
        job_id: str,
        transcript: str,
    ) -> Path:

        destination = self._paths.transcript_file(job_id)

        AtomicWriter.write_text(
            destination,
            transcript,
        )

        return destination

    def get_transcript(
        self,
        job_id: str,
    ) -> str:

        file = self._paths.transcript_file(job_id)

        if not file.exists():
            return ""

        return file.read_text(
            encoding="utf-8",
        )

    # ==========================================================
    # Subtitle
    # ==========================================================

    def save_subtitle(
        self,
        source_file: Path,
    ) -> Path:

        filename = SafeFilename.unique(source_file.name)

        destination = self._paths.subtitles / filename

        AtomicWriter.copy_file(
            source_file,
            destination,
        )

        return destination

    def get_subtitle(
        self,
        filename: str,
    ) -> Path:

        return self._paths.subtitles / filename

    # ==========================================================
    # Temp
    # ==========================================================

    def create_temp_file(
        self,
        suffix: str = "",
    ) -> Path:

        temp = tempfile.NamedTemporaryFile(
            delete=False,
            suffix=suffix,
            dir=self._paths.temp,
        )

        temp.close()

        return Path(temp.name)

    def delete_temp_file(
        self,
        file_path: Path,
    ) -> None:

        if file_path.exists():
            file_path.unlink()

    # ==========================================================
    # Cache
    # ==========================================================

    def clear_cache(
        self,
    ) -> None:

        for file in self._paths.cache.iterdir():

            if file.is_file():
                file.unlink()

            elif file.is_dir():
                shutil.rmtree(file)

    # ==========================================================
    # Job Cleanup
    # ==========================================================

    def delete_job_files(
        self,
        job_id: str,
    ) -> None:

        files = [
            self._paths.transcript_file(job_id),
            self._paths.subtitle_file(job_id),
            self._paths.job_directory(job_id),
        ]

        for item in files:

            if item.is_file():
                item.unlink()

            elif item.is_dir():
                shutil.rmtree(
                    item,
                    ignore_errors=True,
                )

    # ==========================================================
    # Generic
    # ==========================================================

    def exists(
        self,
        path: Path,
    ) -> bool:

        return path.exists()

    def delete(
        self,
        path: Path,
    ) -> None:

        if path.is_file():
            path.unlink()

        elif path.is_dir():
            shutil.rmtree(
                path,
                ignore_errors=True,
            )

    def copy(
        self,
        source: Path,
        destination: Path,
    ) -> Path:

        AtomicWriter.copy_file(
            source,
            destination,
        )

        return destination

    def move(
        self,
        source: Path,
        destination: Path,
    ) -> Path:

        destination.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        shutil.move(
            str(source),
            str(destination),
        )

        return destination

    def storage_usage(
        self,
    ) -> dict[str, int]:

        def directory_size(path: Path) -> int:

            if not path.exists():
                return 0

            return sum(
                file.stat().st_size
                for file in path.rglob("*")
                if file.is_file()
            )

        uploads = directory_size(self._paths.uploads)
        output = directory_size(self._paths.output)
        transcripts = directory_size(self._paths.transcripts)
        subtitles = directory_size(self._paths.subtitles)
        cache = directory_size(self._paths.cache)
        temp = directory_size(self._paths.temp)

        total = (
            uploads
            + output
            + transcripts
            + subtitles
            + cache
            + temp
        )

        return {
            "uploads": uploads,
            "output": output,
            "transcripts": transcripts,
            "subtitles": subtitles,
            "cache": cache,
            "temp": temp,
            "total": total,
        }