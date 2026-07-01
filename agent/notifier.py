"""Simulated Live Agent Log with Slack / WhatsApp notification UI."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, time, timedelta
from typing import Literal

import pandas as pd

from config import CFG

from .analyzer import AnalysisResult

Channel = Literal["system", "slack", "whatsapp"]
LogLevel = Literal["info", "action", "alert", "success"]

_CUR = CFG.currency_symbol


@dataclass(frozen=True)
class AgentLogEntry:
    timestamp: datetime
    channel: Channel
    level: LogLevel
    message: str
    sender: str = CFG.agent_name

    @property
    def time_str(self) -> str:
        return self.timestamp.strftime("%a %d %b · %H:%M")


def build_agent_log(
    result: AnalysisResult,
    *,
    wake_time: time = time(12, 0),
    days_back: int = 5,
    now: datetime | None = None,
) -> list[AgentLogEntry]:
    """Construct a simulated multi-day log ending today at the configured wake time."""
    entries: list[AgentLogEntry] = []
    history_days = min(days_back, max(1, len(result.daily_metrics)))
    daily = result.daily_metrics.tail(history_days).reset_index(drop=True)

    for i, row in daily.iterrows():
        is_today = i == len(daily) - 1
        day = row["Date"].date() if isinstance(row["Date"], pd.Timestamp) else row["Date"]
        ts = datetime.combine(day, wake_time)
        entries.extend(_entries_for_day(ts, row, result, is_today=is_today))

    return entries


def _entries_for_day(
    ts: datetime,
    row: pd.Series,
    result: AnalysisResult,
    *,
    is_today: bool,
) -> list[AgentLogEntry]:
    spend = float(row["Spend"])
    conv = int(row["Conversions"])
    over = bool(row["OverBudget"])
    out: list[AgentLogEntry] = []

    out.append(AgentLogEntry(
        timestamp=ts,
        channel="system",
        level="info",
        message=(
            f"Daily wake-up · ingesting Google Ads report "
            f"({_CUR}{spend:.2f} spent, {conv} conversions)."
        ),
    ))

    out.append(AgentLogEntry(
        timestamp=ts + timedelta(seconds=12),
        channel="system",
        level="info",
        message="Running autonomous analysis: waste detection · winners detection · budget guard…",
    ))

    if over:
        out.append(AgentLogEntry(
            timestamp=ts + timedelta(seconds=30),
            channel="system",
            level="alert",
            message=(
                f"⚠️  Daily budget breach: {_CUR}{spend:.2f} vs cap "
                f"{_CUR}{result.budget.daily_cap:.0f}. Throttling at campaign level."
            ),
        ))

    if is_today:
        out.extend(_today_actions(ts, result))
        out.extend(_today_notifications(ts, result))
    else:
        out.append(AgentLogEntry(
            timestamp=ts + timedelta(seconds=45),
            channel="system",
            level="success",
            message="Daily run complete · 1 notification dispatched.",
        ))

    return out


def _today_actions(ts: datetime, result: AnalysisResult) -> list[AgentLogEntry]:
    out: list[AgentLogEntry] = []

    if result.waste:
        names = ", ".join(f"'{v.keyword}'" for v in result.waste[:3])
        more = f" (+{len(result.waste) - 3} more)" if len(result.waste) > 3 else ""
        out.append(AgentLogEntry(
            timestamp=ts + timedelta(seconds=45),
            channel="system",
            level="action",
            message=f"Pausing {len(result.waste)} wasteful keyword(s): {names}{more}.",
        ))

    if result.winners:
        names = ", ".join(f"'{v.keyword}'" for v in result.winners[:3])
        out.append(AgentLogEntry(
            timestamp=ts + timedelta(seconds=58),
            channel="system",
            level="action",
            message=f"Raising bids +15% on {len(result.winners)} winner(s): {names}.",
        ))

    cap = result.budget.daily_cap
    if result.budget.within_budget:
        out.append(AgentLogEntry(
            timestamp=ts + timedelta(seconds=70),
            channel="system",
            level="success",
            message=(
                f"Projected tomorrow's spend: {_CUR}{result.budget.projected_daily_spend:.2f} "
                f"— within {_CUR}{cap:.0f} cap."
            ),
        ))
    else:
        out.append(AgentLogEntry(
            timestamp=ts + timedelta(seconds=70),
            channel="system",
            level="alert",
            message=(
                f"Cap enforcement engaged — campaign pauses at {_CUR}{cap:.0f} daily spend."
            ),
        ))

    return out


def _today_notifications(ts: datetime, result: AnalysisResult) -> list[AgentLogEntry]:
    return [
        AgentLogEntry(
            timestamp=ts + timedelta(seconds=82),
            channel="slack",
            level="success",
            sender=f"{CFG.agent_name} → {CFG.slack_channel}",
            message=_slack_summary(result),
        ),
        AgentLogEntry(
            timestamp=ts + timedelta(seconds=95),
            channel="whatsapp",
            level="success",
            sender=f"{CFG.agent_name} → {CFG.notification_recipient} (WhatsApp)",
            message=_whatsapp_summary(result),
        ),
    ]


def _slack_summary(result: AnalysisResult) -> str:
    waste_part = (
        f"• Paused *{len(result.waste)}* wasteful keyword(s), "
        f"saving ~{_CUR}{sum(v.avg_daily_spend for v in result.waste):.2f}/day."
        if result.waste else "• No waste detected today."
    )
    winner_part = (
        f"• Scaled *{len(result.winners)}* winning keyword(s) "
        f"(avg CR {_avg_cr(result.winners) * 100:.1f}%)."
        if result.winners else "• No new winners promoted today."
    )
    budget_part = (
        f"• Tomorrow's projected spend: *{_CUR}{result.budget.projected_daily_spend:.2f}* "
        f"vs cap {_CUR}{result.budget.daily_cap:.0f}."
    )
    return (
        f":robot_face: *Daily Google Ads digest — {CFG.company_name}*\n"
        + waste_part + "\n"
        + winner_part + "\n"
        + budget_part + "\n"
        + "_Open the dashboard for full reasoning →_"
    )


def _whatsapp_summary(result: AnalysisResult) -> str:
    saved = sum(v.avg_daily_spend for v in result.waste)
    return (
        f"Hi! {CFG.agent_name} here.\n"
        f"Today I paused {len(result.waste)} wasteful keyword(s) "
        f"(saving ~{_CUR}{saved:.2f}/day) and scaled {len(result.winners)} winner(s). "
        f"Tomorrow we'll spend ~{_CUR}{result.budget.projected_daily_spend:.2f} — "
        f"under your {_CUR}{result.budget.daily_cap:.0f} cap. ✅"
    )


def _avg_cr(verdicts: list) -> float:
    if not verdicts:
        return 0.0
    return sum(v.conv_rate for v in verdicts) / len(verdicts)
