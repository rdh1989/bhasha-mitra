"""
Directory Cleaner.

Provides utilities for cleaning temporary directories, cache,
expired files, and empty folders.
"""

from __future__ import annotations

import shutil
from datetime import datetime, timedelta
from pathlib import Path


class DirectoryCleaner:
    """
    Utility for cleaning directories.
    """

    @staticmethod
    def clear_directory(
        directory: Path,
        *,
        remove_directory: bool = False,
    ) -> int:
        """
        Delete all contents of a directory.

        Returns:
            Number of deleted items.
        """

        if not directory.exists():
            return 0

        deleted = 0

        for item in directory.iterdir():

            if item.is_file():
                item.unlink(missing_ok=True)
                deleted += 1

            elif item.is_dir():
                shutil.rmtree(item, ignore_errors=True)
                deleted += 1

        if remove_directory:
            directory.rmdir()

        return deleted

    @staticmethod
    def delete_older_than(
        directory: Path,
        *,
        days: int,
    ) -> int:
        """
        Delete files older than the specified number of days.

        Returns:
            Number of deleted files.
        """

        if not directory.exists():
            return 0

        cutoff = datetime.now() - timedelta(days=days)

        deleted = 0

        for file in directory.rglob("*"):

            if not file.is_file():
                continue

            modified = datetime.fromtimestamp(
                file.stat().st_mtime
            )

            if modified < cutoff:
                file.unlink(missing_ok=True)
                deleted += 1

        return deleted

    @staticmethod
    def remove_empty_directories(
        directory: Path,
    ) -> int:
        """
        Remove all empty subdirectories.

        Returns:
            Number of removed directories.
        """

        if not directory.exists():
            return 0

        removed = 0

        directories = sorted(
            [p for p in directory.rglob("*") if p.is_dir()],
            reverse=True,
        )

        for path in directories:

            try:
                path.rmdir()
                removed += 1

            except OSError:
                # Directory not empty
                pass

        return removed

    @staticmethod
    def cleanup_job_directory(
        job_directory: Path,
    ) -> None:
        """
        Completely remove a job working directory.
        """

        if job_directory.exists():
            shutil.rmtree(
                job_directory,
                ignore_errors=True,
            )

    @staticmethod
    def cleanup_temp(
        temp_directory: Path,
        *,
        older_than_days: int = 1,
    ) -> int:
        """
        Cleanup temporary files.

        Returns:
            Number of deleted files.
        """

        return DirectoryCleaner.delete_older_than(
            temp_directory,
            days=older_than_days,
        )

    @staticmethod
    def cleanup_cache(
        cache_directory: Path,
        *,
        older_than_days: int = 30,
    ) -> int:
        """
        Cleanup cache files.

        Returns:
            Number of deleted files.
        """

        return DirectoryCleaner.delete_older_than(
            cache_directory,
            days=older_than_days,
        )