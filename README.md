# Veris: DCP KPI Validation Engine (Trust Layer Prototype)

> **Digital KPI Automation & Data Quality — Dangote Cement PLC (DCP) University Engineering Challenge**
> **Scope: Phase 1 Pilot Prototype**

[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue.svg)](https://www.python.org/)
[![Reflex 0.9.6](https://img.shields.io/badge/Reflex-0.9.6-red.svg)](https://reflex.dev/)
[![Streamlit 1.40+](https://img.shields.io/badge/Streamlit-1.40%2B-brightgreen.svg)](https://streamlit.io/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115%2B-009688.svg)](https://fastapi.tiangolo.com/)

---

## 1. Executive Summary & Strategic Purpose

Reporting Key Performance Indicators (KPIs) across Dangote Cement PLC's (DCP) four major plant sites—**Obajana (OBJ)**, **Ibese (IBS)**, **Gboko (GBK)**, and **Okpella (OKP)**—traditionally relies on manual, shift-based operator entries. This reliance results in reporting delays, inconsistent formatting, untraceable manual entries, and a lack of verification mechanisms for identifying faulty sensor readings.

**Veris** is a working **KPI validation trust layer** prototype designed to solve these issues. Operating entirely on the **IT/reporting side** (ensuring absolute isolation from physical operational technology (OT) systems for cyber and physical safety), Veris ingests raw KPI data, processes it through an **ALCOA+-grounded rules engine**, and computes a standardized **Data Quality Score (DQS)**.

This prototype provides immediate, verifiable proof of the "trust layer" concept, demonstrating to the DCP screening team how deterministic, physics-based, and structural checks can flag bad data before it reaches executive dashboards or compliance reports.

### Key Documents & Context

This prototype is built strictly in accordance with:

- [05_Prototype_Technical_Spec.md](file:///Users/great/Desktop/python/veris/05_Prototype_Technical_Spec.md) (TRD): Technical data models, validation rule logic, and scoring formulas.
- [06_Product_Requirements_Document.md](file:///Users/great/Desktop/python/veris/06_Product_Requirements_Document.md) (PRD): User personas, functional/non-functional requirements, and scoping.
- [ARCH.md](file:///Users/great/Desktop/python/veris/ARCH.md): Multi-layer backend/frontend architecture and API schemas.

---

## 2. Core Features

### 1. Deterministic Rules Engine

Processes every record against 8 specific rules, producing independent pass/fail/flag logs:

- **Required Field Check:** Checks for nulls or missing values in mandatory fields.
- **Schema & Type Coercion:** Ensures numeric columns contain valid floats and blocks non-numeric entries (e.g., catching when an operator types `"OFL"` into a tonnage field).
- **Enum Taxonomy Validation:** Enforces standardized lists for `plant_id` (OBJ, IBS, GBK, OKP), `shift` (A, B, C), `source` (sensor, manual_log, lims), and `fault_code`.
- **Future Timestamp Prevention:** Flags any records stamped in the future.
- **Plausible Physical Range Checks:** Flags entries outside realistic physical boundaries (e.g., kiln feed, thermal SEC, electrical SEC, free lime).
- **Physics-Grounded Mass-Balance Check:** The signature demo check. Assesses the feed-to-clinker ratio:
  $$\text{Ratio} = \frac{\text{kiln\_feed\_tph}}{\text{clinker\_output\_tph}}$$
  Flags the record if the ratio falls outside the standard range of **1.55 to 1.66**.
- **Stale/Frozen Sensor Detection:** Identifies frozen sensors by checking for zero variance (`std = 0`) over a rolling window of 3 consecutive vibration readings.
- **ALCOA+ Operator Attribution:** Flags any manual log entries that lack operator attribution (`entered_by`).

### 2. Standardized Fault Taxonomy

Replaces inconsistent, free-text entries (e.g., "drive trip" vs. "Electrical Fault") with an enforced Enum schema:

- `MECH_FAULT`: Mechanical failure (bearing, belt, coupling).
- `ELEC_FAULT`: Electrical failure (drive, motor, wiring).
- `PROC_INSTAB`: Process instability (feed surge, blockage).
- `INSTR_FAULT`: Instrumentation/sensor fault.
- `PLANNED_STOP`: Scheduled maintenance or inspection.
- `UNKNOWN`: Uncategorized entries (targeted to trend toward zero).

### 3. Data Quality Score (DQS) Formula

Computes a percentage-based reliability score at the record, shift, line, and plant level:
$$\text{DQS} = \left( \frac{\text{passed\_records}}{\text{passed\_records} + \text{failed\_records} + \text{null\_records} + \text{stale\_records}} \right) \times 100$$

- **Green Status:** $\ge 95\%$ DQS (Trustworthy batch).
- **Amber/Red Status:** $< 95\%$ DQS (Alert status; requires supervisor review).

### 4. Synthetic Data & Plant Contrast

Generates plausible historical plant datasets containing realistic noise and plant-specific weights. It contrasts a modern plant (**Obajana**) with a legacy one (**Gboko**), intentionally injecting a higher failure rate in Gboko's data to demonstrate how the engine exposes systemic, localized data-entry issues.

---

## 3. Architecture & Data Flow

Veris uses a decoupled, dual-interface architecture:

1.  **Core Validation Engine:** Framework-agnostic Python/Pandas logic.
2.  **Reflex API Backend:** Exposes FastAPI endpoints for remote validation services.
3.  **Streamlit Dashboard:** A judge-facing, interactive GUI.
4.  **CLI Runner:** A command-line script for quick local evaluations.

```
┌──────────────────────────────┐
│      Streamlit Dashboard     │ <--- User-facing GUI for uploads
│         (web/app.py)         │      and report viewing
└──────────────┬───────────────┘
               │ HTTP / JSON
               ▼
┌──────────────────────────────┐
│     Reflex Backend (API)     │ <--- FastAPI server hosting endpoints:
│       (veris/veris.py)       │      /api/health, /api/demo, /api/validate
└──────────────┬───────────────┘
               │
               ▼
┌──────────────────────────────┐
│    Validation Engine Core    │ <--- Deterministic Rules Engine,
│       (veris/engine/)        │      DQS formulas, and data generator
└──────────────┬───────────────┘
               │
               ▼
┌──────────────────────────────┐
│         CLI interface        │ <--- Fast JSON output to terminal
│           (cli.py)           │      for debugging & automation
└──────────────────────────────┘
```

---

## 4. Prerequisites & Setup

### System Requirements

- **Python:** version `3.10`, `3.11`, or `3.12` installed.
- **Operating System:** macOS, Linux, or Windows.
- **Network:** The application runs entirely **offline**; internet access is only needed during initial dependency installation.

### Installation Instructions

Choose **one** of the two setup paths below:

#### Path A: Setup via Poetry (Recommended)

If you have Poetry installed on your system:

```bash
# 1. Install project dependencies (including development tools)
poetry install

# 2. Activate the Poetry virtual environment shell
poetry shell
```

#### Path B: Setup via Standard pip & venv

If you prefer a standard Python virtual environment:

```bash
# 1. Create a virtual environment named .venv
python3 -m venv .venv

# 2. Activate the virtual environment
# On macOS/Linux:
source .venv/bin/activate
# On Windows (cmd):
.venv\Scripts\activate.bat
# On Windows (PowerShell):
.venv\Scripts\Activate.ps1

# 3. Upgrade pip and install dependencies
pip install --upgrade pip
pip install -r requirements.txt
```

---

## 5. Running the Application

To demo the complete system, you must start the **Reflex API Backend** and the **Streamlit Dashboard** in separate terminal windows.

### Step 1: Run the Backend API Server

Choose one of the following commands from your project root directory (with your virtual environment active):

```bash
# Option 1: Direct FastAPI entrypoint (Fastest & Simplest)
python main.py

# Option 2: Run via the Reflex Framework CLI
reflex run
```

_The backend API server will start on **`http://localhost:8000`**._

### Step 2: Run the Streamlit Dashboard

In a new terminal window (ensure the virtual environment is activated here too), run:

```bash
streamlit run web/app.py
```

_This command will automatically open the interactive GUI in your default web browser at **`http://localhost:8501`**._

### Alternative: Run the CLI Demo

If you want to bypass the web interface and see raw validation payloads directly in your terminal:

```bash
python cli.py --records 500 --seed 123
```

_This prints a structured JSON validation report to `stdout` containing the calculated DQS, batch rollups, and flagged records._

### Running the Test Suite

To verify the rules engine and API routes work as expected, execute the unit tests:

```bash
# Using standard virtual environment:
python -m pytest
# or:
PYTHONPATH=. pytest

# Using Poetry:
poetry run python -m pytest
```

---

## 6. Interactive Dashboard Walkthrough

_Designed for the DCP Screening Team to review the live system._

When you open **`http://localhost:8501`** in your browser, follow these steps to explore the prototype:

### Sidebar Control Panel

1.  **Backend Connection:** The `Reflex API base URL` defaults to `http://localhost:8000`. Click the **Check API** button. You should see a green success bubble indicating the backend is online.
2.  **Data Source Selector:** Toggle between:
    - **Synthetic demo:** Generates plant metrics with embedded faults.
    - **Upload records:** Lets you upload custom CSV or JSON files.

### 1. The Synthetic Demo Mode

1.  Set the **Records** slider (e.g., `750`) and enter a **Seed** (e.g., `42` for a repeatable run).
2.  Click **Run validation**.
3.  **Download CSV:** After the validation run finishes, a **Download CSV** button will appear in the sidebar. This allows you to export the generated raw plant records.

### 2. Custom File Upload Mode

1.  Switch the "Data source" toggle to **Upload records**.
2.  Drag and drop or browse for a custom CSV or JSON dataset.
    > [!TIP]
    > To test validation, export a CSV from the "Synthetic demo" mode, manually alter a few values (e.g., set `kiln_feed_tph` to `400` and `clinker_output_tph` to `100` to break the mass balance ratio), and upload the modified file to watch Veris flag it.
3.  Click **Validate upload**.

### 3. Understanding the Validation Report Screen

Once a report loads, the dashboard is divided into visual sections:

- **Key Performance Indicators (Top Row):**
  - **Data Quality Score:** The aggregated DQS for the entire batch. If it falls below the **95.00% threshold**, it displays an amber or red warning.
  - **Total Records / Passed Records / Flagged Records:** A high-level overview of processing volume.
- **Rule Counts & Injected Issues (Left Column):**
  - **Rule Counts Bar Chart:** Shows which validation rules were triggered most often. Hover over a bar to see how many records failed that specific check.
  - **Planted Demo Issues Table:** Summarizes the types of failures generated in the raw data, allowing you to cross-check what was injected versus what the rules engine successfully caught.
- **Failed Records Details (Right Column):**
  - An interactive grid displaying all flagged records.
  - It lists the `record_id`, `plant_id`, and `validation_flags` (e.g., `['mass_balance_violation']`), along with human-readable `validation_notes` explaining exactly _why_ the record failed.
- **Batch Quality Table (Bottom Row):**
  - A breakdown of data volume and DQS rolled up by `plant_id`, `line_id`, and `shift`.
  - This section highlights the data-quality gap between the modern **Obajana (OBJ)** plant and the legacy **Gboko (GBK)** plant.
- **API Payload Sample (Expandable Accordion):**
  - Click to expand and view the raw JSON payload exchanged between the Streamlit client and the Reflex API backend, demonstrating API contract conformance.

---

## 7. Configuration Details

All ranges, physical limits, and schema constants are defined in a single configuration file to prevent value drift. You can inspect or modify these settings in:

[`veris/engine/constants.py`](file:///Users/great/Desktop/python/veris/veris/engine/constants.py)

Key thresholds defined in the file include:

- **DQS Threshold:** `95.0%` (amber warning limit).
- **Mass Balance Ratio:** `1.55` to `1.66`.
- **Stale Sensor Rolling Window:** `3` consecutive readings.
- **KPI Plausible Ranges:**
  | Field | Unit | Plausible Range |
  |---|---|---|
  | `kiln_feed_tph` | tonnes/hour | $50.0 \rightarrow 500.0$ |
  | `clinker_output_tph` | tonnes/hour | $30.0 \rightarrow 350.0$ |
  | `thermal_energy_kcal_kg` | kcal/kg clinker | $600.0 \rightarrow 900.0$ |
  | `electrical_power_kwh_ton` | kWh/tonne cement | $60.0 \rightarrow 130.0$ |
  | `free_lime_pct` | % (LIMS) | $0.5 \rightarrow 3.5$ |
  | `id_fan_vibration_mm_s` | mm/second (vibration sensor) | $0.0 \rightarrow 12.0$ |

---

## 8. Directory Structure

```
veris/
├── README.md                      # This guide
├── pyproject.toml                 # Poetry dependencies and metadata
├── requirements.txt               # Standard pip requirements
├── cli.py                         # Command-line entrypoint for testing
├── main.py                        # Standalone Uvicorn/FastAPI API backend runner
├── rxconfig.py                    # Reflex framework configurations
├── veris/
│   ├── veris.py                   # Reflex app and minimal UI mounting page
│   ├── api/
│   │   └── routes.py              # FastAPI endpoints (/api/demo, /api/validate)
│   └── engine/                    # Core validation engine (UI-agnostic)
│       ├── constants.py           # Physical ranges, enums, & rules configs
│       ├── dqs.py                 # Data Quality Score calculation logic
│       ├── generator.py           # Synthetic KPI generator & error injection
│       ├── rules.py               # Enforces the 8 deterministic rules
│       ├── schema.py              # Pydantic data schemas
│       └── service.py             # Orchestrates generation + validation
├── web/
│   └── app.py                     # Streamlit frontend dashboard code
└── tests/
    └── test_engine.py             # Automated unit tests for engine and API
```

---

## 9. Phase 1 Verification Checklist

_The prototype satisfies the following Definition of Done criteria:_

- [x] **Isolated Operation:** No network calls or OT-side dependencies; runs 100% offline.
- [x] **Physics-Grounded Validation:** Features the signature kiln-feed/clinker ratio rule.
- [x] **Repeatable Demo Runs:** Synthetic generator uses seed-based reproducibility.
- [x] **Full Exception Logging:** Identifies specific rules failed by each record.
- [x] **Automated Verification:** 100% test coverage for all 8 validation rules.
