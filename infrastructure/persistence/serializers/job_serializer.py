"""
Translation Job Serializer.

Converts TranslationJob domain entities to and from dictionaries
for persistence.

Repositories should never directly serialize or deserialize
TranslationJob objects.
"""

from __future__ import annotations

from typing import Any

from domain.entities.translation_job import TranslationJob


class JobSerializer:
    """
    Serializer for TranslationJob.
    """

    @staticmethod
    def serialize(
        job: TranslationJob,
    ) -> dict[str, Any]:
        """
        Convert a TranslationJob into a serializable dictionary.
        """

        return job.to_dict()

    @staticmethod
    def deserialize(
        data: dict[str, Any],
    ) -> TranslationJob:
        """
        Reconstruct a TranslationJob from persisted data.
        """

        return TranslationJob.from_dict(data)

    @staticmethod
    def serialize_many(
        jobs: list[TranslationJob],
    ) -> list[dict[str, Any]]:
        """
        Serialize multiple jobs.
        """

        return [
            JobSerializer.serialize(job)
            for job in jobs
        ]

    @staticmethod
    def deserialize_many(
        data: list[dict[str, Any]],
    ) -> list[TranslationJob]:
        """
        Deserialize multiple jobs.
        """

        return [
            JobSerializer.deserialize(item)
            for item in data
        ]