"""FastAPI webhook — trigger the agent from n8n, Make, or any HTTP client."""

from __future__ import annotations

from typing import Any, Optional

from fastapi import Depends, FastAPI, Header, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware

from agent.models import RunRequest, RunResponse, StatusResponse
from agent.pipeline import run_demo_pipeline, run_pipeline, rows_to_dataframe
from agent.storage import load_last_run, load_schedule_meta
from config import CFG

app = FastAPI(
    title=f"{CFG.company_name} Google Ads Agent API",
    version=CFG.app_version,
    description="Webhook endpoint for scheduled Google Ads analysis via n8n / Make.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


def verify_api_key(x_api_key: Optional[str] = Header(default=None)) -> None:
    if not CFG.api_key:
        return
    if x_api_key != CFG.api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing X-API-Key header.",
        )


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/status", response_model=StatusResponse)
def status_endpoint() -> StatusResponse:
    last = load_last_run()
    last_summary = None
    if last:
        last_summary = {
            "run_id": last.get("run_id"),
            "ran_at": last.get("ran_at"),
            "source": last.get("source"),
            "row_count": last.get("row_count"),
            "totals": last.get("totals"),
        }
    return StatusResponse(
        company=CFG.company_name,
        version=CFG.app_version,
        schedule_interval=CFG.schedule_interval,
        schedule_enabled=CFG.schedule_enabled,
        schedule_label=CFG.schedule_label,
        webhook_url=CFG.webhook_url,
        last_run=last_summary,
        schedule_meta=load_schedule_meta(),
    )


@app.post("/webhook/run", response_model=RunResponse, dependencies=[Depends(verify_api_key)])
def webhook_run(body: RunRequest) -> RunResponse:
    """Main entry point — n8n/Make POST Google Ads keyword rows here."""
    df = rows_to_dataframe([r.model_dump() for r in body.rows])
    result = run_pipeline(
        df,
        source=body.source,
        daily_budget=body.daily_budget,
        send_notifications=body.send_notifications,
    )
    return _to_response(result.to_dict())


@app.post("/webhook/demo", response_model=RunResponse, dependencies=[Depends(verify_api_key)])
def webhook_demo() -> RunResponse:
    """Test endpoint with built-in demo data."""
    result = run_demo_pipeline()
    return _to_response(result.to_dict())


def _to_response(snapshot: dict[str, Any]) -> RunResponse:
    recs = snapshot.get("recommendations", [])[:3]
    return RunResponse(
        run_id=snapshot["run_id"],
        ran_at=snapshot["ran_at"],
        source=snapshot["source"],
        row_count=snapshot["row_count"],
        summary={
            "totals": snapshot["totals"],
            "budget": snapshot["budget"],
        },
        actions={
            "pause": len(snapshot.get("waste", [])),
            "scale_up": len(snapshot.get("winners", [])),
            "total_keywords": len(snapshot.get("verdicts", [])),
        },
        top_recommendations=[
            {"severity": r["severity"], "title": r["title"]} for r in recs
        ],
        notifications_sent=snapshot.get("notifications_sent", []),
    )
