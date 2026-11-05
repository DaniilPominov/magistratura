"""Загрузка YAML-конфигурации и её стабильный хеш.

Хеш конфигурации используется в отчётах и именах артефактов, чтобы прогон
воспроизводился по версии параметров (правило 4 проекта).
"""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

import yaml

_REQUIRED_FIELDS = ("version", "framing", "vad")


def load_config(path: str | Path) -> dict[str, Any]:
    with open(path, "r", encoding="utf-8") as handle:
        config = yaml.safe_load(handle)
    if not isinstance(config, dict):
        raise ValueError("config root must be a mapping")
    validate_config(config)
    return config


def config_hash(config: dict[str, Any]) -> str:
    """Стабильный (SHA256, 16 hex) хеш конфигурации."""
    serialized = yaml.safe_dump(config, sort_keys=True, allow_unicode=True)
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()[:16]


def validate_config(config: dict[str, Any]) -> None:
    missing = [field for field in _REQUIRED_FIELDS if field not in config]
    if missing:
        raise ValueError(f"missing required config fields: {', '.join(missing)}")
