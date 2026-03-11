"""Load and validate health check configuration from YAML."""

import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

import yaml

ENV_VAR_PATTERN = re.compile(r"\$\{(\w+)\}")


def expand_env_vars(value: Any) -> Any:
    """Recursively expand ${VAR_NAME} in strings, dicts, and lists."""
    if isinstance(value, str):
        return ENV_VAR_PATTERN.sub(lambda m: os.environ.get(m.group(1), m.group(0)), value)
    if isinstance(value, dict):
        return {k: expand_env_vars(v) for k, v in value.items()}
    if isinstance(value, list):
        return [expand_env_vars(item) for item in value]
    return value


@dataclass
class Endpoint:
    name: str
    url: str
    method: str = "GET"
    timeout: int = 10
    expected_status: int = 200
    headers: dict = field(default_factory=dict)
    body: Optional[dict] = None


@dataclass
class AlertConfig:
    consecutive_failures: int = 3
    webhook_url: str = ""


@dataclass
class Config:
    check_interval: int
    endpoints: list[Endpoint]
    alerts: AlertConfig


def load_config(path: str) -> Config:
    """Load config from YAML file, expanding environment variables."""
    config_path = Path(path)
    if not config_path.exists():
        raise FileNotFoundError(f"Config not found: {path}")

    with open(config_path) as f:
        raw = yaml.safe_load(f)

    raw = expand_env_vars(raw)

    check_interval = int(os.environ.get("CHECK_INTERVAL", raw.get("check_interval", 30)))

    endpoints = [
        Endpoint(
            name=ep["name"],
            url=ep["url"],
            method=ep.get("method", "GET").upper(),
            timeout=ep.get("timeout", 10),
            expected_status=ep.get("expected_status", 200),
            headers=ep.get("headers", {}),
            body=ep.get("body"),
        )
        for ep in raw.get("endpoints", [])
    ]

    alert_raw = raw.get("alerts", {})
    alerts = AlertConfig(
        consecutive_failures=alert_raw.get("consecutive_failures", 3),
        webhook_url=alert_raw.get("webhook_url", ""),
    )

    return Config(check_interval=check_interval, endpoints=endpoints, alerts=alerts)
