#!/usr/bin/env python3
"""CLI — run the agent locally (cron, manual, or CI)."""

from __future__ import annotations

import argparse
import json
import sys

from agent.data import load_csv
from agent.pipeline import run_demo_pipeline, run_pipeline


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the Google Ads AI agent")
    parser.add_argument("--demo", action="store_true", help="Use built-in demo data")
    parser.add_argument("--file", type=str, help="Path to CSV (optional local test)")
    parser.add_argument("--json", type=str, help="Path to JSON payload (webhook format)")
    parser.add_argument("--budget", type=float, default=None, help="Daily budget cap")
    parser.add_argument("--no-notify", action="store_true", help="Skip Slack webhook")
    args = parser.parse_args()

    if args.demo:
        result = run_demo_pipeline(
            daily_budget=args.budget,
            send_notifications=not args.no_notify,
        )
    elif args.json:
        payload = json.loads(open(args.json, encoding="utf-8").read())
        from agent.pipeline import rows_to_dataframe
        df = rows_to_dataframe(payload["rows"])
        result = run_pipeline(
            df,
            source=payload.get("source", "cli"),
            daily_budget=args.budget or payload.get("daily_budget"),
            send_notifications=not args.no_notify,
        )
    elif args.file:
        df = load_csv(args.file)
        result = run_pipeline(
            df,
            source="cli_csv",
            daily_budget=args.budget,
            send_notifications=not args.no_notify,
        )
    else:
        parser.print_help()
        return 1

    snap = result.to_dict()
    print(json.dumps({
        "run_id": snap["run_id"],
        "actions": {
            "pause": len(snap["waste"]),
            "scale_up": len(snap["winners"]),
        },
        "totals": snap["totals"],
    }, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
