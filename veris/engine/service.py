"""Service functions shared by CLI, API, tests, and Streamlit."""

from __future__ import annotations

from typing import Any

import pandas as pd

from veris.engine.dqs import summarize_batches, summarize_quality
from veris.engine.generator import generate_synthetic_dataset
from veris.engine.rules import validate_dataframe


def validate_records(records: list[dict[str, Any]] | pd.DataFrame) -> dict[str, Any]:
    """Validate supplied KPI records and return a JSON-serializable report."""

    df = records.copy() if isinstance(records, pd.DataFrame) else pd.DataFrame(records)
    result = validate_dataframe(df)
    validated = result.records
    return _report_from_validated(validated, result.rule_counts)


def build_demo_report(records: int = 750, seed: int = 42) -> dict[str, Any]:
    """Generate synthetic demo data, validate it, and return a report."""

    raw = generate_synthetic_dataset(records=records, seed=seed, inject_failures=True)
    report = validate_records(raw)
    report["metadata"]["seed"] = seed
    report["metadata"]["generated_records"] = len(raw)
    report["metadata"]["injection_summary"] = (
        raw["injected_issue"].dropna().value_counts().sort_index().to_dict()
        if "injected_issue" in raw.columns
        else {}
    )
    return report


def _report_from_validated(validated: pd.DataFrame, rule_counts: dict[str, int]) -> dict[str, Any]:
    failed = validated[validated["validation_status"].eq("failed")].copy()
    failed = failed.sort_values(["flag_count", "record_id"], ascending=[False, True])

    passed = validated[validated["validation_status"].eq("passed")].copy()

    report = {
        "metadata": {
            "product": "Veris",
            "engine": "DCP KPI validation trust layer",
            "records": int(len(validated)),
            "rules": [
                "schema/type",
                "enum taxonomy",
                "range constraints",
                "mass balance",
                "stale sensor",
                "attribution",
            ],
        },
        "quality": summarize_quality(validated),
        "rule_counts": {key: int(value) for key, value in rule_counts.items()},
        "batch_summary": summarize_batches(validated),
        "failed_records": _records_for_api(failed.head(50)),
        "sample_records": _records_for_api(passed.head(12)),
        "all_records": _records_for_api(validated),
    }
    return report


def _records_for_api(df: pd.DataFrame) -> list[dict[str, Any]]:
    safe = df.copy()
    for column in safe.columns:
        if pd.api.types.is_datetime64_any_dtype(safe[column]):
            safe[column] = safe[column].astype(str)
    safe = safe.where(pd.notna(safe), None)
    return safe.to_dict(orient="records")
