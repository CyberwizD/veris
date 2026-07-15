"""Core Veris validation engine."""

from veris.engine.generator import generate_synthetic_dataset
from veris.engine.service import build_demo_report, validate_records

__all__ = ["build_demo_report", "generate_synthetic_dataset", "validate_records"]
