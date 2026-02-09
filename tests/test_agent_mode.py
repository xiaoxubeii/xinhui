# -*- coding: utf-8 -*-

from __future__ import annotations

import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient


class TestAgentMode(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls._tmp = Path(tempfile.mkdtemp(prefix="xinhui-test-"))
        data_root = cls._tmp / "data"
        os.environ["XINHUI_DATA_ROOT"] = str(data_root)
        os.environ["XINHUI_DB_PATH"] = str(data_root / "xinhui.db")
        os.environ["XINHUI_JWT_SECRET"] = "test-secret"
        # Make OpenCode fail fast so chat falls back deterministically.
        os.environ["OPENCODE_BASE_URL"] = "http://127.0.0.1:1"
        # Make Qwen unavailable (fallback should degrade gracefully).
        os.environ.pop("QWEN_API_KEY", None)

        # Ensure settings/app reflect the env vars above.
        for name in list(sys.modules.keys()):
            if name.startswith("backend."):
                sys.modules.pop(name, None)

        from backend.api import app  # noqa: WPS433 (import inside test for env control)

        cls.client = TestClient(app)

    @classmethod
    def tearDownClass(cls) -> None:
        try:
            cls.client.close()
        except Exception:
            pass
        shutil.rmtree(cls._tmp, ignore_errors=True)

    def test_auth_required(self) -> None:
        from backend.api import app  # noqa: WPS433

        unauth = TestClient(app)
        resp = unauth.get("/api/chat/sessions?agent_id=report")
        self.assertEqual(resp.status_code, 401)
        unauth.close()

    def test_register_login_upload_and_chat(self) -> None:
        email = "demo@example.com"
        password = "password123"

        resp = self.client.post("/api/auth/register", json={"email": email, "password": password})
        # Register may be called multiple times across local runs.
        self.assertIn(resp.status_code, (200, 400))

        resp = self.client.post("/api/auth/login", json={"email": email, "password": password})
        self.assertEqual(resp.status_code, 200)

        resp = self.client.get("/api/auth/me")
        self.assertEqual(resp.status_code, 200)

        # Create API key for token-based access.
        resp = self.client.post("/api/api-keys", json={"name": "test"})
        self.assertEqual(resp.status_code, 200)
        api_key_payload = resp.json()
        api_key = api_key_payload["api_key"]
        api_key_id = api_key_payload["id"]

        from backend.api import app  # noqa: WPS433

        api_client = TestClient(app)
        resp = api_client.get("/api/auth/me", headers={"x-api-key": api_key})
        self.assertEqual(resp.status_code, 200)
        api_client.close()

        resp = self.client.post("/api/chat/sessions", json={"agent_id": "report", "title": "新会话"})
        self.assertEqual(resp.status_code, 200)
        session_id = resp.json()["id"]

        # Upload a small CSV and attach to the session.
        resp = self.client.post(
            "/api/artifacts/upload",
            data={"category": "cpet_report", "attach_session_id": session_id},
            files={"file": ("results.csv", "key,value\nVO2peak,20\n", "text/csv")},
        )
        self.assertEqual(resp.status_code, 200)

        resp = self.client.get(f"/api/chat/sessions/{session_id}")
        self.assertEqual(resp.status_code, 200)
        detail = resp.json()
        self.assertGreaterEqual(len(detail.get("artifacts", [])), 1)

        # Send a message (OpenCode fails; Qwen missing; should still return a graceful answer).
        resp = self.client.post(
            f"/api/chat/sessions/{session_id}/message",
            json={"content": "hello"},
            headers={"accept": "application/json"},
        )
        self.assertEqual(resp.status_code, 200)
        payload = resp.json()
        self.assertEqual(payload.get("status"), "ok")
        self.assertIn("AI 服务不可用", payload.get("answer", ""))

        resp = self.client.get(f"/api/chat/sessions/{session_id}")
        self.assertEqual(resp.status_code, 200)
        detail = resp.json()
        self.assertGreaterEqual(len(detail.get("messages", [])), 2)

        # Revoke API key and ensure access is denied.
        resp = self.client.delete(f"/api/api-keys/{api_key_id}")
        self.assertEqual(resp.status_code, 200)
        revoked_client = TestClient(app)
        resp = revoked_client.get("/api/auth/me", headers={"x-api-key": api_key})
        self.assertEqual(resp.status_code, 401)
        revoked_client.close()


if __name__ == "__main__":
    unittest.main()
