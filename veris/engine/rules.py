"""Deterministic validation rules for KPI records."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pandas as pd

from veris.engine.constants import (
    FAULT_CODES,
    MASS_BALANCE_MAX,
    MASS_BALANCE_MIN,
    NUMERIC_FIELDS,
    PLANTS,
    RANGE_BOUNDS,
    REQUIRED_FIELDS,
    RULE_LABELS,
    SHIFTS,
    SOURCES,
    STALE_WINDOW_RECORDS,
)


@dataclass(frozen=True)
class ValidationResult:
    """Validated dataframe plus aggregate summaries."""

    records: pd.DataFrame
    rule_counts: dict[str, int]


def validate_dataframe(df: pd.DataFrame) -> ValidationResult:
    """Validate records and attach flags, explanations, and per-record DQS."""

    work = df.copy()
    flags: list[list[str]] = [[] for _ in range(len(work))]

    _apply_required_checks(work, flags)
    numeric = _coerce_numeric(work, flags)
    timestamps = _coerce_timestamps(work, flags)
    _apply_enum_checks(work, flags)
    _apply_future_timestamp_check(timestamps, flags)
    _apply_range_checks(numeric, flags)
    _apply_mass_balance_check(numeric, flags)
    _apply_stale_sensor_check(work, numeric, timestamps, flags)
    _apply_attribution_check(work, flags)

    unique_flags = [_unique(row_flags) for row_flags in flags]
    work["validation_flags"] = unique_flags
    work["validation_status"] = ["passed" if not row_flags else "failed" for row_flags in unique_flags]
    work["flag_count"] = [len(row_flags) for row_flags in unique_flags]
    work["record_dqs"] = [round(100.0 * max(0, 8 - len(row_flags)) / 8, 2) for row_flags in unique_flags]
    work["validation_notes"] = [
        [RULE_LABELS.get(flag, flag) for flag in row_flags] for row_flags in unique_flags
    ]

    rule_counts = {
        flag: sum(flag in row_flags for row_flags in unique_flags)
        for flag in sorted({flag for row_flags in unique_flags for flag in row_flags})
    }
    return ValidationResult(records=work, rule_counts=rule_counts)


def _apply_required_checks(df: pd.DataFrame, flags: list[list[str]]) -> None:
    for field in REQUIRED_FIELDS:
        if field not in df.columns:
            for row_flags in flags:
                row_flags.append("missing_value")
            continue
        missing = df[field].isna() | df[field].astype(str).str.strip().eq("")
        for pos, is_missing in enumerate(missing.tolist()):
            if is_missing:
                flags[pos].append("missing_value")


def _coerce_numeric(df: pd.DataFrame, flags: list[list[str]]) -> dict[str, pd.Series]:
    numeric: dict[str, pd.Series] = {}
    for field in NUMERIC_FIELDS:
        if field not in df.columns:
            numeric[field] = pd.Series([pd.NA] * len(df), index=df.index)
            continue
        coerced = pd.to_numeric(df[field], errors="coerce")
        invalid = df[field].notna() & coerced.isna()
        for pos, is_invalid in enumerate(invalid.tolist()):
            if is_invalid:
                flags[pos].append("schema_type_violation")
        numeric[field] = coerced
    return numeric


def _coerce_timestamps(df: pd.DataFrame, flags: list[list[str]]) -> pd.Series:
    if "timestamp" not in df.columns:
        return pd.Series([pd.NaT] * len(df), index=df.index)
    parsed = pd.to_datetime(df["timestamp"], errors="coerce", utc=True)
    invalid = df["timestamp"].notna() & parsed.isna()
    for pos, is_invalid in enumerate(invalid.tolist()):
        if is_invalid:
            flags[pos].append("schema_type_violation")
    return parsed


def _apply_enum_checks(df: pd.DataFrame, flags: list[list[str]]) -> None:
    enum_sets: dict[str, set[str]] = {
        "plant_id": set(PLANTS),
        "shift": set(SHIFTS),
        "source": set(SOURCES),
    }
    for field, allowed in enum_sets.items():
        if field not in df.columns:
            continue
        invalid = ~df[field].isin(allowed)
        for pos, is_invalid in enumerate(invalid.fillna(False).tolist()):
            if is_invalid:
                flags[pos].append("enum_violation")

    if "fault_code" in df.columns:
        fault_values = df["fault_code"]
        has_value = fault_values.notna() & fault_values.astype(str).str.strip().ne("")
        invalid_fault = has_value & ~fault_values.isin(set(FAULT_CODES))
        for pos, is_invalid in enumerate(invalid_fault.tolist()):
            if is_invalid:
                flags[pos].append("enum_violation")


def _apply_future_timestamp_check(timestamps: pd.Series, flags: list[list[str]]) -> None:
    now = pd.Timestamp.now(tz="UTC")
    future = timestamps.notna() & (timestamps > now)
    for pos, is_future in enumerate(future.tolist()):
        if is_future:
            flags[pos].append("future_timestamp")


def _apply_range_checks(numeric: dict[str, pd.Series], flags: list[list[str]]) -> None:
    for field, (lower, upper) in RANGE_BOUNDS.items():
        series = numeric[field]
        out_of_range = series.notna() & ((series < lower) | (series > upper))
        for pos, is_out_of_range in enumerate(out_of_range.tolist()):
            if is_out_of_range:
                flags[pos].append("range_violation")


def _apply_mass_balance_check(numeric: dict[str, pd.Series], flags: list[list[str]]) -> None:
    feed = numeric["kiln_feed_tph"]
    clinker = numeric["clinker_output_tph"]
    valid_inputs = feed.notna() & clinker.notna() & clinker.ne(0)
    ratio = feed / clinker
    invalid = valid_inputs & ((ratio < MASS_BALANCE_MIN) | (ratio > MASS_BALANCE_MAX))
    for pos, is_invalid in enumerate(invalid.tolist()):
        if is_invalid:
            flags[pos].append("mass_balance_violation")


def _apply_stale_sensor_check(
    df: pd.DataFrame,
    numeric: dict[str, pd.Series],
    timestamps: pd.Series,
    flags: list[list[str]],
) -> None:
    if "line_id" not in df.columns:
        return
    helper = pd.DataFrame(
        {
            "line_id": df["line_id"],
            "timestamp": timestamps,
            "vibration": numeric["id_fan_vibration_mm_s"],
            "_pos": range(len(df)),
        }
    ).dropna(subset=["line_id", "timestamp", "vibration"])

    helper = helper.sort_values(["line_id", "timestamp"])
    rolling_std = (
        helper.groupby("line_id")["vibration"]
        .rolling(window=STALE_WINDOW_RECORDS, min_periods=STALE_WINDOW_RECORDS)
        .std()
        .reset_index(level=0, drop=True)
    )
    stale_positions = helper.loc[rolling_std.eq(0).fillna(False), "_pos"].astype(int).tolist()
    for pos in stale_positions:
        flags[pos].append("stale_sensor")


def _apply_attribution_check(df: pd.DataFrame, flags: list[list[str]]) -> None:
    if "source" not in df.columns or "entered_by" not in df.columns:
        return
    missing_actor = df["entered_by"].isna() | df["entered_by"].astype(str).str.strip().eq("")
    unattributed = df["source"].eq("manual_log") & missing_actor
    for pos, is_unattributed in enumerate(unattributed.tolist()):
        if is_unattributed:
            flags[pos].append("unattributed_entry")


def _unique(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if value not in seen:
            seen.add(value)
            result.append(value)
    return result
