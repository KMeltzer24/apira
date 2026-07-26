"""Thin log ingest service: browser → EC2 file + Grafana Cloud Loki."""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from loki import push_entries

SERVICE_NAME = os.getenv("SERVICE_NAME", "log-service")
ENVIRONMENT = os.getenv("ENVIRONMENT", "development")
LOG_DIR = Path(os.getenv("LOG_DIR", "/var/log/apira"))
MAX_EVENTS = 100
MAX_MESSAGE_LEN = 200
MAX_EVENT_LEN = 100

SAFE_FIELDS = {
    "timestamp",
    "level",
    "service",
    "environment",
    "event",
    "message",
    "request_id",
    "user_id",
    "method",
    "path",
    "status_code",
    "duration_ms",
    "upstream",
    "error_type",
    "error_code",
    "source_path",
    "line_number",
    "column_number",
    "holdings_count",
    "tickers",
}

logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO").upper())
logger = logging.getLogger("apira.log_service")

app = FastAPI(title="Apira Log Service", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("CORS_ALLOW_ORIGINS", "*").split(","),
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)


class IngestRequest(BaseModel):
    events: list[dict[str, Any]] = Field(default_factory=list)


def _safe_value(key: str, value: Any) -> Any:
    if key in {"path", "source_path"} and isinstance(value, str):
        # Keep path only — drop query/fragment if a full URL slipped through.
        path = value.split("?", 1)[0].split("#", 1)[0]
        if "://" in path:
            try:
                from urllib.parse import urlparse

                return urlparse(path).path or "/"
            except Exception:
                return "/"
        return path[:200]
    if isinstance(value, str):
        return value[:200]
    if isinstance(value, bool) or value is None:
        return value
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return value
    if isinstance(value, list):
        return [_safe_value(key, item) for item in value[:20]]
    return None


def sanitize_event(raw: dict[str, Any]) -> dict[str, Any] | None:
    if not isinstance(raw, dict):
        return None

    level = str(raw.get("level") or "INFO").upper()
    if level not in {"DEBUG", "INFO", "WARNING", "ERROR"}:
        level = "INFO"

    event = str(raw.get("event") or "browser_log")[:MAX_EVENT_LEN]
    message = str(raw.get("message") or "")[:MAX_MESSAGE_LEN]
    service = str(raw.get("service") or "apira-frontend")[:64]
    environment = str(raw.get("environment") or ENVIRONMENT)[:32]
    timestamp = str(raw.get("timestamp") or "")[:40]

    entry: dict[str, Any] = {
        "timestamp": timestamp,
        "level": level,
        "service": service,
        "environment": environment,
        "event": event,
        "message": message,
    }

    for key, value in raw.items():
        if key in entry or key not in SAFE_FIELDS:
            continue
        cleaned = _safe_value(key, value)
        if cleaned is not None:
            entry[key] = cleaned

    if "request_id" not in entry:
        entry["request_id"] = None

    if not entry.get("timestamp"):
        from datetime import datetime, timezone

        entry["timestamp"] = datetime.now(timezone.utc).isoformat().replace(
            "+00:00", "Z"
        )

    return entry


def append_local(entries: list[dict[str, Any]]) -> Path:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    path = LOG_DIR / "frontend.jsonl"
    with path.open("a", encoding="utf-8") as handle:
        for entry in entries:
            handle.write(json.dumps(entry, separators=(",", ":"), ensure_ascii=False))
            handle.write("\n")
    return path


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "service": SERVICE_NAME}


@app.post("/v1/logs")
async def ingest_logs(body: IngestRequest) -> dict[str, Any]:
    if not body.events:
        return {"accepted": 0}

    if len(body.events) > MAX_EVENTS:
        raise HTTPException(
            status_code=400,
            detail=f"At most {MAX_EVENTS} events per request",
        )

    entries = [sanitized for raw in body.events if (sanitized := sanitize_event(raw))]
    if not entries:
        return {"accepted": 0}

    append_local(entries)

    try:
        await push_entries(entries)
    except Exception:
        logger.exception(
            "Failed to push browser logs to Loki",
            extra={"event": "loki.push.exception", "count": len(entries)},
        )
        # Local file write already succeeded; return 202 so the UI does not retry forever.
        return {"accepted": len(entries), "cloud": "failed"}

    return {"accepted": len(entries), "cloud": "ok"}
