"""Persist and load agent run snapshots."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from config import CFG


def _state_dir() -> Path:
    d = CFG.data_dir
    d.mkdir(parents=True, exist_ok=True)
    return d


def _last_run_path() -> Path:
    return _state_dir() / "last_run.json"


def _history_path() -> Path:
    return _state_dir() / "run_history.jsonl"


def save_run(snapshot: dict[str, Any]) -> None:
    """Persist the latest run and append to history."""
    path = _last_run_path()
    path.write_text(json.dumps(snapshot, indent=2, default=str), encoding="utf-8")

    history = _history_path()
    with history.open("a", encoding="utf-8") as f:
        f.write(json.dumps({
            "run_id": snapshot.get("run_id"),
            "ran_at": snapshot.get("ran_at"),
            "source": snapshot.get("source"),
            "row_count": snapshot.get("row_count"),
        }, default=str) + "\n")


def load_last_run() -> dict[str, Any] | None:
    path = _last_run_path()
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def load_schedule_meta() -> dict[str, Any]:
    """Metadata about the built-in scheduler (updated by scheduler process)."""
    path = _state_dir() / "schedule_meta.json"
    if not path.exists():
        return {
            "interval": CFG.schedule_interval,
            "enabled": CFG.schedule_enabled,
            "last_trigger_at": None,
            "next_trigger_at": None,
            "last_status": "waiting",
        }
    return json.loads(path.read_text(encoding="utf-8"))


def save_schedule_meta(meta: dict[str, Any]) -> None:
    path = _state_dir() / "schedule_meta.json"
    path.write_text(json.dumps(meta, indent=2, default=str), encoding="utf-8")


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()
