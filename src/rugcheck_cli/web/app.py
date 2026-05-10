"""FastAPI dashboard for rugcheck-cli.

Exposes /api/scan?address=...&chain=... that returns the same RiskReport the
CLI prints, plus a single-page UI at /.
"""
from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from .. import __version__
from ..runner import scan

STATIC_DIR = Path(__file__).parent / "static"


def create_app() -> FastAPI:
    app = FastAPI(
        title="rugcheck-cli dashboard",
        version=__version__,
        docs_url="/api/docs",
        redoc_url=None,
    )

    @app.get("/api/health")
    async def health() -> dict[str, str]:
        return {"status": "ok", "version": __version__}

    @app.get("/api/scan")
    async def scan_token(
        address: str = Query(..., description="Token address"),
        chain: str | None = Query(None, description="Chain hint (optional)"),
    ) -> JSONResponse:
        try:
            report = await scan(address.strip(), chain)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        except Exception as e:
            raise HTTPException(status_code=502, detail=f"upstream error: {e}")
        return JSONResponse(report.to_dict())

    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

    @app.get("/")
    async def index() -> FileResponse:
        return FileResponse(STATIC_DIR / "index.html")

    return app


app = create_app()
