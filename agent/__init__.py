"""Autonomous Google Ads agent package."""

from .data import generate_dummy_data, load_csv, validate_dataframe
from .analyzer import CampaignAnalyzer, AnalysisResult
from .recommender import generate_recommendations, Recommendation
from .notifier import build_agent_log, AgentLogEntry
from .pipeline import run_pipeline, run_demo_pipeline, PipelineResult
from .storage import load_last_run, load_schedule_meta
from .serialize import snapshot_to_ui
from . import charts

__all__ = [
    "generate_dummy_data",
    "load_csv",
    "validate_dataframe",
    "CampaignAnalyzer",
    "AnalysisResult",
    "generate_recommendations",
    "Recommendation",
    "build_agent_log",
    "AgentLogEntry",
    "run_pipeline",
    "run_demo_pipeline",
    "PipelineResult",
    "load_last_run",
    "load_schedule_meta",
    "snapshot_to_ui",
    "charts",
]
