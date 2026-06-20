from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from clients.fortianalyzer import FortiAnalyzerClient
from config import FortiAnalyzerConfig


def response(payload: dict) -> httpx.Response:
    return httpx.Response(200, json=payload)


class FortiAnalyzerClientTests(unittest.IsolatedAsyncioTestCase):
    def make_client(self, handler) -> FortiAnalyzerClient:
        cfg = FortiAnalyzerConfig(
            id="faz-test",
            name="Test FAZ",
            host="faz.example.test",
            username="api-user",
            password="secret",
        )
        client = FortiAnalyzerClient(cfg)
        client._client = httpx.AsyncClient(
            base_url="https://faz.example.test",
            transport=httpx.MockTransport(handler),
        )
        return client

    async def test_request_supports_all_v8_rpc_parameters(self):
        bodies = []

        def handler(request: httpx.Request) -> httpx.Response:
            body = json.loads(request.content)
            bodies.append(body)
            if body["params"][0]["url"] == "/sys/login/user":
                return response({"id": body["id"], "session": "session-1", "result": [{"status": {"code": 0}}]})
            return response({"id": body["id"], "result": [{"status": {"code": 0}, "data": []}]})

        client = self.make_client(handler)
        result = await client.request(
            "get",
            "/logview/adom/root/logsearch",
            params={"filter": [["action", "==", "deny"]], "fields": ["srcip"], "range": [0, 99]},
        )

        self.assertEqual(result["result"][0]["status"]["code"], 0)
        self.assertEqual(bodies[1]["session"], "session-1")
        self.assertEqual(bodies[1]["params"][0]["fields"], ["srcip"])
        self.assertEqual(bodies[1]["verbose"], 1)
        await client.close()

    async def test_expired_session_reauthenticates_once(self):
        calls = []

        def handler(request: httpx.Request) -> httpx.Response:
            body = json.loads(request.content)
            calls.append(body)
            url = body["params"][0]["url"]
            if url == "/sys/login/user":
                session = f"session-{sum(1 for call in calls if call['params'][0]['url'] == '/sys/login/user')}"
                return response({"id": body["id"], "session": session, "result": [{"status": {"code": 0}}]})
            if sum(1 for call in calls if call["params"][0]["url"] == "/sys/status") == 1:
                return response({"id": body["id"], "result": [{"status": {"code": -11, "message": "No permission for the resource"}}]})
            return response({"id": body["id"], "result": [{"status": {"code": 0}, "data": {"Version": "v8.0"}}]})

        client = self.make_client(handler)
        result = await client.get_system_status()

        self.assertEqual(result["result"][0]["data"]["Version"], "v8.0")
        self.assertEqual([call["session"] for call in calls if call["params"][0]["url"] == "/sys/status"], ["session-1", "session-2"])
        await client.close()

    async def test_api_errors_are_not_returned_as_success(self):
        def handler(request: httpx.Request) -> httpx.Response:
            body = json.loads(request.content)
            if body["params"][0]["url"] == "/sys/login/user":
                return response({"session": "session-1", "result": [{"status": {"code": 0}}]})
            return response({"result": [{"status": {"code": -3, "message": "Object does not exist"}}]})

        client = self.make_client(handler)
        with self.assertRaisesRegex(RuntimeError, "FAZ RPC error -3: Object does not exist"):
            await client.get("/missing/object")
        await client.close()

    def test_request_validation_rejects_unsafe_or_unknown_targets(self):
        for method, url in [
            ("post", "/sys/status"),
            ("get", "sys/status"),
            ("get", "//external.example/path"),
            ("exec", "/sys/login/user"),
            ("exec", "/sys/logout"),
        ]:
            with self.subTest(method=method, url=url), self.assertRaises(ValueError):
                FortiAnalyzerClient._validate_request(method, url)


if __name__ == "__main__":
    unittest.main()
