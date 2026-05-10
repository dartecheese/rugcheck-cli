"""Shared HTTP plumbing for all API clients."""
from __future__ import annotations

from typing import Any

import httpx

DEFAULT_TIMEOUT = 12.0
DEFAULT_HEADERS = {"User-Agent": "rugcheck-cli/0.1 (+https://github.com/dartecheese/rugcheck-cli)"}


class APIError(RuntimeError):
    """Raised when an upstream API returns an unexpected response."""


async def get_json(
    client: httpx.AsyncClient,
    url: str,
    *,
    params: dict[str, Any] | None = None,
    headers: dict[str, str] | None = None,
) -> Any:
    merged = {**DEFAULT_HEADERS, **(headers or {})}
    resp = await client.get(url, params=params, headers=merged, timeout=DEFAULT_TIMEOUT)
    if resp.status_code == 404:
        return None
    if resp.status_code >= 400:
        raise APIError(f"GET {url} -> {resp.status_code}: {resp.text[:200]}")
    try:
        return resp.json()
    except ValueError as e:
        raise APIError(f"Invalid JSON from {url}: {e}") from e
