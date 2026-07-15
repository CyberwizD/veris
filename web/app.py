"""Streamlit dashboard for the Veris Reflex API."""

from __future__ import annotations

import json
import os
from typing import Any

import pandas as pd
import requests
import streamlit as st

DEFAULT_API_BASE_URL = os.getenv("VERIS_API_BASE_URL", "http://localhost:8000")


st.set_page_config(
    page_title="Veris | DCP KPI Trust Layer",
    page_icon="V",
    layout="wide",
    initial_sidebar_state="expanded",
)


def main() -> None:
    _apply_style()

    st.title("Veris")
    st.caption("DCP KPI validation trust layer")

    api_base_url = _sidebar_api_controls()
    mode = st.sidebar.segmented_control(
        "Data source",
        options=["Synthetic demo", "Upload records"],
        default="Synthetic demo",
    )

    report: dict[str, Any] | None = None
    if mode == "Synthetic demo":
        report = _synthetic_demo_controls(api_base_url)
    else:
        report = _upload_controls(api_base_url)

    if report:
        _render_report(report)
    else:
        _render_empty_state(api_base_url)


def _sidebar_api_controls() -> str:
    st.sidebar.header("Backend")
    api_base_url = st.sidebar.text_input(
        "Reflex API base URL",
        value=DEFAULT_API_BASE_URL,
        help="Use the deployed Reflex backend URL for the live judge-facing dashboard.",
    ).strip()
    api_base_url = api_base_url.rstrip("/")

    if st.sidebar.button("Check API", use_container_width=True):
        try:
            payload = _get_json(f"{api_base_url}/api/health")
        except requests.RequestException as exc:
            st.sidebar.error(f"API unavailable: {exc}")
        else:
            st.sidebar.success(f"{payload.get('product', 'API')} is online")

    st.sidebar.divider()
    return api_base_url


def _synthetic_demo_controls(api_base_url: str) -> dict[str, Any] | None:
    st.sidebar.header("Demo Run")
    records = st.sidebar.slider("Records", min_value=50, max_value=2000, value=750, step=50)
    seed = st.sidebar.number_input("Seed", min_value=0, max_value=999999, value=42, step=1)

    auto_load = "report" not in st.session_state
    run_clicked = st.sidebar.button("Run validation", type="primary", use_container_width=True)

    if auto_load or run_clicked:
        with st.spinner("Generating synthetic plant KPI data and validating it..."):
            try:
                st.session_state.report = _get_json(
                    f"{api_base_url}/api/demo",
                    params={"records": records, "seed": int(seed)},
                )
            except requests.RequestException as exc:
                st.error(f"Could not reach the Reflex API at `{api_base_url}`: {exc}")
                st.session_state.report = None

    return st.session_state.get("report")


def _upload_controls(api_base_url: str) -> dict[str, Any] | None:
    st.sidebar.header("Validate Upload")
    uploaded = st.sidebar.file_uploader("CSV or JSON records", type=["csv", "json"])

    if uploaded is None:
        return None

    try:
        records = _read_uploaded_records(uploaded)
    except ValueError as exc:
        st.error(str(exc))
        return None

    st.sidebar.write(f"{len(records):,} records loaded")
    if st.sidebar.button("Validate upload", type="primary", use_container_width=True):
        with st.spinner("Sending records to the Reflex validation endpoint..."):
            try:
                st.session_state.upload_report = _post_json(
                    f"{api_base_url}/api/validate",
                    payload={"records": records},
                )
            except requests.RequestException as exc:
                st.error(f"Could not validate uploaded records: {exc}")
                st.session_state.upload_report = None

    return st.session_state.get("upload_report")


def _render_report(report: dict[str, Any]) -> None:
    quality = report["quality"]
    counts = quality["counts"]
    metadata = report["metadata"]

    left, mid, right, last = st.columns(4)
    left.metric("Data Quality Score", f"{quality['dqs']:.2f}%", quality["status"].upper())
    mid.metric("Records", f"{metadata['records']:,}")
    right.metric("Passed", f"{counts['passed_records']:,}")
    last.metric("Flagged", f"{len(report['failed_records']):,}")

    st.divider()

    summary_col, failures_col = st.columns([0.95, 1.35], gap="large")
    with summary_col:
        st.subheader("Rule Counts")
        rule_counts = _series_frame(report.get("rule_counts", {}), "rule", "records")
        if rule_counts.empty:
            st.success("No rule failures detected.")
        else:
            st.bar_chart(rule_counts, x="rule", y="records", height=280)

        injection_summary = metadata.get("injection_summary") or {}
        if injection_summary:
            st.subheader("Planted Demo Issues")
            st.dataframe(
                _series_frame(injection_summary, "issue", "records"),
                use_container_width=True,
                hide_index=True,
            )

    with failures_col:
        st.subheader("Failed Records")
        failed_records = pd.DataFrame(report.get("failed_records", []))
        if failed_records.empty:
            st.success("Every record passed validation.")
        else:
            display_columns = [
                column
                for column in [
                    "record_id",
                    "plant_id",
                    "line_id",
                    "shift",
                    "source",
                    "validation_flags",
                    "validation_notes",
                    "injected_issue",
                ]
                if column in failed_records.columns
            ]
            st.dataframe(
                failed_records[display_columns],
                use_container_width=True,
                hide_index=True,
                height=360,
            )

    st.subheader("Batch Quality")
    batch_summary = pd.DataFrame(report.get("batch_summary", []))
    if not batch_summary.empty:
        flat_summary = batch_summary.drop(columns=["counts"], errors="ignore")
        st.dataframe(flat_summary, use_container_width=True, hide_index=True)

    with st.expander("API payload sample"):
        st.json(
            {
                "metadata": metadata,
                "quality": quality,
                "sample_records": report.get("sample_records", [])[:3],
            }
        )


def _render_empty_state(api_base_url: str) -> None:
    st.info(
        "Connect to a Reflex backend and run the synthetic demo, or upload records "
        "to validate them through `/api/validate`."
    )
    st.code(f"{api_base_url}/api/demo?records=750&seed=42")


def _read_uploaded_records(uploaded: Any) -> list[dict[str, Any]]:
    if uploaded.name.lower().endswith(".csv"):
        df = pd.read_csv(uploaded)
        return df.where(pd.notna(df), None).to_dict(orient="records")

    try:
        payload = json.load(uploaded)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid JSON upload: {exc}") from exc

    if isinstance(payload, dict) and "records" in payload:
        payload = payload["records"]
    if not isinstance(payload, list):
        raise ValueError("JSON uploads must be a list of records or an object with a `records` list.")
    return payload


def _get_json(url: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
    response = requests.get(url, params=params, timeout=20)
    response.raise_for_status()
    return response.json()


def _post_json(url: str, payload: dict[str, Any]) -> dict[str, Any]:
    response = requests.post(url, json=payload, timeout=30)
    response.raise_for_status()
    return response.json()


def _series_frame(values: dict[str, Any], label_name: str, value_name: str) -> pd.DataFrame:
    if not values:
        return pd.DataFrame(columns=[label_name, value_name])
    return (
        pd.DataFrame(values.items(), columns=[label_name, value_name])
        .sort_values(value_name, ascending=False)
        .reset_index(drop=True)
    )


def _apply_style() -> None:
    st.markdown(
        """
        <style>
        .block-container {
            padding-top: 2rem;
            padding-bottom: 2rem;
            max-width: 1280px;
        }
        div[data-testid="stMetric"] {
            border: 1px solid #d8dee4;
            border-radius: 8px;
            padding: 0.9rem 1rem;
            background: #ffffff;
        }
        div[data-testid="stMetric"] label {
            color: #57606a;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


if __name__ == "__main__":
    main()
