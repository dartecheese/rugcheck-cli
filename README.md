# rugcheck-cli

One command. Three sources. A composite rug-risk score for any EVM or Solana token.

`rugcheck-cli` wraps **[rugcheck.xyz]**, **[GoPlus]**, and **[DexScreener]** behind
a single CLI. It auto-detects the chain from the address, fans out concurrent
requests, and rolls everything up into a 0–100 score with a letter grade and a
list of human-readable findings.

[rugcheck.xyz]: https://rugcheck.xyz
[GoPlus]: https://gopluslabs.io
[DexScreener]: https://dexscreener.com

## Install

```bash
pipx install git+https://github.com/dartecheese/rugcheck-cli
# or, from a clone:
pip install -e .
```

Requires Python 3.10+.

## Usage

```bash
rugcheck 0x6982508145454ce325ddbe47a25d4ec3d2311933   # PEPE on ethereum
rugcheck So11111111111111111111111111111111111111112   # wSOL on solana
rugcheck 0x4200000000000000000000000000000000000006 --chain base
rugcheck <addr> --json | jq .findings
```

EVM addresses default to `ethereum`. Use `--chain` to scan on `bsc`, `polygon`,
`arbitrum`, `base`, `optimism`, or `avalanche`. Solana addresses are detected
automatically.

## What it checks

| Source | Signal |
| --- | --- |
| **rugcheck.xyz** | Solana risk model, LP-lock %, top-holder concentration, mint/freeze authority |
| **GoPlus** | Honeypot, open-source, mintable, ownership reclaim, hidden owner, pausable, selfdestruct, proxy, buy/sell taxes, LP holders, holder list |
| **DexScreener** | Best pair, liquidity, FDV, price, pair URL |

Findings are severity-weighted (`info`/`low`/`medium`/`high`/`critical`) and
summed into a score. On Solana, rugcheck.xyz's own score wins when present.

| Score | Grade |
| ---: | :--- |
| 0–14 | A |
| 15–29 | B |
| 30–49 | C |
| 50–74 | D |
| 75–100 | F |

## Output

```
╭─ PEPE  Pepe  [ethereum] ────────────────────────╮
│ Address          0x6982...1933                  │
│ Score            8/100  (A)                     │
│ Liquidity        $14.2M                         │
│ LP locked        99.0%                          │
│ Top-10 holders   34.1%                          │
│ Holders          245,019                        │
│ Sources          goplus, dexscreener            │
╰─────────────────────────────────────────────────╯
```

`--json` emits the full structured report for scripting / piping into a Shield
risk-engine pipeline.

## Local dashboard

For something a little more visually appealing, install the optional dashboard
extras and spin up a local web UI:

```bash
pip install "rugcheck-cli[dashboard]"
rugcheck-dashboard          # opens http://127.0.0.1:8787 in your browser
rugcheck-dashboard --port 9000 --no-open
rugcheck-dashboard --host 0.0.0.0   # expose on your LAN
```

The dashboard is a single-page UI served by FastAPI: paste an address, get a
score ring, key metrics (price / liquidity / FDV / holders / LP-lock / top-10),
severity-colored findings, and the raw JSON for piping. Same scan logic as the
CLI — just rendered.

API surface (handy for embedding into your own tools):

| Endpoint | Purpose |
| --- | --- |
| `GET /api/health` | Liveness probe |
| `GET /api/scan?address=...&chain=...` | Returns the full `RiskReport` JSON |
| `GET /api/docs` | OpenAPI / Swagger UI |

## Development

```bash
pip install -e ".[dev]"
pytest
```

The clients (`src/rugcheck_cli/clients/`) are intentionally small — adding new
chains, new sources, or new heuristics is a one-file change.

## Roadmap

- [x] Local dashboard (`rugcheck-dashboard`)
- [ ] Deployer-wallet age (Etherscan / Solscan)
- [ ] Holder churn / freshness
- [ ] Multi-token batch mode
- [ ] Cache layer (24h) for repeat scans
- [ ] Rugcheck token-history (votes / verified) signal
- [ ] GoPlus NFT + approval security endpoints
- [ ] Watchlist + history view in the dashboard
- [ ] Compare mode (two tokens side-by-side)
