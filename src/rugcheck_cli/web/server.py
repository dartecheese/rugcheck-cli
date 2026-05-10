"""`rugcheck-dashboard` CLI entrypoint — boots a local uvicorn server."""
from __future__ import annotations

import sys
import webbrowser

import click


@click.command()
@click.option("--host", default="127.0.0.1", show_default=True,
              help="Host to bind. Use 0.0.0.0 to expose on your LAN.")
@click.option("--port", default=8787, show_default=True, type=int)
@click.option("--reload", is_flag=True, help="Auto-reload on code changes (dev mode).")
@click.option("--open/--no-open", "open_browser", default=True, show_default=True,
              help="Open the dashboard in your browser.")
def main(host: str, port: int, reload: bool, open_browser: bool) -> None:
    """Run the local rugcheck dashboard."""
    try:
        import uvicorn
    except ImportError:
        click.echo(
            "error: dashboard extras not installed. Run:\n"
            "  pip install 'rugcheck-cli[dashboard]'",
            err=True,
        )
        sys.exit(1)

    url = f"http://{host}:{port}"
    click.echo(f"rugcheck dashboard → {url}")
    if open_browser and host in ("127.0.0.1", "localhost"):
        try:
            webbrowser.open(url)
        except Exception:
            pass

    uvicorn.run(
        "rugcheck_cli.web.app:app",
        host=host,
        port=port,
        reload=reload,
        log_level="info",
    )


if __name__ == "__main__":
    main()
