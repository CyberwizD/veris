"""Shared rule constants for Veris.

These values mirror the PRD/TRD and should stay in one place so the demo,
API, tests, and dashboard do not drift.
"""

from __future__ import annotations

PLANTS = {
    "OBJ": "Obajana",
    "IBS": "Ibese",
    "GBK": "Gboko",
    "OKP": "Okpella",
}

DEMO_PLANTS = ("OBJ", "GBK")

SHIFTS = ("A", "B", "C")
SOURCES = ("sensor", "manual_log", "lims")

FAULT_CODES = {
    "MECH_FAULT": "Mechanical failure",
    "ELEC_FAULT": "Electrical failure",
    "PROC_INSTAB": "Process instability",
    "INSTR_FAULT": "Instrumentation/sensor fault",
    "PLANNED_STOP": "Scheduled maintenance/inspection",
    "UNKNOWN": "Not yet categorized",
}

NUMERIC_FIELDS = (
    "kiln_feed_tph",
    "clinker_output_tph",
    "thermal_energy_kcal_kg",
    "electrical_power_kwh_ton",
    "free_lime_pct",
    "id_fan_vibration_mm_s",
)

REQUIRED_FIELDS = (
    "record_id",
    "plant_id",
    "line_id",
    "timestamp",
    "shift",
    *NUMERIC_FIELDS,
    "source",
)

RANGE_BOUNDS = {
    "kiln_feed_tph": (50.0, 500.0),
    "clinker_output_tph": (30.0, 350.0),
    "thermal_energy_kcal_kg": (600.0, 900.0),
    "electrical_power_kwh_ton": (60.0, 130.0),
    "free_lime_pct": (0.5, 3.5),
    "id_fan_vibration_mm_s": (0.0, 12.0),
}

MASS_BALANCE_MIN = 1.55
MASS_BALANCE_MAX = 1.66
STALE_WINDOW_RECORDS = 3
DQS_ALERT_THRESHOLD = 95.0

RULE_LABELS = {
    "missing_value": "Required value is missing.",
    "schema_type_violation": "Value does not match the expected schema/type.",
    "enum_violation": "Enum value is outside the approved taxonomy.",
    "future_timestamp": "Timestamp is in the future.",
    "range_violation": "Numeric reading is outside plausible physical bounds.",
    "mass_balance_violation": "Kiln feed to clinker output ratio is outside 1.55-1.66.",
    "stale_sensor": "Normally noisy vibration reading is frozen over the rolling window.",
    "unattributed_entry": "Manual log entry is missing the operator/shift attribution.",
}
