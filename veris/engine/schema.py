"""Pydantic schema for KPI records."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict

PlantId = Literal["OBJ", "IBS", "GBK", "OKP"]
Shift = Literal["A", "B", "C"]
Source = Literal["sensor", "manual_log", "lims"]
FaultCode = Literal[
    "MECH_FAULT",
    "ELEC_FAULT",
    "PROC_INSTAB",
    "INSTR_FAULT",
    "PLANNED_STOP",
    "UNKNOWN",
]


class KpiRecord(BaseModel):
    """Expected shape of one KPI reading.

    The validator still reports failures instead of rejecting the full dataset;
    this model is used by tests and API docs as the canonical record contract.
    """

    model_config = ConfigDict(extra="allow")

    record_id: str
    plant_id: PlantId
    line_id: str
    timestamp: datetime
    shift: Shift
    kiln_feed_tph: float
    clinker_output_tph: float
    thermal_energy_kcal_kg: float
    electrical_power_kwh_ton: float
    free_lime_pct: float
    id_fan_vibration_mm_s: float
    fault_code: FaultCode | None = None
    entered_by: str = ""
    source: Source
