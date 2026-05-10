"""GoPlus token security API client (EVM chains)."""
from __future__ import annotations

from typing import Any

import httpx

from ._base import APIError, get_json

BASE = "https://api.gopluslabs.io/api/v1"


class GoPlusClient:
    """Wraps the GoPlus token_security endpoint.

    Each chain has a numeric chain_id. The response is keyed by lowercased
    contract address inside `result`.
    """

    def __init__(self, client: httpx.AsyncClient):
        self._client = client

    async def token_security(self, chain_id: str, address: str) -> dict[str, Any] | None:
        url = f"{BASE}/token_security/{chain_id}"
        data = await get_json(self._client, url, params={"contract_addresses": address})
        if not data:
            return None
        if data.get("code") not in (1, None):
            # Non-fatal: GoPlus returns code != 1 with a message in some error cases.
            raise APIError(f"GoPlus error {data.get('code')}: {data.get('message')}")
        result = (data.get("result") or {})
        return result.get(address.lower())
