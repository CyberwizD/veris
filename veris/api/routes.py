"""FastAPI routes exposed through Reflex's backend."""

from __future__ import annotations

from typing import Any

from fastapi import Body, FastAPI, Query

from veris.engine.service import build_demo_report, validate_records

api = FastAPI(
    title="Veris API",
    description="DCP KPI validation trust layer prototype.",
    version="0.1.0",
)


@api.get("/api/health")
def health() -> dict[str, str]:
    """Health check for deployed Reflex backend."""

    return {"status": "ok", "product": "Veris"}


@api.get("/api/demo")
def demo_report(
    records: int = Query(default=750, ge=50, le=2000),
    seed: int = Query(default=42, ge=0),
) -> dict[str, Any]:
    """Generate a synthetic dataset and return the validation report."""

    return build_demo_report(records=records, seed=seed)


@api.post("/api/validate")
def validate_payload(
    records: list[dict[str, Any]] = Body(..., embed=True),
) -> dict[str, Any]:
    """Validate client-supplied KPI records."""

    return validate_records(records)
