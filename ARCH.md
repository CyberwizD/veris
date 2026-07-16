# Veris Architecture

## Overview

Veris is a **DCP KPI validation trust layer** prototype that validates cement plant KPI (Key Performance Indicator) data through a dual-interface architecture:

- **Reflex backend**: Full-stack Python web framework hosting FastAPI routes for validation logic
- **Streamlit dashboard**: Judge-facing UI for visualizing validation reports and synthetic demo data

The system validates synthetic or uploaded KPI records against a set of deterministic rules, computes Data Quality Scores (DQS), and provides detailed failure attribution.

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                         Streamlit Dashboard                      │
│                         (web/app.py)                             │
│  - Judge-facing UI                                               │
│  - Synthetic demo controls                                       │
│  - File upload validation                                        │
│  - Report visualization                                          │
└────────────────────────────┬────────────────────────────────────┘
                             │ HTTP/JSON
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                         Reflex Backend                            │
│                         (veris/veris.py)                         │
│  - FastAPI routes (veris/api/routes.py)                          │
│  - API transformer mount                                         │
│  - Minimal Reflex state                                          │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Validation Engine Core                        │
│                       (veris/engine/)                            │
├─────────────────────────────────────────────────────────────────┤
│  service.py          │  Orchestration layer                      │
│                      │  - validate_records()                     │
│                      │  - build_demo_report()                    │
├─────────────────────────────────────────────────────────────────┤
│  generator.py        │  Synthetic data generation                │
│                      │  - generate_synthetic_dataset()          │
│                      │  - inject_known_failures()                │
├─────────────────────────────────────────────────────────────────┤
│  rules.py            │  Validation rule engine                   │
│                      │  - validate_dataframe()                   │
│                      │  - 8 deterministic rules                  │
├─────────────────────────────────────────────────────────────────┤
│  dqs.py              │  Data Quality Score calculation           │
│                      │  - summarize_quality()                    │
│                      │  - summarize_batches()                    │
├─────────────────────────────────────────────────────────────────┤
│  schema.py           │  Pydantic record contract                 │
│                      │  - KpiRecord model                        │
├─────────────────────────────────────────────────────────────────┤
│  constants.py        │  Shared validation constants              │
│                      │  - Plant/shift/source enums               │
│                      │  - Range bounds, thresholds               │
└─────────────────────────────────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                      CLI Interface                               │
│                      (cli.py)                                    │
│  - Demo runner for testing                                      │
│  - JSON output for debugging                                     │
└─────────────────────────────────────────────────────────────────┘
```

## Component Breakdown

### 1. Reflex Backend (`veris/`)

**Purpose**: Hosts the validation engine as a FastAPI application through Reflex's API transformer.

**Key Files**:
- `veris/veris.py`: Reflex app shell with minimal state, mounts FastAPI routes
- `veris/api/routes.py`: FastAPI endpoint definitions
  - `GET /api/health`: Health check
  - `GET /api/demo`: Generate synthetic data with validation
  - `POST /api/validate`: Validate client-supplied records

**Configuration** (`rxconfig.py`):
- App name: `veris`
- Plugins: Sitemap, Radix Themes, Tailwind CSS v4

### 2. Streamlit Dashboard (`web/`)

**Purpose**: Judge-facing UI for interacting with the validation engine.

**Key File**: `web/app.py`

**Features**:
- API connection controls with health check
- Two data source modes:
  - **Synthetic demo**: Configurable record count and seed for reproducible demos
  - **Upload records**: CSV/JSON file upload for custom validation
- Report visualization:
  - Data Quality Score (DQS) metrics
  - Rule failure bar charts
  - Failed records table with attribution
  - Batch-level DQS breakdown by plant/line/shift
  - Planted demo issue summary (for synthetic data)

**API Integration**:
- Uses `requests` library to call Reflex backend endpoints
- Configurable API base URL via `VERIS_API_BASE_URL` environment variable
- Session state caching for reports

### 3. Validation Engine (`veris/engine/`)

**Purpose**: Core business logic for data generation, validation, and quality scoring.

#### 3.1 Service Layer (`service.py`)
- `validate_records()`: Entry point for validation, accepts list/dict/DataFrame
- `build_demo_report()`: Orchestrates synthetic generation + validation
- `_report_from_validated()`: Formats validation results into API response structure
- `_records_for_api()`: Serializes DataFrames for JSON response (datetime handling)

#### 3.2 Data Generator (`generator.py`)
- `generate_synthetic_dataset()`: Creates realistic cement plant KPI records
  - Configurable record count (50-2000), seed for reproducibility
  - Plant/line/shift distribution with realistic weights
  - Source distribution: sensor (78%), manual_log (14%), lims (8%)
  - Physically plausible KPI values with plant-specific scaling
- `inject_known_failures()`: Plants deterministic bad data patterns for demos
  - Schema type violations (non-numeric in numeric fields)
  - Mass balance violations (kiln feed/clinker ratio out of bounds)
  - Range violations (values outside physical limits)
  - Enum violations (invalid fault codes)
  - Attribution failures (manual logs without operator)
  - Stale sensor detection (frozen vibration readings)

#### 3.3 Validation Rules (`rules.py`)
Implements 8 deterministic validation rules:

1. **Required field check**: Ensures all mandatory fields are present and non-empty
2. **Schema/type coercion**: Validates numeric and timestamp fields, flags non-numeric values
3. **Enum validation**: Checks plant_id, shift, source, fault_code against approved taxonomies
4. **Future timestamp check**: Rejects timestamps in the future
5. **Range validation**: Ensures numeric KPIs are within physical bounds
6. **Mass balance check**: Validates kiln feed to clinker output ratio (1.55-1.66)
7. **Stale sensor check**: Detects frozen sensor readings using rolling standard deviation
8. **Attribution check**: Ensures manual log entries have operator attribution

**Output**: Each record gets:
- `validation_flags`: List of failed rule codes
- `validation_status`: "passed" or "failed"
- `flag_count`: Number of failures
- `record_dqs`: Per-record quality score (0-100%)
- `validation_notes`: Human-readable rule descriptions

#### 3.4 Data Quality Score (`dqs.py`)
- `summarize_quality()`: Computes batch-level DQS using PRD/TRD formula
  - DQS = (passed_records / total_records) × 100
  - Status: green (≥95%) or amber (<95%)
- `summarize_batches()`: Computes DQS per plant/line/shift combination
- Classification:
  - `passed_records`: No flags
  - `failed_records`: Non-null/stale flags
  - `null_records`: Missing values or unattributed entries
  - `stale_records`: Stale sensor flags

#### 3.5 Schema (`schema.py`)
- `KpiRecord`: Pydantic BaseModel defining the canonical record contract
- Type aliases for enums: `PlantId`, `Shift`, `Source`, `FaultCode`
- Used for API documentation and test validation

#### 3.6 Constants (`constants.py`)
Centralized validation configuration:
- Plant taxonomy (OBJ, IBS, GBK, OKP)
- Shift taxonomy (A, B, C)
- Source taxonomy (sensor, manual_log, lims)
- Fault code taxonomy with descriptions
- Numeric field list and range bounds
- Mass balance ratio limits (1.55-1.66)
- Stale sensor window (3 records)
- DQS alert threshold (95%)
- Human-readable rule labels

### 4. CLI Interface (“cli.py)

**Purpose**: Command-line tool for testing and debugging the validation engine.

**Usage**:
```bash
python cli.py --records 750 --seed 42
```

**Output**: JSON-formatted validation report to stdout.

## Data Flow

### Synthetic Demo Flow
1. User configures record count and seed in Streamlit sidebar
2. Streamlit calls `GET /api/demo?records=N&seed=S`
3. Reflex route calls `build_demo_report()`
4. Engine generates synthetic dataset with injected failures
5. Engine validates the dataset using all 8 rules
6. Engine computes DQS and batch summaries
7. Response returned to Streamlit as JSON
8. Streamlit renders metrics, charts, and tables

### Upload Validation Flow
1. User uploads CSV/JSON file in Streamlit
2. Streamlit parses file into record list
3. Streamlit calls `POST /api/validate` with records payload
4. Reflex route calls `validate_records()`
5. Engine validates using all 8 rules
6. Engine computes DQS and batch summaries
7. Response returned to Streamlit as JSON
8. Streamlit renders validation report

## Technology Stack

- **Reflex 0.9.6.post2**: Full-stack Python web framework for backend
- **FastAPI**: REST API framework (mounted via Reflex)
- **Streamlit 1.40+**: Dashboard UI framework
- **Pandas**: Data manipulation and analysis
- **NumPy**: Numerical operations for synthetic data generation
- **Pydantic**: Data validation and schema definition
- **Requests**: HTTP client for Streamlit→Reflex communication

## Deployment Considerations

### Reflex Backend
- Deployed as a Reflex app with `reflex run` or `reflex deploy`
- Exposes FastAPI routes at `/api/*` endpoints
- Requires Python environment with dependencies from `requirements.txt`

### Streamlit Dashboard
- Runs independently with `streamlit run web/app.py`
- Requires Reflex backend URL via `VERIS_API_BASE_URL` environment variable
- Can connect to local or deployed Reflex instance

### Separation of Concerns
- Validation engine is framework-agnostic (pure Python/Pandas)
- Can be imported and used independently by CLI, tests, or other services
- No Reflex or Streamlit dependencies in core engine

## Extension Points

1. **New validation rules**: Add functions to `rules.py` and call in `validate_dataframe()`
2. **Additional KPI fields**: Extend `schema.py` and `constants.py`
3. **Custom data sources**: Modify `generator.py` for new synthetic patterns
4. **Alternative frontends**: Engine can be consumed by any HTTP client via FastAPI routes
5. **Batch processing**: Service layer accepts DataFrames for bulk operations
