"""Built-in scheduler — optional alternative to n8n/Make cron triggers.

Set SCHEDULE_INTERVAL to one of: 1h, 6h, 12h, 24h
Set INGEST_URL to a webhook that returns { "rows": [...] } (e.g. n8n workflow).

Run:
    python scheduler.py
"""

from __future__ import annotations

import json
import logging
import sys
import urllib.request
from datetime import datetime, timedelta, timezone

from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.interval import IntervalTrigger

from agent.pipeline import run_demo_pipeline, run_pipeline, rows_to_dataframe
from agent.storage import load_schedule_meta, save_schedule_meta, utc_now_iso
from config import CFG, SCHEDULE_PRESETS

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("scheduler")

INTERVAL_HOURS = {"1h": 1, "6h": 6, "12h": 12, "24h": 24}


def _parse_interval() -> int | None:
    key = CFG.schedule_interval.lower()
    if key in ("", "disabled", "off", "false", "0"):
        return None
    if key not in INTERVAL_HOURS:
        log.error("Unknown SCHEDULE_INTERVAL=%r. Use: %s", key, ", ".join(INTERVAL_HOURS))
        sys.exit(1)
    return INTERVAL_HOURS[key]


def _fetch_rows_from_ingest() -> list[dict]:
    """GET keyword rows from INGEST_URL (n8n webhook returning Google Ads data)."""
    req = urllib.request.Request(CFG.ingest_url, method="GET")
    if CFG.api_key:
        req.add_header("X-API-Key", CFG.api_key)
    with urllib.request.urlopen(req, timeout=120) as resp:
        payload = json.loads(resp.read().decode())

    rows = payload.get("rows", payload)
    if not isinstance(rows, list) or not rows:
        raise ValueError("INGEST_URL must return JSON with a non-empty `rows` array.")
    return rows


def scheduled_job() -> None:
    log.info("Scheduled run starting (interval=%s)", CFG.schedule_interval)
    meta = load_schedule_meta()
    meta["last_trigger_at"] = utc_now_iso()
    meta["last_status"] = "running"
    save_schedule_meta(meta)

    try:
        if CFG.ingest_url:
            rows = _fetch_rows_from_ingest()
            df = rows_to_dataframe(rows)
            run_pipeline(df, source="scheduled_ingest", send_notifications=True)
        else:
            log.warning("INGEST_URL not set — using demo data.")
            run_demo_pipeline(send_notifications=True)

        meta["last_status"] = "success"
        log.info("Scheduled run completed.")
    except Exception as exc:
        meta["last_status"] = f"error: {exc}"
        log.exception("Scheduled run failed: %s", exc)
    finally:
        hours = INTERVAL_HOURS.get(CFG.schedule_interval.lower(), 6)
        next_at = datetime.now(timezone.utc) + timedelta(hours=hours)
        meta["next_trigger_at"] = next_at.isoformat()
        meta["interval"] = CFG.schedule_interval
        meta["enabled"] = True
        save_schedule_meta(meta)


def main() -> None:
    hours = _parse_interval()
    if hours is None:
        log.info("Scheduler disabled (SCHEDULE_INTERVAL=%s). Use n8n/Make cron → POST %s",
                 CFG.schedule_interval, CFG.webhook_path)
        sys.exit(0)

    log.info("Starting scheduler: every %dh — %s", hours, SCHEDULE_PRESETS.get(CFG.schedule_interval, ""))
    if CFG.ingest_url:
        log.info("Data source: INGEST_URL=%s", CFG.ingest_url)
    else:
        log.info("Data source: demo data (set INGEST_URL for live Google Ads via n8n)")

    save_schedule_meta({
        "interval": CFG.schedule_interval,
        "enabled": True,
        "last_trigger_at": None,
        "next_trigger_at": (datetime.now(timezone.utc) + timedelta(hours=hours)).isoformat(),
        "last_status": "started",
    })

    scheduler = BlockingScheduler()
    scheduler.add_job(
        scheduled_job,
        IntervalTrigger(hours=hours),
        id="ads_agent_run",
        next_run_time=datetime.now(timezone.utc),
    )
    scheduled_job()  # run immediately on start
    scheduler.start()


if __name__ == "__main__":
    main()
