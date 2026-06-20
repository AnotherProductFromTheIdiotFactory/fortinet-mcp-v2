from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from clients.fortigate import FortiGateClient
from config import FortiGateConfig


def response(payload: dict, status_code: int = 200, headers: dict | None = None) -> httpx.Response:
    return httpx.Response(status_code, json=payload, headers=headers)


class FortiGateClientTests(unittest.IsolatedAsyncioTestCase):
    def make_client(self, handler, *, api_key: str | None = None) -> FortiGateClient:
        cfg = FortiGateConfig(
            id="fgt-test",
            name="Test FGT",
            host="fgt.example.test",
            api_key=api_key,
            username=None if api_key else "api-user",
            password=None if api_key else "secret",
            vdom="root",
        )
        client = FortiGateClient(cfg)
        client._client = httpx.AsyncClient(
            base_url="https://fgt.example.test",
            transport=httpx.MockTransport(handler),
        )
        return client

    async def test_request_injects_auth_and_default_vdom(self):
        seen = []

        def handler(request: httpx.Request) -> httpx.Response:
            seen.append(request)
            if request.url.path == "/logincheck":
                return httpx.Response(
                    200,
                    text="1",
                    headers={"set-cookie": "APSCOOKIE_443=session-1; Path=/"},
                )
            return response({"status": "success", "results": []})

        client = self.make_client(handler)
        result = await client.request(
            "get",
            "/api/v2/cmdb/firewall/address",
            params={"filter": "name==web1"},
        )

        self.assertEqual(result["status"], "success")
        self.assertEqual(seen[1].url.params["vdom"], "root")
        self.assertEqual(seen[1].url.params["filter"], "name==web1")
        self.assertIn("APSCOOKIE_443=session-1", seen[1].headers["Cookie"])
        await client.close()

    async def test_api_key_request_uses_query_token_without_login(self):
        seen = []

        def handler(request: httpx.Request) -> httpx.Response:
            seen.append(request)
            return response({"status": "success"})

        client = self.make_client(handler, api_key="token-123")
        await client.request("get", "/api/v2/monitor/system/status", include_vdom=False)

        self.assertEqual(len(seen), 1)
        self.assertEqual(seen[0].url.params["access_token"], "token-123")
        self.assertNotIn("Cookie", seen[0].headers)
        await client.close()

    async def test_expired_session_reauthenticates_once(self):
        seen = []

        def handler(request: httpx.Request) -> httpx.Response:
            seen.append(request)
            if request.url.path == "/logincheck":
                session = f"session-{sum(1 for r in seen if r.url.path == '/logincheck')}"
                return httpx.Response(
                    200,
                    text="1",
                    headers={"set-cookie": f"APSCOOKIE_443={session}; Path=/"},
                )
            if sum(1 for r in seen if r.url.path == "/api/v2/monitor/system/status") == 1:
                return response({"error": "expired"}, status_code=401)
            return response({"status": "success", "version": "v8.0"})

        client = self.make_client(handler)
        result = await client.get_system_status()

        self.assertEqual(result["version"], "v8.0")
        cookies = [
            request.headers["Cookie"]
            for request in seen
            if request.url.path == "/api/v2/monitor/system/status"
        ]
        self.assertEqual(cookies, ["APSCOOKIE_443=session-1", "APSCOOKIE_443=session-2"])
        await client.close()

    async def test_text_response_is_returned_without_json_decoding(self):
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, text="backup-content", headers={"content-type": "text/plain"})

        client = self.make_client(handler, api_key="token-123")
        result = await client.request(
            "get",
            "/api/v2/monitor/system/config/backup",
            params={"scope": "global"},
            include_vdom=False,
        )

        self.assertEqual(result, "backup-content")
        await client.close()

    def test_request_validation_rejects_unsafe_or_unknown_targets(self):
        for method, path in [
            ("patch", "/api/v2/cmdb/firewall/address"),
            ("get", "api/v2/cmdb/firewall/address"),
            ("get", "//example.test/api/v2/cmdb/firewall/address"),
            ("post", "/logincheck"),
            ("post", "/logout"),
            ("get", "/api/v1/cmdb/firewall/address"),
        ]:
            with self.subTest(method=method, path=path), self.assertRaises(ValueError):
                FortiGateClient._validate_request(method, path)


if __name__ == "__main__":
    unittest.main()
