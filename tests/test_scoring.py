from rugcheck_cli.chains import CHAINS
from rugcheck_cli.scoring import score_evm, score_solana


def test_clean_evm_token_grades_well():
    goplus = {
        "is_honeypot": "0",
        "is_open_source": "1",
        "is_mintable": "0",
        "can_take_back_ownership": "0",
        "buy_tax": "0",
        "sell_tax": "0",
        "holder_count": "12000",
        "lp_holders": [{"is_locked": "1", "percent": "0.95"}],
        "holders": [{"percent": "0.02"}] * 5,
        "token_name": "Clean",
        "token_symbol": "CLN",
    }
    pair = {"liquidity": {"usd": 500_000}, "priceUsd": "0.001",
            "baseToken": {"name": "Clean", "symbol": "CLN"}}
    report = score_evm("0x" + "a" * 40, CHAINS["ethereum"], goplus=goplus, dex_pair=pair)
    assert report.score < 15
    assert report.grade == "A"
    assert report.lp_locked_pct == 95.0
    assert report.findings == []


def test_honeypot_evm_token_scores_high():
    goplus = {
        "is_honeypot": "1",
        "is_open_source": "0",
        "is_mintable": "1",
        "buy_tax": "0",
        "sell_tax": "30",
        "holder_count": "20",
        "lp_holders": [{"is_locked": "0", "percent": "1"}],
        "holders": [{"percent": "0.85"}],
    }
    report = score_evm("0x" + "b" * 40, CHAINS["bsc"], goplus=goplus, dex_pair=None)
    assert report.score >= 75
    assert report.grade == "F"
    codes = {f.code for f in report.findings}
    assert "honeypot" in codes
    assert "high_sell_tax" in codes
    assert "few_holders" in codes
    assert "lp_unlocked" in codes
    assert "holder_concentration" in codes


def test_solana_uses_rugcheck_score_when_present():
    rug = {
        "score": 42,
        "risks": [{"name": "Low liquidity", "level": "warn", "description": "thin"}],
        "topHolders": [{"pct": 6}, {"pct": 5}, {"pct": 4}],
        "totalHolders": 1500,
        "token": {"mintAuthority": None, "freezeAuthority": None},
        "tokenMeta": {"name": "Cat", "symbol": "CAT"},
    }
    report = score_solana("So11111111111111111111111111111111111111112",
                          CHAINS["solana"], rug=rug, dex_pair=None)
    assert report.score == 42
    assert report.grade == "C"
    assert report.holder_count == 1500


def test_solana_freeze_authority_flagged():
    rug = {
        "risks": [],
        "topHolders": [],
        "totalHolders": 5000,
        "token": {"mintAuthority": "Abc...", "freezeAuthority": "Def..."},
    }
    report = score_solana("So11111111111111111111111111111111111111112",
                          CHAINS["solana"], rug=rug, dex_pair=None)
    codes = {f.code for f in report.findings}
    assert "freezable" in codes
    assert "mintable" in codes
