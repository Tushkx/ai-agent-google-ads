"""Data loading utilities for the Google Ads AI Agent.

Handles:
    1. User-uploaded Google Ads CSV exports.
    2. A deterministic demo dataset for onboarding without real data.

Schema: Keyword | Date | Clicks | Spend | Conversions
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from io import BytesIO, StringIO
from typing import IO, Iterable

import numpy as np
import pandas as pd

REQUIRED_COLUMNS: tuple[str, ...] = ("Keyword", "Date", "Clicks", "Spend", "Conversions")

# Generic SaaS / marketing keyword set — works for any B2B or product company demo.
_KEYWORD_UNIVERSE: tuple[tuple[str, str, float, float, float], ...] = (
    # Winners — high-intent, strong conversion rates.
    ("crm software free trial",        "winner",  0.058, 0.078, 0.95),
    ("project management tool",        "winner",  0.055, 0.068, 1.05),
    ("marketing automation platform",  "winner",  0.048, 0.072, 1.12),
    ("team collaboration software",    "winner",  0.052, 0.061, 0.88),
    # Mid performers.
    ("business productivity app",      "average", 0.038, 0.024, 1.15),
    ("workflow automation tool",       "average", 0.035, 0.020, 1.08),
    ("customer support software",      "average", 0.032, 0.016, 1.25),
    # Waste — broad match, high CPC, near-zero conversions.
    ("crm software",                   "waste",   0.042, 0.002, 1.75),
    ("project management",             "waste",   0.038, 0.001, 1.60),
    ("marketing software",             "waste",   0.050, 0.003, 1.90),
)


@dataclass(frozen=True)
class DataSource:
    label: str
    is_dummy: bool
    rows: int


def generate_dummy_data(
    days: int = 14,
    end_date: date | None = None,
    seed: int = 42,
) -> pd.DataFrame:
    """Generate a deterministic 14-day keyword-level demo dataset."""
    if days <= 0:
        raise ValueError("days must be positive")

    rng = np.random.default_rng(seed)
    end = end_date or date.today()
    dates = [end - timedelta(days=i) for i in range(days - 1, -1, -1)]

    rows: list[dict] = []
    for kw, persona, base_ctr, base_cr, base_cpc in _KEYWORD_UNIVERSE:
        base_impressions = {
            "winner":  rng.integers(180, 260),
            "average": rng.integers(120, 200),
            "waste":   rng.integers(140, 220),
        }[persona]

        for d in dates:
            dow_mult = 0.88 if d.weekday() >= 5 else 1.0
            noise = rng.normal(loc=1.0, scale=0.18)
            impressions = max(1, int(base_impressions * dow_mult * max(0.4, noise)))

            ctr = max(0.0, rng.normal(loc=base_ctr, scale=base_ctr * 0.25))
            clicks = int(round(impressions * ctr))
            cpc = max(0.20, rng.normal(loc=base_cpc, scale=base_cpc * 0.15))
            spend = round(clicks * cpc, 2)

            cr = max(0.0, rng.normal(loc=base_cr, scale=base_cr * 0.5 + 0.002))
            expected_conv = max(0.0, clicks * cr)
            conversions = int(rng.poisson(expected_conv)) if expected_conv > 0 else 0
            if persona == "waste" and rng.random() < 0.92:
                conversions = 0

            rows.append({
                "Keyword": kw,
                "Date": pd.Timestamp(d),
                "Clicks": int(clicks),
                "Spend": float(spend),
                "Conversions": int(conversions),
            })

    return pd.DataFrame(rows, columns=list(REQUIRED_COLUMNS)).sort_values(
        ["Date", "Keyword"]
    ).reset_index(drop=True)


def validate_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing:
        raise ValueError(
            "CSV is missing required column(s): "
            + ", ".join(missing)
            + f". Expected: {', '.join(REQUIRED_COLUMNS)}."
        )

    out = df[list(REQUIRED_COLUMNS)].copy()
    out["Keyword"] = out["Keyword"].astype(str).str.strip()
    out["Date"] = pd.to_datetime(out["Date"], errors="coerce")
    out["Clicks"] = pd.to_numeric(out["Clicks"], errors="coerce").fillna(0).astype(int)
    out["Spend"] = pd.to_numeric(out["Spend"], errors="coerce").fillna(0.0).astype(float)
    out["Conversions"] = pd.to_numeric(out["Conversions"], errors="coerce").fillna(0).astype(int)

    out = out.dropna(subset=["Date"])
    if out.empty:
        raise ValueError("CSV contained no usable rows after parsing.")

    return out.sort_values(["Date", "Keyword"]).reset_index(drop=True)


def load_csv(source: IO[bytes] | IO[str] | str | bytes) -> pd.DataFrame:
    if isinstance(source, (bytes, bytearray)):
        buf: IO = BytesIO(source)
    elif isinstance(source, str) and "\n" in source:
        buf = StringIO(source)
    else:
        buf = source

    return validate_dataframe(pd.read_csv(buf))


def describe_source(df: pd.DataFrame, *, label: str, is_dummy: bool) -> DataSource:
    return DataSource(label=label, is_dummy=is_dummy, rows=len(df))


def known_keywords() -> Iterable[str]:
    return [kw for kw, *_ in _KEYWORD_UNIVERSE]
