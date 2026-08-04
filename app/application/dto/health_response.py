"""
Health Response DTO

Application layer response model for system health.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass(slots=True, frozen=True)
class ComponentHealth:
    """
    Health information for an individual component.
    """

    name: str
    status: str
    message: Optional[str] = None
    details: Dict[str, str] = field(default_factory=dict)


@dataclass(slots=True, frozen=True)
class HealthResponse:
    """
    Overall system health response.
    """

    status: str
    version: str
    uptime_seconds: float
    timestamp: str
    components: List[ComponentHealth] = field(default_factory=list)