from __future__ import annotations

import os

import httpx


def get_api_root() -> str:
    host = os.getenv("GYM_API_HOST", "127.0.0.1")
    port = os.getenv("GYM_API_PORT", "8000")
    return f"http://{host}:{port}"


def get_api_base_url() -> str:
    return os.getenv("GYM_API_BASE_URL", "http://127.0.0.1:8000/api/v1")


def check_health(timeout_seconds: float = 5.0) -> tuple[bool, str]:
    url = f"{get_api_root()}/health"
    try:
        response = httpx.get(url, timeout=timeout_seconds)
        if response.status_code == 200:
            return True, f"API OK ({url})"
        return False, f"API returned {response.status_code} ({url})"
    except httpx.HTTPError as exc:
        return False, f"API unavailable ({url}): {exc.__class__.__name__}"
