"""Serialize analysis results to JSON-friendly dicts."""

from __future__ import annotations

from datetime import datetime
from typing import Any

import pandas as pd

from .analyzer import AnalysisResult, BudgetStatus, KeywordVerdict
from .notifier import AgentLogEntry
from .recommender import Recommendation


def verdict_to_dict(v: KeywordVerdict) -> dict[str, Any]:
    return {
        "keyword": v.keyword,
        "action": v.action,
        "reason": v.reason,
        "clicks": v.clicks,
        "spend": v.spend,
        "conversions": v.conversions,
        "conv_rate": v.conv_rate,
        "cost_per_conv": v.cost_per_conv,
        "avg_daily_spend": v.avg_daily_spend,
    }


def verdict_from_dict(d: dict[str, Any]) -> KeywordVerdict:
    return KeywordVerdict(
        keyword=d["keyword"],
        action=d["action"],
        reason=d["reason"],
        clicks=int(d["clicks"]),
        spend=float(d["spend"]),
        conversions=int(d["conversions"]),
        conv_rate=float(d["conv_rate"]),
        cost_per_conv=d.get("cost_per_conv"),
        avg_daily_spend=float(d["avg_daily_spend"]),
    )


def budget_to_dict(b: BudgetStatus) -> dict[str, Any]:
    return {
        "daily_cap": b.daily_cap,
        "avg_daily_spend": b.avg_daily_spend,
        "last_day_spend": b.last_day_spend,
        "over_budget_days": b.over_budget_days,
        "projected_daily_spend": b.projected_daily_spend,
        "within_budget": b.within_budget,
    }


def budget_from_dict(d: dict[str, Any]) -> BudgetStatus:
    return BudgetStatus(**d)


def recommendation_to_dict(r: Recommendation) -> dict[str, Any]:
    return {
        "title": r.title,
        "body": r.body,
        "severity": r.severity,
        "icon": r.icon,
    }


def recommendation_from_dict(d: dict[str, Any]) -> Recommendation:
    return Recommendation(**d)


def log_entry_to_dict(e: AgentLogEntry) -> dict[str, Any]:
    return {
        "timestamp": e.timestamp.isoformat(),
        "channel": e.channel,
        "level": e.level,
        "message": e.message,
        "sender": e.sender,
    }


def log_entry_from_dict(d: dict[str, Any]) -> AgentLogEntry:
    ts = d["timestamp"]
    if isinstance(ts, str):
        ts = datetime.fromisoformat(ts)
    return AgentLogEntry(
        timestamp=ts,
        channel=d["channel"],
        level=d["level"],
        message=d["message"],
        sender=d.get("sender", "Ads Agent"),
    )


def df_to_records(df: pd.DataFrame) -> list[dict[str, Any]]:
    out = df.copy()
    if "Date" in out.columns:
        out["Date"] = pd.to_datetime(out["Date"]).dt.strftime("%Y-%m-%d")
    return out.to_dict(orient="records")


def records_to_daily_df(records: list[dict[str, Any]]) -> pd.DataFrame:
    df = pd.DataFrame(records)
    if not df.empty and "Date" in df.columns:
        df["Date"] = pd.to_datetime(df["Date"])
    return df


def records_to_keyword_df(records: list[dict[str, Any]]) -> pd.DataFrame:
    return pd.DataFrame(records)


def result_to_snapshot(
    result: AnalysisResult,
    *,
    run_id: str,
    ran_at: str,
    source: str,
    daily_budget: float,
    recommendations: list[Recommendation],
    agent_log: list[AgentLogEntry],
    row_count: int,
    notifications_sent: list[str] | None = None,
) -> dict[str, Any]:
    return {
        "run_id": run_id,
        "ran_at": ran_at,
        "source": source,
        "daily_budget": daily_budget,
        "row_count": row_count,
        "totals": result.totals,
        "budget": budget_to_dict(result.budget),
        "waste": [verdict_to_dict(v) for v in result.waste],
        "winners": [verdict_to_dict(v) for v in result.winners],
        "verdicts": [verdict_to_dict(v) for v in result.verdicts],
        "recommendations": [recommendation_to_dict(r) for r in recommendations],
        "agent_log": [log_entry_to_dict(e) for e in agent_log],
        "daily_metrics": df_to_records(result.daily_metrics),
        "keyword_metrics": df_to_records(result.keyword_metrics),
        "notifications_sent": notifications_sent or [],
    }


def snapshot_to_ui(snapshot: dict[str, Any]) -> dict[str, Any]:
    """Rehydrate a stored snapshot into objects the dashboard can render."""
    return {
        "run_id": snapshot["run_id"],
        "ran_at": snapshot["ran_at"],
        "source": snapshot["source"],
        "daily_budget": snapshot["daily_budget"],
        "totals": snapshot["totals"],
        "budget": budget_from_dict(snapshot["budget"]),
        "waste": [verdict_from_dict(v) for v in snapshot["waste"]],
        "winners": [verdict_from_dict(v) for v in snapshot["winners"]],
        "verdicts": [verdict_from_dict(v) for v in snapshot["verdicts"]],
        "recommendations": [recommendation_from_dict(r) for r in snapshot["recommendations"]],
        "agent_log": [log_entry_from_dict(e) for e in snapshot["agent_log"]],
        "daily_metrics": records_to_daily_df(snapshot["daily_metrics"]),
        "keyword_metrics": records_to_keyword_df(snapshot["keyword_metrics"]),
        "notifications_sent": snapshot.get("notifications_sent", []),
    }
