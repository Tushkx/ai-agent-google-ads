"""Plotly chart builders — dark mode, brand colors from config."""

from __future__ import annotations

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from config import CFG, COLOR_NEUTRAL, COLOR_TEXT, COLOR_WASTE, COLOR_WIN

COLOR_PRIMARY = CFG.primary_color
COLOR_ACCENT = CFG.accent_color
COLOR_BG = "rgba(0,0,0,0)"
COLOR_GRID = "rgba(255,255,255,0.06)"
_CURRENCY = CFG.currency_symbol


def _style(fig: go.Figure, *, height: int = 380, legend: bool = True) -> go.Figure:
    fig.update_layout(
        height=height,
        paper_bgcolor=COLOR_BG,
        plot_bgcolor=COLOR_BG,
        font=dict(color=COLOR_TEXT, family="Inter, sans-serif", size=13),
        margin=dict(l=10, r=10, t=40, b=10),
        showlegend=legend,
        legend=dict(
            orientation="h",
            yanchor="bottom", y=1.02,
            xanchor="right", x=1,
            bgcolor=COLOR_BG,
        ),
        hoverlabel=dict(
            bgcolor="#1A1D24",
            bordercolor=COLOR_PRIMARY,
            font_color=COLOR_TEXT,
        ),
    )
    fig.update_xaxes(showgrid=False, zeroline=False, color=COLOR_TEXT)
    fig.update_yaxes(showgrid=True, gridcolor=COLOR_GRID, zeroline=False, color=COLOR_TEXT)
    return fig


def conversion_trend_chart(daily: pd.DataFrame, *, daily_budget: float = 20.0) -> go.Figure:
    fig = make_subplots(specs=[[{"secondary_y": True}]])

    fig.add_trace(
        go.Bar(
            x=daily["Date"],
            y=daily["Conversions"],
            name="Conversions",
            marker_color=COLOR_PRIMARY,
            opacity=0.9,
            hovertemplate="<b>%{x|%a %d %b}</b><br>Conversions: %{y}<extra></extra>",
        ),
        secondary_y=False,
    )

    fig.add_trace(
        go.Scatter(
            x=daily["Date"],
            y=daily["Spend"],
            name=f"Spend ({_CURRENCY})",
            mode="lines+markers",
            line=dict(color=COLOR_ACCENT, width=3, shape="spline"),
            marker=dict(size=7, color=COLOR_ACCENT),
            hovertemplate=f"<b>%{{x|%a %d %b}}</b><br>Spend: {_CURRENCY}%{{y:.2f}}<extra></extra>",
        ),
        secondary_y=True,
    )

    if daily_budget and not daily.empty:
        fig.add_hline(
            y=daily_budget,
            line_dash="dash",
            line_color=COLOR_WASTE,
            line_width=1.5,
            annotation_text=f"{_CURRENCY}{daily_budget:.0f} daily cap",
            annotation_position="top right",
            annotation_font_color=COLOR_WASTE,
            secondary_y=True,
        )

    fig.update_yaxes(title_text="Conversions", secondary_y=False, color=COLOR_TEXT,
                     gridcolor=COLOR_GRID)
    fig.update_yaxes(
        title_text=f"Spend ({_CURRENCY})",
        secondary_y=True,
        color=COLOR_ACCENT,
        showgrid=False,
    )
    return _style(fig, height=400)


def spend_vs_conversions_chart(km: pd.DataFrame) -> go.Figure:
    if km.empty:
        return _style(go.Figure())

    fig = px.scatter(
        km,
        x="Spend",
        y="Conversions",
        size="Clicks",
        color="ConvRate",
        hover_name="Keyword",
        size_max=42,
        color_continuous_scale=[
            [0.0, COLOR_WASTE],
            [0.5, COLOR_NEUTRAL],
            [1.0, COLOR_WIN],
        ],
        labels={"Spend": f"Spend ({_CURRENCY})", "ConvRate": "Conv. rate"},
    )
    fig.update_traces(
        marker=dict(line=dict(width=1, color="rgba(255,255,255,0.15)")),
        hovertemplate=(
            "<b>%{hovertext}</b><br>"
            f"Spend: {_CURRENCY}%{{x:.2f}}<br>"
            "Conversions: %{y}<br>"
            "Clicks: %{marker.size}<extra></extra>"
        ),
    )
    fig.update_coloraxes(
        colorbar=dict(title="CR", tickformat=".0%", outlinewidth=0, len=0.8)
    )
    return _style(fig, height=400)


def keyword_performance_chart(km: pd.DataFrame, *, top_n: int = 10) -> go.Figure:
    if km.empty:
        return _style(go.Figure())

    top = km.head(top_n).copy().iloc[::-1]

    colors = []
    for _, row in top.iterrows():
        if row["Conversions"] == 0 and row["Spend"] >= 5:
            colors.append(COLOR_WASTE)
        elif row["ConvRate"] >= 0.04 and row["Clicks"] >= 20:
            colors.append(COLOR_WIN)
        else:
            colors.append(COLOR_NEUTRAL)

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=top["Spend"],
        y=top["Keyword"],
        orientation="h",
        marker_color=colors,
        text=[
            f"{_CURRENCY}{s:.2f} · {int(c)} conv"
            for s, c in zip(top["Spend"], top["Conversions"])
        ],
        textposition="outside",
        textfont=dict(color=COLOR_TEXT, size=12),
        hovertemplate=(
            "<b>%{y}</b><br>"
            f"Spend: {_CURRENCY}%{{x:.2f}}<br>"
            "Conversions: %{customdata[0]}<br>"
            "Conv. rate: %{customdata[1]:.1%}<extra></extra>"
        ),
        customdata=top[["Conversions", "ConvRate"]].values,
    ))
    fig.update_xaxes(title_text=f"Spend ({_CURRENCY})")
    fig.update_yaxes(title_text="")
    return _style(fig, height=max(320, 36 * len(top)), legend=False)
