import json
import logging
import os
import unittest
import uuid
from unittest.mock import patch

from logging_config import (
    JsonFormatter,
    RequestLoggingMiddleware,
    redact,
    request_id_var,
    safe_request_id,
)


class RecordHandler(logging.Handler):
    def __init__(self) -> None:
        super().__init__()
        self.records: list[logging.LogRecord] = []

    def emit(self, record: logging.LogRecord) -> None:
        self.records.append(record)


class LoggingHelpersTest(unittest.TestCase):
    def test_json_formatter_emits_contract_and_redacts_sensitive_extras(self):
        formatter = JsonFormatter()
        record = logging.LogRecord(
            "test", logging.INFO, __file__, 1, "Safe message", (), None
        )
        record.event = "test_event"
        record.holdings_count = 3
        record.portfolio = {"secret": "content"}

        token = request_id_var.set("4c37e820-e749-4c22-8487-fb9a9a86b127")
        try:
            with patch.dict(
                os.environ,
                {"SERVICE_NAME": "portfolio-service", "ENVIRONMENT": "test"},
            ):
                result = json.loads(formatter.format(record))
        finally:
            request_id_var.reset(token)

        for key in (
            "timestamp",
            "level",
            "service",
            "environment",
            "event",
            "message",
            "request_id",
        ):
            self.assertIn(key, result)
        self.assertEqual(result["service"], "portfolio-service")
        self.assertEqual(result["holdings_count"], 3)
        self.assertEqual(result["portfolio"], "[REDACTED]")

    def test_redact_handles_nested_secret_keys(self):
        self.assertEqual(
            redact(
                {
                    "safe": [{"authorization": "Bearer secret"}],
                    "database_url": "postgresql://secret",
                }
            ),
            {
                "safe": [{"authorization": "[REDACTED]"}],
                "database_url": "[REDACTED]",
            },
        )

    def test_request_id_accepts_canonical_uuid_and_replaces_other_values(self):
        valid = "4c37e820-e749-4c22-8487-fb9a9a86b127"
        self.assertEqual(safe_request_id(valid), valid)

        generated = safe_request_id("not-a-uuid")
        self.assertEqual(str(uuid.UUID(generated)), generated)


class RequestLoggingMiddlewareTest(unittest.IsolatedAsyncioTestCase):
    async def test_generates_and_echoes_safe_request_id(self):
        sent = []
        handler = RecordHandler()
        logger = logging.Logger("test.middleware")
        logger.addHandler(handler)

        async def capture(message):
            sent.append(message)

        async def app(scope, receive, send):
            await send(
                {
                    "type": "http.response.start",
                    "status": 200,
                    "headers": [],
                }
            )
            await send({"type": "http.response.body", "body": b"{}"})

        async def receive():
            return {"type": "http.disconnect"}

        scope = {
            "type": "http",
            "method": "GET",
            "path": "/portfolio",
            "headers": [(b"x-request-id", b"unsafe")],
        }
        await RequestLoggingMiddleware(app, logger)(scope, receive, capture)

        response_id = dict(sent[0]["headers"])[b"x-request-id"].decode()
        self.assertEqual(str(uuid.UUID(response_id)), response_id)
        record = handler.records[0]
        self.assertEqual(record.event, "request_completed")
        self.assertEqual(record.path, "/portfolio")
        self.assertEqual(record.status_code, 200)
        self.assertIsNone(request_id_var.get())


if __name__ == "__main__":
    unittest.main()
