"""Configuration loading and hashing utilities."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

import yaml


def load_config(path: str | Path) -> dict[str, Any]:
    """Загружает YAML-конфигурацию."""
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def config_hash(config: dict[str, Any]) -> str:
    """Вычисляет стабильный hash конфигурации для воспроизводимости."""
    serialized = yaml.dump(config, sort_keys=True, default_flow_style=False)
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()[:16]


def validate_config(config: dict[str, Any]) -> None:
    """Базовая валидация обязательных полей."""
    required = ["version", "framing", "vad", "taxonomy"]
    for field in required:
        if field not in config:
            raise ValueError(f"missing required config field: {field}")
