import json
import logging
import os
import sys
import time
import uuid
from contextvars import ContextVar, Token
from datetime import datetime, timezone
from typing import Any, Awaitable, Callable


request_id_var: ContextVar[str | None] = ContextVar("request_id", default=None)
Message = dict[str, Any]
Scope = dict[str, Any]
Receive = Callable[[], Awaitable[Message]]
Send = Callable[[Message], Awaitable[None]]
ASGIApp = Callable[[Scope, Receive, Send], Awaitable[None]]

_STANDARD_LOG_RECORD_FIELDS = set(logging.makeLogRecord({}).__dict__) | {
    "asctime",
    "message",
}
_SENSITIVE_KEYS = {
    "api_key",
    "authorization",
    "database_url",
    "db_url",
    "password",
    "portfolio",
    "prompt",
    "request_body",
    "response_body",
    "token",
    "username",
}


def _is_sensitive_key(key: str) -> bool:
    normalized = key.lower().replace("-", "_")
    compact = normalized.replace("_", "")
    return normalized in _SENSITIVE_KEYS or any(
        part in compact
        for part in (
            "apikey",
            "authorization",
            "credential",
            "databaseurl",
            "password",
            "requestbody",
            "responsebody",
            "secret",
            "token",
            "username",
        )
    )


def redact(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            str(key): "[REDACTED]" if _is_sensitive_key(str(key)) else redact(item)
            for key, item in value.items()
        }
    if isinstance(value, (list, tuple)):
        return [redact(item) for item in value]
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return str(value)


def safe_request_id(value: str | None) -> str:
    if value:
        try:
            parsed = uuid.UUID(value)
            if str(parsed) == value.lower():
                return str(parsed)
        except (ValueError, AttributeError):
            pass
    return str(uuid.uuid4())


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        fields = {
            "timestamp": datetime.fromtimestamp(
                record.created, tz=timezone.utc
            ).isoformat(timespec="milliseconds").replace("+00:00", "Z"),
            "level": record.levelname,
            "service": os.getenv("SERVICE_NAME", "user-service"),
            "environment": os.getenv("ENVIRONMENT", "development"),
            "event": getattr(record, "event", "application_log"),
            "message": record.getMessage(),
            "request_id": request_id_var.get(),
        }
        fields.update(
            {
                key: value
                for key, value in record.__dict__.items()
                if key not in _STANDARD_LOG_RECORD_FIELDS
                and key not in {"event"}
                and not key.startswith("_")
            }
        )
        return json.dumps(redact(fields), separators=(",", ":"), ensure_ascii=False)


class TextFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        request_id = request_id_var.get() or "-"
        event = getattr(record, "event", "application_log")
        return (
            f"{record.levelname} service={os.getenv('SERVICE_NAME', 'user-service')} "
            f"environment={os.getenv('ENVIRONMENT', 'development')} "
            f"event={event} request_id={request_id} message={record.getMessage()}"
        )


def configure_logging() -> None:
    level_name = os.getenv("LOG_LEVEL", "INFO").upper()
    level = getattr(logging, level_name, logging.INFO)
    handler = logging.StreamHandler(sys.stdout)
    if os.getenv("LOG_FORMAT", "json").lower() == "text":
        handler.setFormatter(TextFormatter())
    else:
        handler.setFormatter(JsonFormatter())

    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(level)


class RequestLoggingMiddleware:
    def __init__(self, app: ASGIApp, logger: logging.Logger | None = None) -> None:
        self.app = app
        self.logger = logger or logging.getLogger("apira.http")

    async def __call__(
        self, scope: Scope, receive: Receive, send: Send
    ) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        headers = dict(scope.get("headers", []))
        incoming = headers.get(b"x-request-id", b"").decode("ascii", errors="ignore")
        request_id = safe_request_id(incoming)
        token: Token[str | None] = request_id_var.set(request_id)
        started = time.perf_counter()
        status_code = 500
        response_started = False

        async def send_with_request_id(message: Message) -> None:
            nonlocal response_started, status_code
            if message["type"] == "http.response.start":
                response_started = True
                status_code = message["status"]
                response_headers = list(message.get("headers", []))
                response_headers = [
                    (key, value)
                    for key, value in response_headers
                    if key.lower() != b"x-request-id"
                ]
                response_headers.append((b"x-request-id", request_id.encode("ascii")))
                message["headers"] = response_headers
            await send(message)

        try:
            await self.app(scope, receive, send_with_request_id)
        except Exception as exc:
            self.logger.exception(
                "HTTP %s %s failed (%s)",
                scope["method"],
                scope["path"],
                type(exc).__name__,
                extra={
                    "event": "request_failed",
                    "method": scope["method"],
                    "path": scope["path"],
                    "status_code": status_code,
                    "duration_ms": round(
                        (time.perf_counter() - started) * 1000, 2
                    ),
                    "error_type": type(exc).__name__,
                },
            )
            if response_started:
                raise
            await send_with_request_id(
                {
                    "type": "http.response.start",
                    "status": 500,
                    "headers": [
                        (b"content-type", b"text/plain; charset=utf-8"),
                        (b"content-length", b"21"),
                    ],
                }
            )
            await send_with_request_id(
                {
                    "type": "http.response.body",
                    "body": b"Internal Server Error",
                }
            )
        else:
            self.logger.info(
                "HTTP %s %s completed (%s)",
                scope["method"],
                scope["path"],
                status_code,
                extra={
                    "event": "request_completed",
                    "method": scope["method"],
                    "path": scope["path"],
                    "status_code": status_code,
                    "duration_ms": round(
                        (time.perf_counter() - started) * 1000, 2
                    ),
                },
            )
        finally:
            request_id_var.reset(token)
