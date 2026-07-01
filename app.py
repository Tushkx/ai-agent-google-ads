"""Google Ads AI Agent — Streamlit dashboard (reads last automated run)."""

from __future__ import annotations

from datetime import datetime

import pandas as pd
import streamlit as st

from agent import charts
from agent.notifier import AgentLogEntry
from agent.pipeline import run_demo_pipeline
from agent.serialize import snapshot_to_ui
from agent.storage import load_last_run, load_schedule_meta
from config import CFG, COLOR_CARD, COLOR_MUTED, COLOR_TEXT, COLOR_WARN, COLOR_WIN, COLOR_WASTE

st.set_page_config(
    page_title=CFG.full_title,
    page_icon=CFG.page_icon,
    layout="wide",
    initial_sidebar_state="expanded",
)

_CUR = CFG.currency_symbol


def _build_css() -> str:
    p, a = CFG.primary_color, CFG.accent_color
    return f"""
<style>
:root {{
    --t-card: {COLOR_CARD};
    --t-border: rgba(255,255,255,0.06);
    --t-text: {COLOR_TEXT};
    --t-muted: {COLOR_MUTED};
    --t-primary: {p};
    --t-accent: {a};
    --t-win: {COLOR_WIN};
    --t-waste: {COLOR_WASTE};
    --t-warn: {COLOR_WARN};
}}
.block-container {{ padding-top: 1.6rem; padding-bottom: 4rem; max-width: 1300px; }}
[data-testid="stSidebar"] {{ background: #0E1118; border-right: 1px solid var(--t-border); }}
.app-hero {{
    background: linear-gradient(135deg, color-mix(in srgb, {p} 18%, transparent),
                                color-mix(in srgb, {a} 10%, transparent) 60%, transparent);
    border: 1px solid var(--t-border); border-radius: 18px;
    padding: 22px 28px; margin-bottom: 22px;
    display: flex; align-items: center; justify-content: space-between;
}}
.app-hero h1 {{
    font-size: 1.7rem; font-weight: 700; margin: 0;
    background: linear-gradient(90deg, {p}, {a});
    -webkit-background-clip: text; -webkit-text-fill-color: transparent;
}}
.app-hero p {{ color: var(--t-muted); margin: 4px 0 0; font-size: 0.95rem; }}
.app-hero .status {{
    background: rgba(61,220,151,0.12); color: var(--t-win);
    padding: 6px 14px; border-radius: 999px; font-weight: 600; font-size: 0.85rem;
    border: 1px solid rgba(61,220,151,0.3);
}}
.kpi-card {{
    background: var(--t-card); border: 1px solid var(--t-border);
    border-radius: 14px; padding: 16px 18px; height: 100%;
}}
.kpi-card .label {{ color: var(--t-muted); font-size: 0.78rem; text-transform: uppercase; }}
.kpi-card .value {{ font-size: 1.8rem; font-weight: 700; margin-top: 4px; }}
.kpi-card .sub {{ color: var(--t-muted); font-size: 0.82rem; }}
.kpi-card.win .value {{ color: var(--t-win); }}
.kpi-card.waste .value {{ color: var(--t-waste); }}
.kpi-card.warn .value {{ color: var(--t-warn); }}
.section-title {{ display: flex; align-items: baseline; gap: 10px; margin: 28px 0 14px; }}
.section-title h2 {{ font-size: 1.15rem; margin: 0; }}
.section-title .pill {{
    font-size: 0.7rem; padding: 3px 9px; border-radius: 999px;
    background: rgba(255,255,255,0.05); color: var(--t-muted); border: 1px solid var(--t-border);
}}
.rec-card {{
    background: var(--t-card); border: 1px solid var(--t-border);
    border-left: 3px solid var(--t-primary); border-radius: 12px;
    padding: 14px 18px; margin-bottom: 12px;
}}
.rec-card.critical {{ border-left-color: var(--t-waste); }}
.rec-card.high {{ border-left-color: var(--t-warn); }}
.rec-card.medium {{ border-left-color: var(--t-accent); }}
.rec-card.info {{ border-left-color: var(--t-win); }}
.rec-card .rec-head {{ display: flex; align-items: center; gap: 10px; font-weight: 600; }}
.rec-card .rec-sev {{ font-size: 0.68rem; text-transform: uppercase; color: var(--t-muted); margin-left: auto; }}
.rec-card .rec-body {{ opacity: 0.85; margin-top: 8px; line-height: 1.55; font-size: 0.93rem; }}
.log-panel {{
    background: var(--t-card); border: 1px solid var(--t-border);
    border-radius: 14px; max-height: 560px; overflow-y: auto;
}}
.log-line {{
    display: flex; gap: 10px; padding: 8px 18px;
    border-bottom: 1px solid rgba(255,255,255,0.03);
    font-family: ui-monospace, Menlo, monospace; font-size: 0.82rem;
}}
.log-line .ts {{ color: var(--t-muted); }}
.log-line.info .lvl {{ color: var(--t-accent); }}
.log-line.action .lvl {{ color: var(--t-primary); }}
.log-line.alert .lvl {{ color: var(--t-waste); }}
.log-line.success .lvl {{ color: var(--t-win); }}
.chat-wrap {{ background: var(--t-card); border: 1px solid var(--t-border); border-radius: 14px; padding: 18px; }}
.chat-header {{ display: flex; gap: 10px; padding-bottom: 12px; margin-bottom: 12px; border-bottom: 1px solid var(--t-border); }}
.chat-header .avatar {{ width: 34px; height: 34px; border-radius: 8px; display: flex; align-items: center; justify-content: center; color: white; font-weight: 700; }}
.chat-header.slack .avatar {{ background: #4A154B; }}
.chat-header.whatsapp .avatar {{ background: #25D366; }}
.bubble {{ border-radius: 12px; padding: 12px 14px; line-height: 1.55; white-space: pre-wrap; }}
.bubble.slack {{ background: rgba(74,21,75,0.25); border: 1px solid rgba(160,90,160,0.3); }}
.bubble.whatsapp {{ background: rgba(37,211,102,0.1); border: 1px solid rgba(37,211,102,0.3); }}
</style>
"""


st.markdown(_build_css(), unsafe_allow_html=True)


def sidebar() -> None:
    meta = load_schedule_meta()
    with st.sidebar:
        st.markdown(
            f"<h2>{CFG.page_icon} {CFG.company_name}</h2>"
            f"<p style='color:#8892A6'>{CFG.tagline}</p>",
            unsafe_allow_html=True,
        )
        st.markdown("---")
        st.markdown("##### ⚡ Automation")
        st.code(CFG.webhook_url, language=None)
        st.caption("n8n / Make → **Schedule Trigger** → Google Ads → **HTTP POST** here")

        st.markdown(f"**Schedule (built-in):** `{CFG.schedule_interval}` — {CFG.schedule_label}")
        if meta.get("next_trigger_at"):
            st.caption(f"Next built-in run: {meta['next_trigger_at']}")
        if meta.get("last_status"):
            st.caption(f"Scheduler status: `{meta['last_status']}`")

        st.markdown("---")
        st.markdown("##### 🧪 Local test")
        if st.button("Run demo analysis now", use_container_width=True):
            run_demo_pipeline()
            st.success("Demo run saved. Refresh to view.")
            st.rerun()

        st.markdown("---")
        st.caption(f"v{CFG.app_version}")


def section(title: str, pill: str | None = None) -> None:
    pill_html = f"<span class='pill'>{pill}</span>" if pill else ""
    st.markdown(f"<div class='section-title'><h2>{title}</h2>{pill_html}</div>", unsafe_allow_html=True)


def render_header(ui: dict) -> None:
    ran = ui["ran_at"][:19].replace("T", " · ")
    st.markdown(
        f"""
        <div class="app-hero">
            <div>
                <h1>{CFG.full_title}</h1>
                <p>Source: <b>{ui['source']}</b> · run <b>{ui['run_id']}</b> · {ran} UTC</p>
            </div>
            <div class="status">● Agent online</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_kpis(ui: dict) -> None:
    t, b = ui["totals"], ui["budget"]
    budget = ui["daily_budget"]
    cards = [
        ("Total spend", f"{_CUR}{t['spend']:.2f}", f"{t['days']} day(s)", ""),
        ("Conversions", f"{int(t['conversions'])}", f"{t['conv_rate']*100:.2f}% CR", "win"),
        ("Cost / conv", f"{_CUR}{t['cost_per_conv']:.2f}" if t["conversions"] else "—", "", ""),
        ("Avg daily spend", f"{_CUR}{b.avg_daily_spend:.2f}", f"cap {_CUR}{budget:.0f}",
         "warn" if b.over_budget_days else "win"),
        ("Waste", f"{len(ui['waste'])}", f"{_CUR}{sum(v.spend for v in ui['waste']):.2f}", "waste" if ui['waste'] else ""),
        ("Winners", f"{len(ui['winners'])}", "ready to scale", "win" if ui['winners'] else ""),
    ]
    for col, (label, val, sub, mod) in zip(st.columns(len(cards)), cards):
        with col:
            st.markdown(
                f'<div class="kpi-card {mod}"><div class="label">{label}</div>'
                f'<div class="value">{val}</div><div class="sub">{sub}</div></div>',
                unsafe_allow_html=True,
            )


def _md_to_html(text: str) -> str:
    out, bold = [], False
    i = 0
    while i < len(text):
        if text[i:i+2] == "**":
            out.append("</strong>" if bold else "<strong>")
            bold = not bold
            i += 2
        else:
            out.append(text[i])
            i += 1
    return "".join(out)


def render_recommendations(recs) -> None:
    for rec in recs:
        body = rec.body.replace("\n", "<br>")
        st.markdown(
            f'<div class="rec-card {rec.severity}"><div class="rec-head">'
            f'<span>{rec.icon}</span><span>{rec.title}</span>'
            f'<span class="rec-sev">{rec.severity}</span></div>'
            f'<div class="rec-body">{_md_to_html(body)}</div></div>',
            unsafe_allow_html=True,
        )


def render_agent_log(log: list[AgentLogEntry]) -> None:
    rows = []
    for e in sorted(log, key=lambda x: x.timestamp, reverse=True):
        if e.channel != "system":
            continue
        rows.append(
            f"<div class='log-line {e.level}'><span class='ts'>{e.time_str}</span>"
            f"<span class='lvl'>{e.level.upper()}</span><span>{e.message}</span></div>"
        )
    st.markdown(f"<div class='log-panel'>{''.join(rows)}</div>", unsafe_allow_html=True)


def render_chat(log: list[AgentLogEntry]) -> None:
    slack = [e for e in log if e.channel == "slack"]
    wa = [e for e in log if e.channel == "whatsapp"]
    c1, c2 = st.columns(2)
    with c1:
        if slack:
            e = max(slack, key=lambda x: x.timestamp)
            st.markdown(
                f'<div class="chat-wrap"><div class="chat-header slack">'
                f'<div class="avatar">S</div><div><b>{e.sender}</b><br><small>{e.time_str}</small></div></div>'
                f'<div class="bubble slack">{e.message.replace(chr(10), "<br>")}</div></div>',
                unsafe_allow_html=True,
            )
    with c2:
        if wa:
            e = max(wa, key=lambda x: x.timestamp)
            st.markdown(
                f'<div class="chat-wrap"><div class="chat-header whatsapp">'
                f'<div class="avatar">W</div><div><b>{e.sender}</b><br><small>{e.time_str}</small></div></div>'
                f'<div class="bubble whatsapp">{e.message.replace(chr(10), "<br>")}</div></div>',
                unsafe_allow_html=True,
            )


def render_tables(ui: dict) -> None:
    def verdict_df(verdicts):
        return pd.DataFrame([{
            "Keyword": v.keyword,
            "Clicks": v.clicks,
            f"Spend ({_CUR})": round(v.spend, 2),
            "Conversions": v.conversions,
            "Conv. rate": f"{v.conv_rate*100:.2f}%",
            "Action": v.action.replace("_", " ").title(),
            "Reason": v.reason,
        } for v in verdicts])

    t1, t2, t3 = st.tabs([
        f"Waste · {len(ui['waste'])}",
        f"Winners · {len(ui['winners'])}",
        f"All · {len(ui['verdicts'])}",
    ])
    with t1:
        st.dataframe(verdict_df(ui["waste"]) if ui["waste"] else pd.DataFrame(), width="stretch", hide_index=True)
    with t2:
        st.dataframe(verdict_df(ui["winners"]) if ui["winners"] else pd.DataFrame(), width="stretch", hide_index=True)
    with t3:
        st.dataframe(verdict_df(ui["verdicts"]), width="stretch", hide_index=True)


def empty_state() -> None:
    st.info(
        "Waiting for the first automated run.\n\n"
        "1. Deploy the API (`uvicorn api:app`)\n"
        "2. In **n8n** or **Make**, schedule a workflow (e.g. every 6 hours)\n"
        "3. Pull Google Ads keyword data → **HTTP POST** to the webhook URL\n\n"
        "Or click **Run demo analysis** in the sidebar to preview the dashboard."
    )
    with st.expander("Example webhook payload"):
        st.code(
            '{\n  "rows": [\n    {"Keyword": "crm software", "Date": "2026-06-01", '
            '"Clicks": 42, "Spend": 35.5, "Conversions": 3}\n  ],\n  "daily_budget": 20\n}',
            language="json",
        )


def main() -> None:
    sidebar()
    snapshot = load_last_run()
    if snapshot is None:
        empty_state()
        return

    ui = snapshot_to_ui(snapshot)
    render_header(ui)
    render_kpis(ui)

    section("14-Day performance", "from last run")
    c1, c2 = st.columns([1.4, 1])
    with c1:
        st.plotly_chart(
            charts.conversion_trend_chart(ui["daily_metrics"], daily_budget=ui["daily_budget"]),
            use_container_width=True,
        )
    with c2:
        st.plotly_chart(charts.spend_vs_conversions_chart(ui["keyword_metrics"]), use_container_width=True)
    st.plotly_chart(charts.keyword_performance_chart(ui["keyword_metrics"]), use_container_width=True)

    section("Strategic Recommendations")
    render_recommendations(ui["recommendations"])

    section("Keyword verdicts")
    render_tables(ui)

    section("Live Agent Log", "last automated run")
    c1, c2 = st.columns([1.1, 1.2])
    with c1:
        render_agent_log(ui["agent_log"])
    with c2:
        render_chat(ui["agent_log"])


if __name__ == "__main__":
    main()
