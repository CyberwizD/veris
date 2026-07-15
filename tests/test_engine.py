from __future__ import annotations

import pandas as pd
from fastapi.testclient import TestClient

from veris.api.routes import api
from veris.engine.generator import generate_synthetic_dataset
from veris.engine.service import build_demo_report, validate_records


def test_generator_injects_known_failures() -> None:
    df = generate_synthetic_dataset(records=300, seed=7)

    assert len(df) == 300
    assert df["injected_issue"].notna().sum() > 0
    assert "mass_balance_violation" in set(df["injected_issue"].dropna())


def test_validation_catches_signature_mass_balance_failure() -> None:
    df = pd.DataFrame(
        [
            {
                "record_id": "KPI-TEST-001",
                "plant_id": "OBJ",
                "line_id": "OBJ-L1",
                "timestamp": "2026-01-01T08:00:00+00:00",
                "shift": "A",
                "kiln_feed_tph": 320.0,
                "clinker_output_tph": 160.0,
                "thermal_energy_kcal_kg": 730.0,
                "electrical_power_kwh_ton": 90.0,
                "free_lime_pct": 1.6,
                "id_fan_vibration_mm_s": 4.2,
                "fault_code": None,
                "entered_by": "AUTO",
                "source": "sensor",
            }
        ]
    )

    report = validate_records(df)

    assert report["rule_counts"]["mass_balance_violation"] == 1
    assert report["failed_records"][0]["record_id"] == "KPI-TEST-001"


def test_validation_catches_stale_sensor_run() -> None:
    rows = []
    for idx in range(4):
        rows.append(
            {
                "record_id": f"KPI-ST-{idx}",
                "plant_id": "GBK",
                "line_id": "GBK-L1",
                "timestamp": f"2026-01-01T08:{idx * 10:02d}:00+00:00",
                "shift": "A",
                "kiln_feed_tph": 240.0,
                "clinker_output_tph": 150.0,
                "thermal_energy_kcal_kg": 730.0,
                "electrical_power_kwh_ton": 90.0,
                "free_lime_pct": 1.6,
                "id_fan_vibration_mm_s": 3.3,
                "fault_code": None,
                "entered_by": "AUTO",
                "source": "sensor",
            }
        )

    report = validate_records(rows)

    assert report["rule_counts"]["stale_sensor"] >= 2


def test_demo_report_is_api_serializable_and_scores_batch() -> None:
    report = build_demo_report(records=200, seed=11)

    assert report["metadata"]["product"] == "Veris"
    assert report["quality"]["dqs"] < 100
    assert report["batch_summary"]
    assert report["failed_records"]


def test_demo_endpoint_returns_streamlit_ready_payload() -> None:
    client = TestClient(api)

    health = client.get("/health")
    assert health.status_code == 200
    assert health.json()["backend"] == "reflex"

    response = client.get("/api/demo", params={"records": 100, "seed": 13})

    assert response.status_code == 200
    payload = response.json()
    assert payload["metadata"]["product"] == "Veris"
    assert payload["quality"]["counts"]["passed_records"] > 0
    assert payload["failed_records"]

    versioned = client.get("/api/v1/demo", params={"records": 100, "seed": 13})
    assert versioned.status_code == 200
    assert versioned.json()["quality"]["dqs"] == payload["quality"]["dqs"]
