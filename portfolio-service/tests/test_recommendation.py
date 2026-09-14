"""Tests for last-recommendation GET/PUT on portfolio-service."""

from __future__ import annotations

import os
import unittest
from unittest.mock import MagicMock

os.environ["DATABASE_URL"] = "sqlite://"

from fastapi.testclient import TestClient

from db import get_db
from main import app
from models import Recommendation


class _Store:
    def __init__(self) -> None:
        self.rows: dict[int, Recommendation] = {}

    def get(self, _model, user_id: int):
        return self.rows.get(user_id)

    def execute(self, stmt):  # noqa: ANN001
        params = stmt.compile().params
        user_id = params["user_id"]
        body = params["body"]
        self.rows[user_id] = Recommendation(user_id=user_id, body=body)
        return MagicMock()

    def commit(self) -> None:
        return None


class RecommendationApiTests(unittest.TestCase):
    def setUp(self) -> None:
        self.store = _Store()
        app.dependency_overrides[get_db] = lambda: self.store
        self.client = TestClient(app)

    def tearDown(self) -> None:
        app.dependency_overrides.clear()

    def test_get_empty(self) -> None:
        response = self.client.get("/recommendation", params={"user_id": 1})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"user_id": 1, "body": None})

    def test_put_then_get(self) -> None:
        put = self.client.put(
            "/recommendation",
            json={"user_id": 1, "body": "Hold AAPL"},
        )
        self.assertEqual(put.status_code, 200)
        self.assertEqual(put.json()["body"], "Hold AAPL")
        got = self.client.get("/recommendation", params={"user_id": 1})
        self.assertEqual(got.json()["body"], "Hold AAPL")

    def test_second_put_replaces(self) -> None:
        self.client.put("/recommendation", json={"user_id": 1, "body": "first"})
        self.client.put("/recommendation", json={"user_id": 1, "body": "second"})
        got = self.client.get("/recommendation", params={"user_id": 1})
        self.assertEqual(got.json()["body"], "second")


if __name__ == "__main__":
    unittest.main()
