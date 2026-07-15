"""Data Quality Score calculations."""

from __future__ import annotations

import pandas as pd

from veris.engine.constants import DQS_ALERT_THRESHOLD


def summarize_quality(df: pd.DataFrame) -> dict[str, object]:
    """Compute the PRD/TRD DQS formula across the full batch."""

    counts = _quality_counts(df)
    dqs = _dqs_from_counts(counts)
    return {
        "dqs": dqs,
        "status": "green" if dqs >= DQS_ALERT_THRESHOLD else "amber",
        "threshold": DQS_ALERT_THRESHOLD,
        "counts": counts,
    }


def summarize_batches(df: pd.DataFrame) -> list[dict[str, object]]:
    """Compute DQS per plant, line, and shift."""

    summaries: list[dict[str, object]] = []
    for keys, group in df.groupby(["plant_id", "line_id", "shift"], dropna=False):
        counts = _quality_counts(group)
        dqs = _dqs_from_counts(counts)
        plant_id, line_id, shift = keys
        summaries.append(
            {
                "plant_id": plant_id,
                "line_id": line_id,
                "shift": shift,
                "records": int(len(group)),
                "dqs": dqs,
                "status": "green" if dqs >= DQS_ALERT_THRESHOLD else "amber",
                "counts": counts,
            }
        )
    return sorted(summaries, key=lambda row: (str(row["plant_id"]), str(row["line_id"]), str(row["shift"])))


def _quality_counts(df: pd.DataFrame) -> dict[str, int]:
    flags = df["validation_flags"]
    passed = int(flags.map(len).eq(0).sum())
    stale = int(flags.map(lambda row: "stale_sensor" in row).sum())
    nulls = int(flags.map(lambda row: "missing_value" in row or "unattributed_entry" in row).sum())
    failed = int(
        flags.map(
            lambda row: bool(
                set(row)
                - {
                    "missing_value",
                    "unattributed_entry",
                    "stale_sensor",
                }
            )
        ).sum()
    )
    return {
        "passed_records": passed,
        "failed_records": failed,
        "null_records": nulls,
        "stale_records": stale,
    }


def _dqs_from_counts(counts: dict[str, int]) -> float:
    denominator = sum(counts.values())
    if denominator == 0:
        return 100.0
    return round((counts["passed_records"] / denominator) * 100.0, 2)
