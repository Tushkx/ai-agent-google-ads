"""End-to-end agent pipeline — analyze, notify, persist."""

from __future__ import annotations

import uuid
from typing import Any

import pandas as pd

from config import CFG

from .analyzer import CampaignAnalyzer, AnalysisResult
from .data import generate_dummy_data, validate_dataframe
from .notifier import build_agent_log
from .recommender import generate_recommendations
from .serialize import result_to_snapshot
from .storage import save_run, utc_now_iso


class PipelineResult:
    """In-memory result returned to API callers."""

    def __init__(self, snapshot: dict[str, Any]) -> None:
        self.snapshot = snapshot

    @property
    def run_id(self) -> str:
        return self.snapshot["run_id"]

    def to_dict(self) -> dict[str, Any]:
        return self.snapshot


def rows_to_dataframe(rows: list[dict[str, Any]]) -> pd.DataFrame:
    if not rows:
        raise ValueError("Payload must include at least one row in `rows`.")
    return validate_dataframe(pd.DataFrame(rows))


def run_pipeline(
    df: pd.DataFrame,
    *,
    source: str = "api",
    daily_budget: float | None = None,
    persist: bool = True,
    send_notifications: bool = True,
) -> PipelineResult:
    """Run the full autonomous analysis pipeline."""
    budget = daily_budget if daily_budget is not None else CFG.default_daily_budget
    analyzer = CampaignAnalyzer(df, daily_budget=budget)
    result: AnalysisResult = analyzer.run()
    recommendations = generate_recommendations(result)
    agent_log = build_agent_log(result)

    notifications_sent: list[str] = []
    if send_notifications:
        notifications_sent = _dispatch_notifications(agent_log)

    run_id = str(uuid.uuid4())[:8]
    snapshot = result_to_snapshot(
        result,
        run_id=run_id,
        ran_at=utc_now_iso(),
        source=source,
        daily_budget=budget,
        recommendations=recommendations,
        agent_log=agent_log,
        row_count=len(df),
        notifications_sent=notifications_sent,
    )

    if persist:
        save_run(snapshot)

    return PipelineResult(snapshot)


def run_demo_pipeline(**kwargs: Any) -> PipelineResult:
    df = generate_dummy_data()
    return run_pipeline(df, source="demo", **kwargs)


def _dispatch_notifications(agent_log: list) -> list[str]:
    """Send real Slack webhook if configured; always records simulated channels."""
    sent: list[str] = []
    slack_msgs = [e for e in agent_log if e.channel == "slack"]
    if CFG.slack_webhook_url and slack_msgs:
        import json
        import urllib.request

        latest = max(slack_msgs, key=lambda e: e.timestamp)
        payload = json.dumps({"text": latest.message}).encode()
        req = urllib.request.Request(
            CFG.slack_webhook_url,
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            urllib.request.urlopen(req, timeout=10)
            sent.append("slack_webhook")
        except Exception:
            sent.append("slack_webhook_failed")

    if slack_msgs:
        sent.append("slack_ui")
    if any(e.channel == "whatsapp" for e in agent_log):
        sent.append("whatsapp_ui")
    return sent
