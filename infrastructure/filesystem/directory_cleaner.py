"""
Directory Cleaner.

Provides utilities for cleaning temporary directories, cache,
expired files, and empty folders.

This utility does not decide application retention policy.
Callers are responsible for deciding what may be deleted.
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

        Args:
            directory:
                Directory whose contents should be removed.

            remove_directory:
                Also remove the directory itself.

        Returns:
            Number of deleted items.
        """

        directory = Path(directory)

        if not directory.exists():
            return 0

        if not directory.is_dir():

            raise NotADirectoryError(
                f"Not a directory: {directory}"
            )

        deleted = 0

        for item in directory.iterdir():

            try:

                if item.is_file() or item.is_symlink():

                    item.unlink(
                        missing_ok=True
                    )

                    deleted += 1

                elif item.is_dir():

                    shutil.rmtree(
                        item
                    )

                    deleted += 1

            except OSError:

                raise

        if remove_directory:

            try:
                directory.rmdir()

            except OSError as exc:

                raise RuntimeError(
                    f"Unable to remove directory: "
                    f"{directory}"
                ) from exc

        return deleted

    @staticmethod
    def delete_older_than(
        directory: Path,
        *,
        days: int,
    ) -> int:
        """
        Delete files older than the specified number of days.

        Only files are deleted. Directories are retained.

        Args:
            directory:
                Directory to scan.

            days:
                Age threshold in days.

        Returns:
            Number of deleted files.
        """

        directory = Path(directory)

        if days < 0:

            raise ValueError(
                "days cannot be negative."
            )

        if not directory.exists():
            return 0

        if not directory.is_dir():

            raise NotADirectoryError(
                f"Not a directory: {directory}"
            )

        cutoff = (
            datetime.now()
            - timedelta(days=days)
        )

        deleted = 0

        for file in directory.rglob("*"):

            if not file.is_file():

                continue

            try:

                modified = datetime.fromtimestamp(
                    file.stat().st_mtime
                )

                if modified < cutoff:

                    file.unlink(
                        missing_ok=True
                    )

                    deleted += 1

            except OSError:

                raise

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

        directory = Path(directory)

        if not directory.exists():
            return 0

        if not directory.is_dir():

            raise NotADirectoryError(
                f"Not a directory: {directory}"
            )

        removed = 0

        directories = sorted(
            (
                path
                for path in directory.rglob("*")
                if path.is_dir()
            ),
            key=lambda path: len(
                path.parts
            ),
            reverse=True,
        )

        for path in directories:

            try:

                path.rmdir()
                removed += 1

            except OSError:
                # Directory is not empty or cannot be removed.
                pass

        return removed

    @staticmethod
    def cleanup_job_directory(
        job_directory: Path,
    ) -> None:
        """
        Completely remove a job working directory.

        The caller must ensure that the supplied directory is actually
        eligible for deletion.

        This method does not determine whether a translation job is
        completed, failed, expired, or still required.
        """

        job_directory = Path(
            job_directory
        )

        if not job_directory.exists():
            return

        if not job_directory.is_dir():

            raise NotADirectoryError(
                f"Not a directory: {job_directory}"
            )

        shutil.rmtree(
            job_directory
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