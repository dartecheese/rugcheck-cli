"""rugcheck.xyz API client (Solana-focused)."""
from __future__ import annotations

from typing import Any

import httpx

from ._base import get_json

BASE = "https://api.rugcheck.xyz/v1"


class RugcheckClient:
    """Wraps the public rugcheck.xyz token report endpoints.

    Solana-only. The /report endpoint returns rich data (LP locks, top holders,
    risks, score). /report/summary is a lighter variant.
    """

    def __init__(self, client: httpx.AsyncClient):
        self._client = client

    async def report(self, mint: str) -> dict[str, Any] | None:
        return await get_json(self._client, f"{BASE}/tokens/{mint}/report")

    async def summary(self, mint: str) -> dict[str, Any] | None:
        return await get_json(self._client, f"{BASE}/tokens/{mint}/report/summary")
