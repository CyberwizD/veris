"""Command-line demo runner for Veris."""

from __future__ import annotations

import argparse
import json

from veris.engine.service import build_demo_report


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the Veris validation demo.")
    parser.add_argument("--records", type=int, default=750)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    report = build_demo_report(records=args.records, seed=args.seed)
    print(json.dumps(report, indent=2, default=str))


if __name__ == "__main__":
    main()
