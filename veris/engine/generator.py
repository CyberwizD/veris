"""Synthetic data generator for the Veris demo."""

from __future__ import annotations

from datetime import timedelta
from typing import Any

import numpy as np
import pandas as pd

from veris.engine.constants import DEMO_PLANTS, FAULT_CODES, SOURCES

PLANT_LINES = {
    "OBJ": ("OBJ-L1", "OBJ-L2", "OBJ-L3"),
    "GBK": ("GBK-L1", "GBK-L2"),
}


def generate_synthetic_dataset(
    records: int = 750,
    seed: int = 42,
    plants: tuple[str, ...] = DEMO_PLANTS,
    inject_failures: bool = True,
) -> pd.DataFrame:
    """Generate synthetic cement-plant KPI records.

    The dataset is intentionally export-like: flat records that could plausibly
    arrive from historian, LIMS, and shift-log sources. When ``inject_failures``
    is true, known bad records are planted for the live demo.
    """

    records = max(50, min(int(records), 2_000))
    rng = np.random.default_rng(seed)
    start = pd.Timestamp.now(tz="UTC").floor("min") - pd.Timedelta(days=3)
    plant_choices = np.array(plants)
    rows: list[dict[str, Any]] = []

    for idx in range(records):
        plant_id = str(rng.choice(plant_choices, p=_plant_weights(plant_choices)))
        line_id = str(rng.choice(PLANT_LINES.get(plant_id, (f"{plant_id}-L1",))))
        timestamp = start + pd.Timedelta(minutes=10 * idx)
        shift = _shift_for_timestamp(timestamp)
        source = str(rng.choice(SOURCES, p=(0.78, 0.14, 0.08)))

        plant_factor = 1.0 if plant_id == "OBJ" else 0.74
        clinker_output = max(35.0, rng.normal(185.0 * plant_factor, 12.0))
        ratio = rng.uniform(1.57, 1.64)
        kiln_feed = clinker_output * ratio

        has_fault = source == "manual_log" or rng.random() < (0.055 if plant_id == "GBK" else 0.025)
        fault_code = str(rng.choice(list(FAULT_CODES))) if has_fault else None
        entered_by = _entered_by(source, rng)

        rows.append(
            {
                "record_id": f"KPI-{idx + 1:05d}",
                "plant_id": plant_id,
                "line_id": line_id,
                "timestamp": timestamp.isoformat(),
                "shift": shift,
                "kiln_feed_tph": round(float(kiln_feed), 2),
                "clinker_output_tph": round(float(clinker_output), 2),
                "thermal_energy_kcal_kg": round(float(rng.normal(735.0, 32.0)), 2),
                "electrical_power_kwh_ton": round(float(rng.normal(91.0, 8.0)), 2),
                "free_lime_pct": round(float(rng.normal(1.65, 0.35)), 2),
                "id_fan_vibration_mm_s": round(float(rng.normal(4.4, 0.65)), 3),
                "fault_code": fault_code,
                "entered_by": entered_by,
                "source": source,
                "injected_issue": None,
            }
        )

    df = pd.DataFrame(rows)
    if inject_failures:
        df = inject_known_failures(df, seed=seed + 1009)
    return df


def inject_known_failures(df: pd.DataFrame, seed: int = 1051) -> pd.DataFrame:
    """Plant deterministic bad-data patterns for the judges' demo."""

    rng = np.random.default_rng(seed)
    mutated = df.copy()
    mutated["thermal_energy_kcal_kg"] = mutated["thermal_energy_kcal_kg"].astype(object)
    used: set[int] = set()

    def choose(count: int) -> np.ndarray:
        available = np.array([idx for idx in mutated.index if idx not in used])
        selected = rng.choice(available, size=min(count, len(available)), replace=False)
        used.update(int(idx) for idx in selected)
        return selected

    count = max(2, len(mutated) // 60)

    for idx in choose(count):
        mutated.at[idx, "thermal_energy_kcal_kg"] = "OFL"
        mutated.at[idx, "injected_issue"] = "schema_type_violation"

    for idx in choose(count):
        clinker = float(mutated.at[idx, "clinker_output_tph"])
        mutated.at[idx, "kiln_feed_tph"] = round(clinker * 1.82, 2)
        mutated.at[idx, "injected_issue"] = "mass_balance_violation"

    for idx in choose(count):
        mutated.at[idx, "free_lime_pct"] = 5.8
        mutated.at[idx, "injected_issue"] = "range_violation"

    manual_candidates = mutated.index[mutated["source"].eq("manual_log")].tolist()
    if len(manual_candidates) < count:
        extra = choose(count - len(manual_candidates))
        mutated.loc[extra, "source"] = "manual_log"
        manual_candidates.extend([int(idx) for idx in extra])
    for idx in rng.choice(np.array(manual_candidates), size=min(count, len(manual_candidates)), replace=False):
        mutated.at[int(idx), "entered_by"] = ""
        mutated.at[int(idx), "injected_issue"] = "unattributed_entry"

    for idx in choose(max(1, count // 2)):
        mutated.at[idx, "fault_code"] = "DRIVE_TRIP"
        mutated.at[idx, "injected_issue"] = "enum_violation"

    stale_line = "GBK-L1" if "GBK-L1" in set(mutated["line_id"]) else str(mutated["line_id"].iloc[0])
    
    stale_candidates = mutated.index[
        mutated["line_id"].eq(stale_line) & mutated["source"].isin(["sensor", "lims"])
    ].tolist()
    if len(stale_candidates) >= 3:
        for idx in stale_candidates[:3]:
            mutated.at[int(idx), "id_fan_vibration_mm_s"] = 3.333
            mutated.at[int(idx), "injected_issue"] = "stale_sensor"

    return mutated


def _plant_weights(plants: np.ndarray) -> tuple[float, ...]:
    weights = np.array([0.58 if plant == "OBJ" else 0.42 for plant in plants], dtype=float)
    weights = weights / weights.sum()
    return tuple(float(weight) for weight in weights)


def _shift_for_timestamp(timestamp: pd.Timestamp) -> str:
    hour = timestamp.hour
    if 6 <= hour < 14:
        return "A"
    if 14 <= hour < 22:
        return "B"
    return "C"


def _entered_by(source: str, rng: np.random.Generator) -> str:
    if source == "manual_log":
        return f"OP-{int(rng.integers(101, 165))}"
    if source == "lims":
        return f"LAB-{int(rng.integers(10, 30))}"
    return "AUTO"
