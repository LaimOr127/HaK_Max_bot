from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from typing import Any

SECRET_KEYS = {"authorization", "token", "secret", "password", "api_key", "contact"}


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "ts": datetime.now(UTC).isoformat(),
            "level": record.levelname,
            "service": "benefit-navigator",
            "event": record.getMessage(),
        }
        if record.exc_info:
            error_type = record.exc_info[0]
            if error_type is not None:
                payload["error_type"] = error_type.__name__
        for key, value in record.__dict__.items():
            if key in {"correlation_id", "max_user_id_hash", "state", "update_type", "duration_ms"}:
                payload[key] = value
        return json.dumps(_redact(payload), ensure_ascii=False)


def configure_logging(level: str) -> None:
    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter())
    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(level.upper())


def _redact(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: "***" if _is_secret_key(key) else _redact(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_redact(item) for item in value]
    return value


def _is_secret_key(key: str) -> bool:
    lowered = key.lower()
    return any(part in lowered for part in SECRET_KEYS)
