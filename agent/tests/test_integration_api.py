from __future__ import annotations

import os
import unittest

import httpx


class TestIntegrationApi(unittest.TestCase):
    def test_health_if_server_running(self) -> None:
        """
        Lightweight integration check.

        If the API server isn't running, skip (CI/local may not have docker up).
        """
        base = os.environ.get("API_SERVER_URL", "http://localhost:8080")
        try:
            r = httpx.get(f"{base}/api/health", timeout=1.0)
        except Exception:
            self.skipTest("API server not reachable")
            return

        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json().get("status"), "ok")


if __name__ == "__main__":
    unittest.main()
