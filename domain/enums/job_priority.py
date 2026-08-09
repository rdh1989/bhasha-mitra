"""
===============================================================================
BHASHA MITRA

Module:
    job_priority.py

Layer:
    Domain / Enums

Description:
    Defines translation job priority levels.

Database compatibility:
    Existing SQLite records persist priority values such as:
        NORMAL

    Therefore enum values must match the persisted representation.
===============================================================================
"""

from enum import Enum


class JobPriority(str, Enum):
    """
    Priority assigned to a translation job.
    """

    LOW = "LOW"

    NORMAL = "NORMAL"

    HIGH = "HIGH"

    CRITICAL = "CRITICAL"