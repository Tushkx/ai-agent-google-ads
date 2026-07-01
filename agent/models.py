"""Pydantic models for the webhook API."""

from __future__ import annotations

from __future__ import annotations

from typing import Any, Literal, Optional

from pydantic import BaseModel, Field


class KeywordRow(BaseModel):
    Keyword: str
    Date: str
    Clicks: int = 0
    Spend: float = 0.0
    Conversions: int = 0


class RunRequest(BaseModel):
    """POST /webhook/run body — map Google Ads API output from n8n/Make here."""

    rows: list[KeywordRow] = Field(..., min_length=1)
    daily_budget: Optional[float] = Field(None, ge=1, le=10_000)
    source: str = "google_ads_api"
    send_notifications: bool = True


class RunResponse(BaseModel):
    ok: bool = True
    run_id: str
    ran_at: str
    source: str
    row_count: int
    summary: dict[str, Any]
    actions: dict[str, int]
    top_recommendations: list[dict[str, str]]
    notifications_sent: list[str]


class StatusResponse(BaseModel):
    ok: bool = True
    company: str
    version: str
    schedule_interval: str
    schedule_enabled: bool
    schedule_label: str
    webhook_url: str
    last_run: Optional[dict[str, Any]]
    schedule_meta: dict[str, Any]
