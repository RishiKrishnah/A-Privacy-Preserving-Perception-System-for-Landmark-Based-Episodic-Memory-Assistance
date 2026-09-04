from __future__ import annotations

from pathlib import Path
from typing import Any
import yaml

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG = ROOT / "config" / "edge_config.yaml"
EXAMPLE_CONFIG = ROOT / "config" / "edge_config.example.yaml"


def load_config(path: str | None = None) -> dict[str, Any]:
    config_path = Path(path) if path else DEFAULT_CONFIG
    if not config_path.exists():
        if EXAMPLE_CONFIG.exists():
            config_path = EXAMPLE_CONFIG
        else:
            raise FileNotFoundError(f"Configuration not found: {config_path}")

    with config_path.open("r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f) or {}

    validate_config(cfg)
    return cfg


def validate_config(cfg: dict[str, Any]) -> None:
    for section in ("camera", "perception", "objects", "tracking", "hands",
                    "events", "database", "api"):
        if not isinstance(cfg.get(section, {}), dict):
            raise ValueError(f"Config section '{section}' must be a mapping")

    if not cfg["objects"].get("personal"):
        raise ValueError("objects.personal must not be empty")
    if not cfg["objects"].get("landmarks"):
        raise ValueError("objects.landmarks must not be empty")

    for key in ("contact_frames", "release_frames", "stable_frames", "min_moving_frames"):
        if int(cfg["events"].get(key, 1)) < 1:
            raise ValueError(f"events.{key} must be >= 1")

    threshold = float(cfg["events"].get("min_event_confidence", 0.55))
    if not 0 < threshold <= 1:
        raise ValueError("events.min_event_confidence must be in (0,1]")


def resolve_project_path(value: str | Path) -> Path:
    p = Path(value)
    return p if p.is_absolute() else ROOT / p
