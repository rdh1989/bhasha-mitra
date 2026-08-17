from __future__ import annotations

import secrets


INTERNAL_API_HEADER = "X-Bhasha-Internal-Token"
INTERNAL_API_TOKEN = secrets.token_urlsafe(48)


def internal_api_headers() -> dict[str, str]:
    return {INTERNAL_API_HEADER: INTERNAL_API_TOKEN}