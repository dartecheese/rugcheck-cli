"""Composite risk scoring across rugcheck.xyz, GoPlus, and DexScreener."""
from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any

from .chains import Chain


@dataclass
class RiskFinding:
    code: str
    severity: str   # "info" | "low" | "medium" | "high" | "critical"
    detail: str

    def points(self) -> int:
        return {"info": 0, "low": 5, "medium": 15, "high": 30, "critical": 50}[self.severity]


@dataclass
class RiskReport:
    address: str
    chain: str
    score: int                    # 0 (clean) – 100 (rug-shaped)
    grade: str                    # A / B / C / D / F
    name: str | None = None
    symbol: str | None = None
    price_usd: float | None = None
    liquidity_usd: float | None = None
    fdv_usd: float | None = None
    pair_url: str | None = None
    lp_locked_pct: float | None = None
    top10_holder_pct: float | None = None
    holder_count: int | None = None
    deployer: str | None = None
    deployer_age_days: float | None = None
    is_honeypot: bool | None = None
    is_open_source: bool | None = None
    is_mintable: bool | None = None
    can_take_back_ownership: bool | None = None
    findings: list[RiskFinding] = field(default_factory=list)
    sources: dict[str, bool] = field(default_factory=dict)  # which APIs answered

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["findings"] = [asdict(f) for f in self.findings]
        return d


def _grade(score: int) -> str:
    if score < 15:
        return "A"
    if score < 30:
        return "B"
    if score < 50:
        return "C"
    if score < 75:
        return "D"
    return "F"


def _as_pct(value: Any) -> float | None:
    """GoPlus returns string ratios like "0.05"; coerce to a 0–100 percentage."""
    if value is None or value == "":
        return None
    try:
        v = float(value)
    except (TypeError, ValueError):
        return None
    return v * 100 if v <= 1 else v


def _as_bool(value: Any) -> bool | None:
    if value is None or value == "":
        return None
    if isinstance(value, bool):
        return value
    s = str(value).strip().lower()
    if s in ("1", "true", "yes"):
        return True
    if s in ("0", "false", "no"):
        return False
    return None


def score_evm(
    address: str,
    chain: Chain,
    goplus: dict[str, Any] | None,
    dex_pair: dict[str, Any] | None,
) -> RiskReport:
    findings: list[RiskFinding] = []
    g = goplus or {}

    is_honeypot = _as_bool(g.get("is_honeypot"))
    is_open_source = _as_bool(g.get("is_open_source"))
    is_mintable = _as_bool(g.get("is_mintable"))
    can_take_back_ownership = _as_bool(g.get("can_take_back_ownership"))
    is_proxy = _as_bool(g.get("is_proxy"))
    transfer_pausable = _as_bool(g.get("transfer_pausable"))
    hidden_owner = _as_bool(g.get("hidden_owner"))
    selfdestruct = _as_bool(g.get("selfdestruct"))
    external_call = _as_bool(g.get("external_call"))
    buy_tax = _as_pct(g.get("buy_tax"))
    sell_tax = _as_pct(g.get("sell_tax"))
    holder_count = int(g["holder_count"]) if g.get("holder_count") not in (None, "") else None

    # LP-lock estimate: GoPlus returns lp_holders[*].is_locked + percent (string fraction).
    lp_locked_pct: float | None = None
    lp_holders = g.get("lp_holders") or []
    if lp_holders:
        locked = 0.0
        for lp in lp_holders:
            if _as_bool(lp.get("is_locked")):
                pct = _as_pct(lp.get("percent"))
                if pct is not None:
                    locked += pct
        lp_locked_pct = round(min(locked, 100.0), 2)

    # Top-10 holder concentration
    top10_holder_pct: float | None = None
    holders = g.get("holders") or []
    if holders:
        top = sorted(
            (h for h in holders if h.get("percent") not in (None, "")),
            key=lambda h: float(h["percent"]),
            reverse=True,
        )[:10]
        if top:
            top10_holder_pct = round(sum(float(h["percent"]) for h in top) * 100, 2)

    # Deployer
    deployer = g.get("creator_address") or g.get("owner_address") or None

    # Findings — severity-weighted points roll up into a 0..100 score.
    if is_honeypot:
        findings.append(RiskFinding("honeypot", "critical", "GoPlus flags this token as a honeypot."))
    if is_open_source is False:
        findings.append(RiskFinding("not_open_source", "high", "Contract source is not verified."))
    if is_mintable:
        findings.append(RiskFinding("mintable", "medium", "Owner can mint additional supply."))
    if can_take_back_ownership:
        findings.append(RiskFinding("ownership_reclaim", "high", "Renounced ownership can be reclaimed."))
    if hidden_owner:
        findings.append(RiskFinding("hidden_owner", "high", "Contract has a hidden owner address."))
    if transfer_pausable:
        findings.append(RiskFinding("pausable", "medium", "Owner can pause all transfers."))
    if selfdestruct:
        findings.append(RiskFinding("selfdestruct", "critical", "Contract contains selfdestruct."))
    if is_proxy:
        findings.append(RiskFinding("proxy", "low", "Contract is a proxy — implementation can change."))
    if external_call:
        findings.append(RiskFinding("external_call", "low", "Contract makes external calls during transfer."))

    if buy_tax is not None and buy_tax >= 10:
        sev = "critical" if buy_tax >= 25 else "high" if buy_tax >= 15 else "medium"
        findings.append(RiskFinding("high_buy_tax", sev, f"Buy tax is {buy_tax:.1f}%."))
    if sell_tax is not None and sell_tax >= 10:
        sev = "critical" if sell_tax >= 25 else "high" if sell_tax >= 15 else "medium"
        findings.append(RiskFinding("high_sell_tax", sev, f"Sell tax is {sell_tax:.1f}%."))

    if lp_locked_pct is not None and lp_locked_pct < 50:
        sev = "high" if lp_locked_pct < 10 else "medium"
        findings.append(RiskFinding("lp_unlocked", sev, f"Only {lp_locked_pct:.1f}% of LP is locked."))

    if top10_holder_pct is not None and top10_holder_pct >= 50:
        sev = "critical" if top10_holder_pct >= 80 else "high" if top10_holder_pct >= 65 else "medium"
        findings.append(RiskFinding(
            "holder_concentration", sev,
            f"Top-10 holders own {top10_holder_pct:.1f}% of supply.",
        ))

    if holder_count is not None and holder_count < 100:
        findings.append(RiskFinding("few_holders", "medium", f"Only {holder_count} on-chain holders."))

    pair = dex_pair or {}
    liq = (pair.get("liquidity") or {}).get("usd")
    if liq is not None and liq < 10_000:
        sev = "high" if liq < 1_000 else "medium"
        findings.append(RiskFinding("thin_liquidity", sev, f"Pair liquidity is only ${liq:,.0f}."))

    score = min(100, sum(f.points() for f in findings))

    return RiskReport(
        address=address,
        chain=chain.slug,
        score=score,
        grade=_grade(score),
        name=(pair.get("baseToken") or {}).get("name") or g.get("token_name"),
        symbol=(pair.get("baseToken") or {}).get("symbol") or g.get("token_symbol"),
        price_usd=float(pair["priceUsd"]) if pair.get("priceUsd") else None,
        liquidity_usd=liq,
        fdv_usd=pair.get("fdv"),
        pair_url=pair.get("url"),
        lp_locked_pct=lp_locked_pct,
        top10_holder_pct=top10_holder_pct,
        holder_count=holder_count,
        deployer=deployer,
        deployer_age_days=None,  # populated by caller when available
        is_honeypot=is_honeypot,
        is_open_source=is_open_source,
        is_mintable=is_mintable,
        can_take_back_ownership=can_take_back_ownership,
        findings=findings,
        sources={"goplus": goplus is not None, "dexscreener": dex_pair is not None},
    )


def score_solana(
    address: str,
    chain: Chain,
    rug: dict[str, Any] | None,
    dex_pair: dict[str, Any] | None,
) -> RiskReport:
    findings: list[RiskFinding] = []
    r = rug or {}

    # rugcheck.xyz returns a `risks` array with name/level/score and a top-level score.
    severity_map = {"none": "info", "info": "info", "low": "low", "warn": "medium",
                    "warning": "medium", "danger": "high", "critical": "critical"}
    for risk in (r.get("risks") or []):
        sev = severity_map.get(str(risk.get("level", "")).lower(), "low")
        findings.append(RiskFinding(
            code=str(risk.get("name") or "rugcheck_risk").lower().replace(" ", "_"),
            severity=sev,
            detail=str(risk.get("description") or risk.get("name") or "").strip(),
        ))

    # LP locked: rugcheck exposes either `markets[*].lp.lpLockedPct` or `totalLPProviders`.
    lp_locked_pct: float | None = None
    markets = r.get("markets") or []
    if markets:
        lp_pcts = [
            (m.get("lp") or {}).get("lpLockedPct")
            for m in markets
            if (m.get("lp") or {}).get("lpLockedPct") is not None
        ]
        if lp_pcts:
            lp_locked_pct = round(max(float(p) for p in lp_pcts), 2)

    if lp_locked_pct is not None and lp_locked_pct < 50:
        sev = "high" if lp_locked_pct < 10 else "medium"
        # Avoid duplicating if rugcheck already flagged it.
        if not any(f.code.startswith("lp_") for f in findings):
            findings.append(RiskFinding("lp_unlocked", sev, f"Only {lp_locked_pct:.1f}% of LP is locked."))

    # Top-10 holder concentration
    top10_holder_pct: float | None = None
    top_holders = r.get("topHolders") or []
    if top_holders:
        top10_holder_pct = round(sum(float(h.get("pct") or 0) for h in top_holders[:10]), 2)
        if top10_holder_pct >= 50 and not any(f.code == "holder_concentration" for f in findings):
            sev = "critical" if top10_holder_pct >= 80 else "high" if top10_holder_pct >= 65 else "medium"
            findings.append(RiskFinding(
                "holder_concentration", sev,
                f"Top-10 holders own {top10_holder_pct:.1f}% of supply.",
            ))

    holder_count = r.get("totalHolders") or r.get("token", {}).get("holderCount")
    holder_count = int(holder_count) if holder_count else None

    is_mintable = r.get("token", {}).get("mintAuthority") not in (None, "")
    if is_mintable:
        findings.append(RiskFinding("mintable", "medium", "Mint authority is not renounced."))

    freeze_authority = r.get("token", {}).get("freezeAuthority")
    if freeze_authority:
        findings.append(RiskFinding("freezable", "high", "Freeze authority is not renounced."))

    pair = dex_pair or {}
    liq = (pair.get("liquidity") or {}).get("usd")
    if liq is not None and liq < 10_000:
        sev = "high" if liq < 1_000 else "medium"
        findings.append(RiskFinding("thin_liquidity", sev, f"Pair liquidity is only ${liq:,.0f}."))

    # Prefer rugcheck's own score when it looks reasonable (0..100), otherwise compute.
    rug_score = r.get("score")
    if isinstance(rug_score, (int, float)) and 0 <= rug_score <= 100:
        score = int(round(rug_score))
    else:
        score = min(100, sum(f.points() for f in findings))

    return RiskReport(
        address=address,
        chain=chain.slug,
        score=score,
        grade=_grade(score),
        name=(pair.get("baseToken") or {}).get("name") or (r.get("tokenMeta") or {}).get("name"),
        symbol=(pair.get("baseToken") or {}).get("symbol") or (r.get("tokenMeta") or {}).get("symbol"),
        price_usd=float(pair["priceUsd"]) if pair.get("priceUsd") else None,
        liquidity_usd=liq,
        fdv_usd=pair.get("fdv"),
        pair_url=pair.get("url"),
        lp_locked_pct=lp_locked_pct,
        top10_holder_pct=top10_holder_pct,
        holder_count=holder_count,
        deployer=(r.get("creator") or r.get("token", {}).get("mintAuthority")),
        is_mintable=is_mintable,
        findings=findings,
        sources={"rugcheck": rug is not None, "dexscreener": dex_pair is not None},
    )
