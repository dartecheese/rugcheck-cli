"""Chain detection and metadata."""
from __future__ import annotations

import re
from dataclasses import dataclass

EVM_RE = re.compile(r"^0x[0-9a-fA-F]{40}$")
SOLANA_RE = re.compile(r"^[1-9A-HJ-NP-Za-km-z]{32,44}$")


@dataclass(frozen=True)
class Chain:
    slug: str          # internal canonical name
    goplus_id: str | None  # GoPlus chain id, None if unsupported
    dexscreener: str   # DexScreener chain identifier
    family: str        # "evm" or "solana"


CHAINS: dict[str, Chain] = {
    "ethereum": Chain("ethereum", "1", "ethereum", "evm"),
    "bsc": Chain("bsc", "56", "bsc", "evm"),
    "polygon": Chain("polygon", "137", "polygon", "evm"),
    "arbitrum": Chain("arbitrum", "42161", "arbitrum", "evm"),
    "base": Chain("base", "8453", "base", "evm"),
    "optimism": Chain("optimism", "10", "optimism", "evm"),
    "avalanche": Chain("avalanche", "43114", "avalanche", "evm"),
    "solana": Chain("solana", None, "solana", "solana"),
}


def detect_chain(address: str, hint: str | None = None) -> Chain:
    """Detect chain from address shape, or use the user hint."""
    if hint:
        key = hint.lower()
        if key not in CHAINS:
            raise ValueError(f"Unknown chain '{hint}'. Known: {', '.join(CHAINS)}")
        return CHAINS[key]

    if EVM_RE.match(address):
        # Default EVM to ethereum; user can override with --chain.
        return CHAINS["ethereum"]
    if SOLANA_RE.match(address):
        return CHAINS["solana"]
    raise ValueError(
        f"Could not detect chain for address {address!r}. Pass --chain explicitly."
    )
