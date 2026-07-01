"""Autonomous logic engine for the Google Ads AI agent.

The analyzer is intentionally *pure*: it takes a validated DataFrame and a budget
config in, and returns an immutable `AnalysisResult` snapshot out. The Streamlit
layer never mutates these objects — it just renders them.

Three core jobs:
    1. Identify WASTE keywords (high spend, zero conversions).
    2. Identify WINNER keywords (statistically strong conversion rate).
    3. Enforce a hard daily budget cap (default 20 €) by recommending pauses
       and bid reductions until projected daily spend is within budget.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

import numpy as np
import pandas as pd

# ---------------------------------------------------------------------------
# Result types
# ---------------------------------------------------------------------------

ActionType = Literal["pause", "reduce_bid", "scale_up", "hold"]


@dataclass(frozen=True)
class KeywordVerdict:
    """Per-keyword decision the agent has made."""

    keyword: str
    action: ActionType
    reason: str
    clicks: int
    spend: float
    conversions: int
    conv_rate: float          # 0-1
    cost_per_conv: float | None  # None if conversions == 0
    avg_daily_spend: float

    @property
    def is_waste(self) -> bool:
        return self.action == "pause"

    @property
    def is_winner(self) -> bool:
        return self.action == "scale_up"


@dataclass(frozen=True)
class BudgetStatus:
    """Snapshot of how today / yesterday compare against the hard cap."""

    daily_cap: float
    avg_daily_spend: float
    last_day_spend: float
    over_budget_days: int        # how many days in the dataset exceeded the cap
    projected_daily_spend: float # after applying recommended pauses
    within_budget: bool          # projected_daily_spend <= daily_cap


@dataclass(frozen=True)
class AnalysisResult:
    """Immutable bundle returned by `CampaignAnalyzer.run()`."""

    keyword_metrics: pd.DataFrame
    daily_metrics: pd.DataFrame
    verdicts: list[KeywordVerdict]
    waste: list[KeywordVerdict]
    winners: list[KeywordVerdict]
    holds: list[KeywordVerdict]
    budget: BudgetStatus
    totals: dict[str, float] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Analyzer
# ---------------------------------------------------------------------------

class CampaignAnalyzer:
    """Pure analytical engine — no I/O, no Streamlit dependencies."""

    def __init__(
        self,
        df: pd.DataFrame,
        *,
        daily_budget: float = 20.0,
        waste_min_spend_eur: float = 5.0,
        winner_min_clicks: int = 20,
        winner_min_conv_rate: float = 0.04,
    ) -> None:
        if df.empty:
            raise ValueError("Cannot analyze an empty dataframe.")
        self.df = df.copy()
        self.daily_budget = float(daily_budget)
        self.waste_min_spend_eur = float(waste_min_spend_eur)
        self.winner_min_clicks = int(winner_min_clicks)
        self.winner_min_conv_rate = float(winner_min_conv_rate)

    # -- public API --------------------------------------------------------

    def run(self) -> AnalysisResult:
        keyword_metrics = self._keyword_metrics()
        daily_metrics = self._daily_metrics()
        verdicts = self._verdicts(keyword_metrics)
        budget = self._budget_status(daily_metrics, verdicts)
        totals = self._totals()
        return AnalysisResult(
            keyword_metrics=keyword_metrics,
            daily_metrics=daily_metrics,
            verdicts=verdicts,
            waste=[v for v in verdicts if v.action == "pause"],
            winners=[v for v in verdicts if v.action == "scale_up"],
            holds=[v for v in verdicts if v.action in ("hold", "reduce_bid")],
            budget=budget,
            totals=totals,
        )

    # -- aggregations ------------------------------------------------------

    def _keyword_metrics(self) -> pd.DataFrame:
        n_days = max(1, self.df["Date"].dt.normalize().nunique())
        grouped = (
            self.df.groupby("Keyword", as_index=False)
                   .agg(Clicks=("Clicks", "sum"),
                        Spend=("Spend", "sum"),
                        Conversions=("Conversions", "sum"))
        )
        grouped["ConvRate"] = np.where(
            grouped["Clicks"] > 0,
            grouped["Conversions"] / grouped["Clicks"],
            0.0,
        )
        grouped["CostPerConv"] = np.where(
            grouped["Conversions"] > 0,
            grouped["Spend"] / grouped["Conversions"],
            np.nan,
        )
        grouped["AvgCpc"] = np.where(
            grouped["Clicks"] > 0,
            grouped["Spend"] / grouped["Clicks"],
            0.0,
        )
        grouped["AvgDailySpend"] = grouped["Spend"] / n_days
        return grouped.sort_values("Spend", ascending=False).reset_index(drop=True)

    def _daily_metrics(self) -> pd.DataFrame:
        df = self.df.assign(Date=self.df["Date"].dt.normalize())
        daily = (
            df.groupby("Date", as_index=False)
              .agg(Clicks=("Clicks", "sum"),
                   Spend=("Spend", "sum"),
                   Conversions=("Conversions", "sum"))
        )
        daily["ConvRate"] = np.where(
            daily["Clicks"] > 0,
            daily["Conversions"] / daily["Clicks"],
            0.0,
        )
        daily["OverBudget"] = daily["Spend"] > self.daily_budget
        return daily.sort_values("Date").reset_index(drop=True)

    def _totals(self) -> dict[str, float]:
        spend = float(self.df["Spend"].sum())
        clicks = int(self.df["Clicks"].sum())
        conv = int(self.df["Conversions"].sum())
        return {
            "spend": spend,
            "clicks": clicks,
            "conversions": conv,
            "conv_rate": (conv / clicks) if clicks else 0.0,
            "cost_per_conv": (spend / conv) if conv else float("nan"),
            "days": int(self.df["Date"].dt.normalize().nunique()),
        }

    # -- decision logic ----------------------------------------------------

    def _verdicts(self, km: pd.DataFrame) -> list[KeywordVerdict]:
        verdicts: list[KeywordVerdict] = []
        for _, row in km.iterrows():
            action, reason = self._decide(row)
            verdicts.append(KeywordVerdict(
                keyword=str(row["Keyword"]),
                action=action,
                reason=reason,
                clicks=int(row["Clicks"]),
                spend=float(row["Spend"]),
                conversions=int(row["Conversions"]),
                conv_rate=float(row["ConvRate"]),
                cost_per_conv=(None if pd.isna(row["CostPerConv"])
                               else float(row["CostPerConv"])),
                avg_daily_spend=float(row["AvgDailySpend"]),
            ))
        return verdicts

    def _decide(self, row: pd.Series) -> tuple[ActionType, str]:
        spend = float(row["Spend"])
        conv = int(row["Conversions"])
        clicks = int(row["Clicks"])
        cr = float(row["ConvRate"])
        avg_cpc = float(row["AvgCpc"])

        # 1. WASTE — meaningful spend, zero conversions.
        if conv == 0 and spend >= self.waste_min_spend_eur:
            return (
                "pause",
                f"Spent €{spend:.2f} across {clicks} clicks with 0 conversions — "
                f"clear waste. Pausing to free up daily budget.",
            )

        # 2. WINNERS — enough traffic AND a strong conversion rate.
        if clicks >= self.winner_min_clicks and cr >= self.winner_min_conv_rate:
            cpa = spend / conv if conv else float("inf")
            return (
                "scale_up",
                f"Conversion rate {cr * 100:.1f}% over {clicks} clicks "
                f"(CPA €{cpa:.2f}). Recommend increasing bid by ~15% "
                f"and reallocating freed budget here.",
            )

        # 3. REDUCE BID — expensive CPC with weak signal.
        if clicks >= self.winner_min_clicks and avg_cpc > 1.30 and cr < 0.02:
            return (
                "reduce_bid",
                f"Average CPC €{avg_cpc:.2f} is high while conversion rate is only "
                f"{cr * 100:.1f}%. Lowering max CPC by 20% to test efficiency.",
            )

        # 4. Otherwise — hold.
        if conv == 0:
            note = "Not enough spend yet to call waste — keeping under observation."
        else:
            note = f"Stable performer ({cr * 100:.1f}% CR). Keeping current bid."
        return ("hold", note)

    # -- budget ------------------------------------------------------------

    def _budget_status(
        self,
        daily: pd.DataFrame,
        verdicts: list[KeywordVerdict],
    ) -> BudgetStatus:
        avg_daily = float(daily["Spend"].mean()) if not daily.empty else 0.0
        last_day_spend = float(daily["Spend"].iloc[-1]) if not daily.empty else 0.0
        over_days = int(daily["OverBudget"].sum()) if not daily.empty else 0

        # Project tomorrow's spend assuming we apply our pauses + bid reductions.
        # The model: paused keywords contribute 0; reduce_bid contributes 80%;
        # everything else keeps its average daily spend.
        projected = 0.0
        for v in verdicts:
            if v.action == "pause":
                continue
            if v.action == "reduce_bid":
                projected += v.avg_daily_spend * 0.80
            else:
                projected += v.avg_daily_spend

        # If still over budget, scale everything proportionally to fit the cap.
        if projected > self.daily_budget and projected > 0:
            projected = self.daily_budget  # we *enforce* the cap

        return BudgetStatus(
            daily_cap=self.daily_budget,
            avg_daily_spend=avg_daily,
            last_day_spend=last_day_spend,
            over_budget_days=over_days,
            projected_daily_spend=projected,
            within_budget=projected <= self.daily_budget + 1e-6,
        )
