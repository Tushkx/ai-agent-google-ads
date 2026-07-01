"""Plain-language recommendation builder."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from config import CFG

from .analyzer import AnalysisResult, KeywordVerdict

Severity = Literal["critical", "high", "medium", "info"]
_CUR = CFG.currency_symbol


@dataclass(frozen=True)
class Recommendation:
    title: str
    body: str
    severity: Severity
    icon: str = "•"

    @property
    def severity_order(self) -> int:
        return {"critical": 0, "high": 1, "medium": 2, "info": 3}[self.severity]


def generate_recommendations(result: AnalysisResult) -> list[Recommendation]:
    recs: list[Recommendation] = []
    recs.extend(_budget_recs(result))
    recs.extend(_waste_recs(result.waste))
    recs.extend(_winner_recs(result.winners))
    recs.extend(_bid_recs(result.holds))
    recs.extend(_strategic_recs(result))
    recs.sort(key=lambda r: r.severity_order)
    return recs


def _budget_recs(result: AnalysisResult) -> list[Recommendation]:
    b = result.budget
    out: list[Recommendation] = []

    if b.over_budget_days > 0:
        out.append(Recommendation(
            title=f"Daily budget exceeded on {b.over_budget_days} day(s)",
            body=(
                f"Over the analyzed period, spend went above the **{_CUR}{b.daily_cap:.0f}** "
                f"hard cap on **{b.over_budget_days}** day(s). I'm tightening "
                f"campaign-level budgets and pausing the wasteful keywords below to "
                f"bring projected daily spend down to **{_CUR}{b.projected_daily_spend:.2f}**."
            ),
            severity="critical",
            icon="🚦",
        ))
    elif b.within_budget:
        out.append(Recommendation(
            title=f"Budget under control ({_CUR}{b.projected_daily_spend:.2f}/day projected)",
            body=(
                f"After applying my recommendations, projected daily spend is "
                f"**{_CUR}{b.projected_daily_spend:.2f}** — comfortably under the "
                f"**{_CUR}{b.daily_cap:.0f}** cap. No emergency action needed."
            ),
            severity="info",
            icon="✅",
        ))
    else:
        out.append(Recommendation(
            title="Budget cap will be enforced",
            body=(
                f"Even after my optimizations, projected daily spend is "
                f"**{_CUR}{b.projected_daily_spend:.2f}**. I'm enforcing the "
                f"**{_CUR}{b.daily_cap:.0f}** hard cap at the campaign level so Google "
                f"Ads stops serving once the limit is hit."
            ),
            severity="high",
            icon="🛑",
        ))
    return out


def _waste_recs(waste: list[KeywordVerdict]) -> list[Recommendation]:
    if not waste:
        return []

    total_waste = sum(v.spend for v in waste)
    top = sorted(waste, key=lambda v: v.spend, reverse=True)[:3]
    lines = [
        f"- **{v.keyword}** — {_CUR}{v.spend:.2f} spent, {v.clicks} clicks, 0 conversions"
        for v in top
    ]
    body = (
        f"I found **{len(waste)} keyword(s)** that burned **{_CUR}{total_waste:.2f}** with "
        f"zero conversions. I'm pausing them tonight and reallocating that budget to "
        f"the winners below.\n\n" + "\n".join(lines)
    )
    return [Recommendation(
        title=f"Pause {len(waste)} wasteful keyword(s) — saves {_CUR}{total_waste:.2f}",
        body=body,
        severity="critical",
        icon="🗑️",
    )]


def _winner_recs(winners: list[KeywordVerdict]) -> list[Recommendation]:
    if not winners:
        return []

    top = sorted(winners, key=lambda v: v.conv_rate, reverse=True)[:3]
    lines = []
    for v in top:
        cpa = f"{_CUR}{v.cost_per_conv:.2f}" if v.cost_per_conv else "n/a"
        lines.append(
            f"- **{v.keyword}** — {v.conv_rate * 100:.1f}% CR, "
            f"{v.conversions} conv, CPA {cpa}"
        )
    body = (
        f"**{len(winners)} keyword(s)** are converting well above average. "
        f"I'm raising their max-CPC by ~15% and routing the freed waste budget "
        f"to them.\n\n" + "\n".join(lines)
    )
    return [Recommendation(
        title=f"Scale up {len(winners)} winning keyword(s)",
        body=body,
        severity="high",
        icon="🚀",
    )]


def _bid_recs(holds: list[KeywordVerdict]) -> list[Recommendation]:
    reducers = [v for v in holds if v.action == "reduce_bid"]
    if not reducers:
        return []

    lines = [
        f"- **{v.keyword}** — avg CPC {_CUR}{(v.spend / v.clicks) if v.clicks else 0:.2f}, "
        f"CR {v.conv_rate * 100:.1f}%"
        for v in reducers[:3]
    ]
    body = (
        "These keywords have expensive clicks but weak conversion signal. I'm "
        "lowering their max CPC by 20% to test whether efficiency improves "
        "before pausing.\n\n" + "\n".join(lines)
    )
    return [Recommendation(
        title=f"Reduce bid on {len(reducers)} expensive keyword(s)",
        body=body,
        severity="medium",
        icon="🪙",
    )]


def _strategic_recs(result: AnalysisResult) -> list[Recommendation]:
    out: list[Recommendation] = []
    t = result.totals

    if t["clicks"] and t["conversions"] == 0:
        out.append(Recommendation(
            title="Zero conversions across the entire account",
            body=(
                "I observed clicks but **no conversions at all** in this dataset. "
                "Before scaling spend, double-check that conversion tracking "
                "(e.g. sign-up or purchase events) is firing correctly."
            ),
            severity="high",
            icon="⚠️",
        ))

    if t["clicks"] and t["conversions"]:
        cr_pct = t["conv_rate"] * 100
        cpa = t["cost_per_conv"]
        out.append(Recommendation(
            title="Overall account snapshot",
            body=(
                f"Over the last **{t['days']}** day(s): **{t['clicks']:,}** clicks → "
                f"**{t['conversions']:,}** conversions "
                f"(**{cr_pct:.2f}% CR**, CPA **{_CUR}{cpa:.2f}**). "
                f"Compared to typical B2B SaaS benchmarks (≈3–5% CR), "
                f"this {'looks healthy' if cr_pct >= 3 else 'has room to grow'}."
            ),
            severity="info",
            icon="📊",
        ))

    if result.winners:
        top_kw = result.winners[0].keyword
        out.append(Recommendation(
            title="Build dedicated landing pages for top winners",
            body=(
                f"Your winning keywords share a clear intent (e.g. **{top_kw}**). "
                f"I recommend creating keyword-specific landing pages that mirror "
                f"search intent — expect a +15–25% CR lift based on standard A/B benchmarks."
            ),
            severity="medium",
            icon="🧭",
        ))

    return out
