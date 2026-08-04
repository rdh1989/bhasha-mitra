"""
History Serializer.

Serializes archived TranslationJob instances.

Currently this is identical to JobSerializer because archived jobs
share the same domain model. Keeping it separate allows the archive
format to evolve independently in the future.
"""

from __future__ import annotations

from typing import Any

from domain.entities.translation_job import TranslationJob


class HistorySerializer:
    """
    Serializer for archived TranslationJob objects.
    """

    @staticmethod
    def serialize(
        job: TranslationJob,
    ) -> dict[str, Any]:
        """
        Serialize an archived TranslationJob.
        """

        return job.to_dict()

    @staticmethod
    def deserialize(
        data: dict[str, Any],
    ) -> TranslationJob:
        """
        Deserialize an archived TranslationJob.
        """

        return TranslationJob.from_dict(data)

    @staticmethod
    def serialize_many(
        jobs: list[TranslationJob],
    ) -> list[dict[str, Any]]:
        """
        Serialize multiple archived jobs.
        """

        return [
            HistorySerializer.serialize(job)
            for job in jobs
        ]

    @staticmethod
    def deserialize_many(
        data: list[dict[str, Any]],
    ) -> list[TranslationJob]:
        """
        Deserialize multiple archived jobs.
        """

        return [
            HistorySerializer.deserialize(item)
            for item in data
        ]