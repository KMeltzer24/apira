"""Push structured log lines to Grafana Cloud Loki."""

from __future__ import annotations

import json
import logging
import os
from collections import defaultdict
from datetime import datetime, timezone
from typing import Any

import httpx

logger = logging.getLogger("apira.log_service.loki")


def _ns_timestamp(entry: dict[str, Any]) -> str:
    raw = entry.get("timestamp")
    if isinstance(raw, str) and raw:
        try:
            dt = datetime.fromisoformat(raw.replace("Z", "+00:00"))
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return str(int(dt.timestamp() * 1_000_000_000))
        except ValueError:
            pass
    return str(int(datetime.now(timezone.utc).timestamp() * 1_000_000_000))


def _stream_labels(entry: dict[str, Any]) -> tuple[tuple[str, str], ...]:
    service = str(entry.get("service") or "unknown")[:64]
    level = str(entry.get("level") or "INFO").upper()[:16]
    environment = str(entry.get("environment") or "development")[:32]
    return (
        ("job", "apira"),
        ("service", service),
        ("level", level),
        ("environment", environment),
        ("source", "log-service"),
    )


async def push_entries(entries: list[dict[str, Any]]) -> None:
    url = os.getenv("GRAFANA_LOKI_URL", "").strip()
    user = os.getenv("GRAFANA_LOKI_USER", "").strip()
    token = os.getenv("GRAFANA_LOKI_API_KEY", "").strip()
    if not url or not user or not token:
        logger.warning(
            "Grafana Loki credentials missing; skipping cloud push",
            extra={"event": "loki.push.skipped"},
        )
        return

    grouped: dict[tuple[tuple[str, str], ...], list[list[str]]] = defaultdict(list)
    for entry in entries:
        labels = _stream_labels(entry)
        line = json.dumps(entry, separators=(",", ":"), ensure_ascii=False)
        grouped[labels].append([_ns_timestamp(entry), line])

    payload = {
        "streams": [
            {"stream": dict(labels), "values": values}
            for labels, values in grouped.items()
        ]
    }

    timeout = httpx.Timeout(10.0, connect=5.0)
    async with httpx.AsyncClient(timeout=timeout) as client:
        response = await client.post(
            url,
            json=payload,
            auth=(user, token),
            headers={"Content-Type": "application/json"},
        )
        if response.status_code >= 300:
            logger.error(
                "Loki push failed",
                extra={
                    "event": "loki.push.failed",
                    "status_code": response.status_code,
                    "error_type": "LokiPushError",
                },
            )
            response.raise_for_status()
