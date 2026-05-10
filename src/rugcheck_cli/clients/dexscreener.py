"""DexScreener API client."""
from __future__ import annotations

from typing import Any

import httpx

from ._base import get_json

BASE = "https://api.dexscreener.com/latest/dex"


class DexScreenerClient:
    """Wraps the public DexScreener token endpoint.

    Returns the list of pairs across all DEXs. We pick the highest-liquidity
    pair on the requested chain as the canonical pair for risk scoring.
    """

    def __init__(self, client: httpx.AsyncClient):
        self._client = client

    async def token(self, address: str) -> dict[str, Any] | None:
        return await get_json(self._client, f"{BASE}/tokens/{address}")

    async def best_pair(self, address: str, chain_slug: str) -> dict[str, Any] | None:
        data = await self.token(address)
        pairs = (data or {}).get("pairs") or []
        chain_pairs = [p for p in pairs if (p.get("chainId") or "").lower() == chain_slug.lower()]
        if not chain_pairs:
            return None
        return max(chain_pairs, key=lambda p: ((p.get("liquidity") or {}).get("usd") or 0))
