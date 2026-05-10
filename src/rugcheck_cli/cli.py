"""rugcheck CLI entrypoint."""
from __future__ import annotations

import asyncio
import json
import sys

import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from .runner import scan
from .scoring import RiskReport

GRADE_STYLE = {"A": "bold green", "B": "green", "C": "yellow", "D": "orange3", "F": "bold red"}
SEVERITY_STYLE = {"info": "dim", "low": "yellow", "medium": "orange3",
                  "high": "red", "critical": "bold red"}


def _fmt_usd(value: float | None) -> str:
    if value is None:
        return "—"
    if value >= 1_000_000:
        return f"${value/1_000_000:.2f}M"
    if value >= 1_000:
        return f"${value/1_000:.2f}K"
    return f"${value:,.4f}" if value < 1 else f"${value:,.2f}"


def _fmt_pct(value: float | None) -> str:
    return "—" if value is None else f"{value:.1f}%"


def _render(report: RiskReport, console: Console) -> None:
    grade_style = GRADE_STYLE.get(report.grade, "white")
    title = Text()
    title.append(f"{report.symbol or '?'}  ", style="bold")
    if report.name:
        title.append(f"{report.name}  ", style="dim")
    title.append(f"[{report.chain}]", style="cyan")

    summary = Table.grid(padding=(0, 2))
    summary.add_column(style="dim")
    summary.add_column()
    summary.add_row("Address", report.address)
    summary.add_row("Score", Text(f"{report.score}/100  ({report.grade})", style=grade_style))
    summary.add_row("Price", _fmt_usd(report.price_usd))
    summary.add_row("Liquidity", _fmt_usd(report.liquidity_usd))
    summary.add_row("FDV", _fmt_usd(report.fdv_usd))
    summary.add_row("LP locked", _fmt_pct(report.lp_locked_pct))
    summary.add_row("Top-10 holders", _fmt_pct(report.top10_holder_pct))
    summary.add_row("Holders", "—" if report.holder_count is None else f"{report.holder_count:,}")
    if report.deployer:
        summary.add_row("Deployer", report.deployer)
    if report.pair_url:
        summary.add_row("Pair", report.pair_url)

    sources = ", ".join(k for k, v in report.sources.items() if v) or "none"
    summary.add_row("Sources", sources)

    console.print(Panel(summary, title=title, border_style=grade_style))

    if not report.findings:
        console.print("[green]No risk findings detected.[/green]")
        return

    findings_table = Table(title="Findings", show_lines=False)
    findings_table.add_column("Severity", no_wrap=True)
    findings_table.add_column("Code", no_wrap=True)
    findings_table.add_column("Detail")
    for f in sorted(report.findings, key=lambda f: -f.points()):
        findings_table.add_row(
            Text(f.severity.upper(), style=SEVERITY_STYLE.get(f.severity, "white")),
            f.code,
            f.detail,
        )
    console.print(findings_table)


@click.command()
@click.argument("address")
@click.option("--chain", "chain_hint", default=None,
              help="Override chain detection (ethereum, bsc, polygon, arbitrum, base, "
                   "optimism, avalanche, solana).")
@click.option("--json", "as_json", is_flag=True, help="Emit raw JSON instead of a table.")
@click.version_option(package_name="rugcheck-cli")
def main(address: str, chain_hint: str | None, as_json: bool) -> None:
    """Scan a token address and print a composite rug-risk report.

    \b
    Examples:
      rugcheck 0x6982508145454ce325ddbe47a25d4ec3d2311933   # PEPE on ethereum
      rugcheck So11111111111111111111111111111111111111112   # wSOL
      rugcheck <addr> --chain base
    """
    try:
        report = asyncio.run(scan(address, chain_hint))
    except ValueError as e:
        click.echo(f"error: {e}", err=True)
        sys.exit(2)
    except Exception as e:  # noqa: BLE001 — top-level guard for nicer CLI UX
        click.echo(f"error: {e}", err=True)
        sys.exit(1)

    if as_json:
        click.echo(json.dumps(report.to_dict(), indent=2, default=str))
        return

    _render(report, Console())


if __name__ == "__main__":
    main()
