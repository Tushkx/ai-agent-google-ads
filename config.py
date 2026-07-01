"""White-label configuration — override via environment variables."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


def _env(key: str, default: str) -> str:
    return os.environ.get(key, default).strip()


def _env_float(key: str, default: float) -> float:
    try:
        return float(os.environ.get(key, str(default)))
    except ValueError:
        return default


def _env_bool(key: str, default: bool) -> bool:
    val = os.environ.get(key, str(default)).lower()
    return val in ("1", "true", "yes", "on")


# Valid built-in schedule presets (also used by n8n/Make docs).
SCHEDULE_PRESETS: dict[str, str] = {
    "1h": "Every 1 hour",
    "6h": "Every 6 hours",
    "12h": "Every 12 hours",
    "24h": "Every 24 hours (daily)",
    "disabled": "Disabled — trigger only via webhook",
}


@dataclass(frozen=True)
class AppConfig:
    company_name: str
    app_title: str
    tagline: str
    agent_name: str
    page_icon: str
    primary_color: str
    accent_color: str
    slack_channel: str
    notification_recipient: str
    default_daily_budget: float
    currency_symbol: str
    app_version: str
    # API / automation
    api_key: str
    api_host: str
    api_port: int
    data_dir: Path
    schedule_interval: str
    ingest_url: str
    slack_webhook_url: str
    public_api_url: str

    @property
    def full_title(self) -> str:
        return f"{self.company_name} · {self.app_title}"

    @property
    def agent_sender(self) -> str:
        return self.agent_name

    @property
    def schedule_enabled(self) -> bool:
        return self.schedule_interval.lower() not in ("", "disabled", "off", "false", "0")

    @property
    def schedule_label(self) -> str:
        return SCHEDULE_PRESETS.get(self.schedule_interval.lower(), self.schedule_interval)

    @property
    def webhook_path(self) -> str:
        return "/webhook/run"

    @property
    def webhook_url(self) -> str:
        base = self.public_api_url.rstrip("/") if self.public_api_url else f"http://{self.api_host}:{self.api_port}"
        return f"{base}{self.webhook_path}"


def load_config() -> AppConfig:
    company = _env("COMPANY_NAME", "Your Company")
    data_dir = Path(_env("DATA_DIR", "data/state"))
    return AppConfig(
        company_name=company,
        app_title=_env("APP_TITLE", "Google Ads AI Agent"),
        tagline=_env(
            "APP_TAGLINE",
            "Autonomous Google Ads optimization via API — powered by n8n / Make.",
        ),
        agent_name=_env("AGENT_NAME", "Ads Agent"),
        page_icon=_env("PAGE_ICON", "📊"),
        primary_color=_env("PRIMARY_COLOR", "#6366F1"),
        accent_color=_env("ACCENT_COLOR", "#22D3EE"),
        slack_channel=_env("SLACK_CHANNEL", "#marketing-alerts"),
        notification_recipient=_env("NOTIFICATION_RECIPIENT", "Marketing team"),
        default_daily_budget=_env_float("DEFAULT_DAILY_BUDGET", 20.0),
        currency_symbol=_env("CURRENCY_SYMBOL", "€"),
        app_version=_env("APP_VERSION", "2.0.0"),
        api_key=_env("API_KEY", ""),
        api_host=_env("API_HOST", "0.0.0.0"),
        api_port=int(_env("API_PORT", "8000")),
        data_dir=data_dir,
        schedule_interval=_env("SCHEDULE_INTERVAL", "6h").lower(),
        ingest_url=_env("INGEST_URL", ""),
        slack_webhook_url=_env("SLACK_WEBHOOK_URL", ""),
        public_api_url=_env("PUBLIC_API_URL", ""),
    )


CFG = load_config()

COLOR_WIN = "#3DDC97"
COLOR_WASTE = "#FF5C6B"
COLOR_NEUTRAL = "#8892A6"
COLOR_WARN = "#FFB23B"
COLOR_BG = "#0B0D12"
COLOR_CARD = "#141821"
COLOR_TEXT = "#F5F7FB"
COLOR_MUTED = "#8892A6"
