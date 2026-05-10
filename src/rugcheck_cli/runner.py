"""Top-level orchestration: fan out to upstream APIs and produce a RiskReport."""
from __future__ import annotations

import asyncio

import httpx

from .chains import Chain, detect_chain
from .clients import DexScreenerClient, GoPlusClient, RugcheckClient
from .scoring import RiskReport, score_evm, score_solana


async def scan(address: str, chain_hint: str | None = None) -> RiskReport:
    chain = detect_chain(address, chain_hint)

    async with httpx.AsyncClient() as client:
        dex = DexScreenerClient(client)
        if chain.family == "solana":
            rug = RugcheckClient(client)
            rug_data, dex_pair = await asyncio.gather(
                rug.report(address),
                dex.best_pair(address, chain.dexscreener),
                return_exceptions=True,
            )
            return score_solana(
                address, chain,
                rug=_unwrap(rug_data),
                dex_pair=_unwrap(dex_pair),
            )

        # EVM path
        if chain.goplus_id is None:
            raise ValueError(f"GoPlus has no chain id for {chain.slug}")
        gp = GoPlusClient(client)
        gp_data, dex_pair = await asyncio.gather(
            gp.token_security(chain.goplus_id, address),
            dex.best_pair(address, chain.dexscreener),
            return_exceptions=True,
        )
        return score_evm(
            address, chain,
            goplus=_unwrap(gp_data),
            dex_pair=_unwrap(dex_pair),
        )


def _unwrap(maybe_exc):
    """Treat upstream errors as missing data so a single 5xx doesn't break the scan."""
    if isinstance(maybe_exc, BaseException):
        return None
    return maybe_exc
