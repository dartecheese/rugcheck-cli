import pytest

from rugcheck_cli.chains import detect_chain


def test_evm_address_defaults_to_ethereum():
    chain = detect_chain("0x6982508145454ce325ddbe47a25d4ec3d2311933")
    assert chain.slug == "ethereum"
    assert chain.family == "evm"
    assert chain.goplus_id == "1"


def test_evm_hint_overrides_default():
    chain = detect_chain("0x6982508145454ce325ddbe47a25d4ec3d2311933", "base")
    assert chain.slug == "base"
    assert chain.goplus_id == "8453"


def test_solana_address_detected():
    chain = detect_chain("So11111111111111111111111111111111111111112")
    assert chain.slug == "solana"
    assert chain.family == "solana"


def test_unknown_chain_raises():
    with pytest.raises(ValueError):
        detect_chain("0x6982508145454ce325ddbe47a25d4ec3d2311933", "fakechain")


def test_garbage_address_raises():
    with pytest.raises(ValueError):
        detect_chain("not-a-real-address!!")
