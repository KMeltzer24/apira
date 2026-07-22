import asyncio
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
        record.user_id = 42
        record.password = "do-not-log"

        token = request_id_var.set("4c37e820-e749-4c22-8487-fb9a9a86b127")
        try:
            with patch.dict(
                os.environ,
                {"SERVICE_NAME": "user-service", "ENVIRONMENT": "test"},
            ):
                result = json.loads(formatter.format(record))
        finally:
            request_id_var.reset(token)

        self.assertEqual(
            {
                "timestamp",
                "level",
                "service",
                "environment",
                "event",
                "message",
                "request_id",
            },
            set(result).intersection(
                {
                    "timestamp",
                    "level",
                    "service",
                    "environment",
                    "event",
                    "message",
                    "request_id",
                }
            ),
        )
        self.assertEqual(result["service"], "user-service")
        self.assertEqual(result["environment"], "test")
        self.assertEqual(result["user_id"], 42)
        self.assertEqual(result["password"], "[REDACTED]")

    def test_redact_handles_nested_secret_keys(self):
        value = {
            "safe": [{"authorization": "Bearer secret"}],
            "database_url": "postgresql://secret",
            "username": "person",
        }
        self.assertEqual(
            redact(value),
            {
                "safe": [{"authorization": "[REDACTED]"}],
                "database_url": "[REDACTED]",
                "username": "[REDACTED]",
            },
        )

    def test_request_id_accepts_canonical_uuid_and_replaces_other_values(self):
        valid = "4c37e820-e749-4c22-8487-fb9a9a86b127"
        self.assertEqual(safe_request_id(valid), valid)

        generated = safe_request_id("../../unsafe\nvalue")
        self.assertNotEqual(generated, "../../unsafe\nvalue")
        self.assertEqual(str(uuid.UUID(generated)), generated)


class RequestLoggingMiddlewareTest(unittest.IsolatedAsyncioTestCase):
    async def test_echoes_request_id_and_logs_request_metadata(self):
        request_id = "4c37e820-e749-4c22-8487-fb9a9a86b127"
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
                    "status": 204,
                    "headers": [],
                }
            )
            await send({"type": "http.response.body", "body": b""})

        scope = {
            "type": "http",
            "method": "GET",
            "path": "/health",
            "headers": [(b"x-request-id", request_id.encode())],
        }

        await RequestLoggingMiddleware(app, logger)(
            scope, self._receive, capture
        )

        response_headers = dict(sent[0]["headers"])
        self.assertEqual(response_headers[b"x-request-id"].decode(), request_id)
        self.assertEqual(handler.records[0].event, "request_completed")
        self.assertEqual(handler.records[0].method, "GET")
        self.assertEqual(handler.records[0].path, "/health")
        self.assertEqual(handler.records[0].status_code, 204)
        self.assertIsNone(request_id_var.get())

    async def test_logs_exception_without_exception_message(self):
        sent = []
        handler = RecordHandler()
        logger = logging.Logger("test.middleware.exception")
        logger.addHandler(handler)

        async def capture(message):
            sent.append(message)

        async def app(scope, receive, send):
            raise RuntimeError("database URL must stay private")

        scope = {
            "type": "http",
            "method": "POST",
            "path": "/login",
            "headers": [],
        }

        await RequestLoggingMiddleware(app, logger)(
            scope, self._receive, capture
        )

        record = handler.records[0]
        self.assertEqual(record.event, "request_failed")
        self.assertEqual(record.error_type, "RuntimeError")
        self.assertNotIn("database URL", record.getMessage())
        self.assertEqual(sent[0]["status"], 500)
        response_id = dict(sent[0]["headers"])[b"x-request-id"].decode()
        self.assertEqual(str(uuid.UUID(response_id)), response_id)
        self.assertEqual(sent[1]["body"], b"Internal Server Error")
        self.assertIsNone(request_id_var.get())

    @staticmethod
    async def _receive():
        await asyncio.sleep(0)
        return {"type": "http.disconnect"}

if __name__ == "__main__":
    unittest.main()
