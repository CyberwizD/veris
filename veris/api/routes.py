"""FastAPI routes exposed through Reflex's backend."""

from __future__ import annotations

from typing import Any

from fastapi import Body, FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware

from veris.engine.service import build_demo_report, validate_records

API_PREFIX = "/api"
VERSIONED_API_PREFIX = "/api/v1"

api = FastAPI(
    title="Veris API",
    description="DCP KPI validation trust layer prototype.",
    version="0.1.0",
)

api.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@api.get("/")
def root() -> dict[str, Any]:
    """Backend index for direct checks against the deployed backend URL."""

    return {
        "product": "Veris",
        "status": "ok",
        "endpoints": {
            "health": "/health",
            "demo": f"{API_PREFIX}/demo?records=750&seed=42",
            "validate": f"{API_PREFIX}/validate",
            "versioned_demo": f"{VERSIONED_API_PREFIX}/demo?records=750&seed=42",
        },
    }


@api.get("/health")
@api.get(f"{API_PREFIX}/health")
@api.get(f"{VERSIONED_API_PREFIX}/health")
def health() -> dict[str, str]:
    """Health check for deployed Reflex backend."""

    return {"status": "ok", "product": "Veris", "backend": "reflex"}


@api.get(f"{API_PREFIX}/demo")
@api.get(f"{VERSIONED_API_PREFIX}/demo")
def demo_report(
    records: int = Query(default=750, ge=50, le=2000),
    seed: int = Query(default=42, ge=0),
) -> dict[str, Any]:
    """Generate a synthetic dataset and return the validation report."""

    return build_demo_report(records=records, seed=seed)


@api.post(f"{API_PREFIX}/validate")
@api.post(f"{VERSIONED_API_PREFIX}/validate")
def validate_payload(
    records: list[dict[str, Any]] = Body(..., embed=True),
) -> dict[str, Any]:
    """Validate client-supplied KPI records."""

    return validate_records(records)
