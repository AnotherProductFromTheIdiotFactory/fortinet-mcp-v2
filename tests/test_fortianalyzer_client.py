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

    async def test_v8_log_search_uses_add_and_flattened_params(self):
        bodies = []

        def handler(request: httpx.Request) -> httpx.Response:
            body = json.loads(request.content)
            bodies.append(body)
            if body["params"][0]["url"] == "/sys/login/user":
                return response({"session": "session-1", "result": [{"status": {"code": 0}}]})
            return response({"result": [{"status": {"code": 0}, "data": {"tid": 42}}]})

        client = self.make_client(handler)
        await client.query_logs(
            time_from="2026-06-19T00:00:00Z",
            time_to="2026-06-20T00:00:00Z",
            filter="action='deny'",
        )

        call = bodies[1]
        params = call["params"][0]
        self.assertEqual(call["method"], "add")
        self.assertEqual(params["url"], "/logview/adom/root/logsearch")
        self.assertEqual(params["apiver"], 3)
        self.assertEqual(params["device"], [{"devid": "All_FortiGate"}])
        self.assertEqual(params["time-range"]["start"], "2026-06-19T00:00:00Z")
        self.assertNotIn("data", params)
        await client.close()

    async def test_v8_report_and_fortiview_paths_match_openapi(self):
        bodies = []

        def handler(request: httpx.Request) -> httpx.Response:
            body = json.loads(request.content)
            bodies.append(body)
            if body["params"][0]["url"] == "/sys/login/user":
                return response({"session": "session-1", "result": [{"status": {"code": 0}}]})
            return response({"result": [{"status": {"code": 0}}]})

        client = self.make_client(handler)
        await client.download_report(7)
        await client.start_fortiview(
            "top-sources", "2026-06-19T00:00:00Z", "2026-06-20T00:00:00Z"
        )

        report = bodies[1]
        fortiview = bodies[2]
        self.assertEqual(report["method"], "get")
        self.assertEqual(report["params"][0]["url"], "/report/adom/root/reports/data/7")
        self.assertEqual(report["params"][0]["format"], "PDF")
        self.assertEqual(fortiview["method"], "add")
        self.assertEqual(
            fortiview["params"][0]["url"], "/fortiview/adom/root/top-sources/run"
        )
        self.assertEqual(fortiview["params"][0]["apiver"], 3)
        await client.close()

    async def test_execute_method_is_available_for_v8_soar_operations(self):
        bodies = []

        def handler(request: httpx.Request) -> httpx.Response:
            body = json.loads(request.content)
            bodies.append(body)
            if body["params"][0]["url"] == "/sys/login/user":
                return response({"session": "session-1", "result": [{"status": {"code": 0}}]})
            return response({"result": [{"status": {"code": 0}}]})

        client = self.make_client(handler)
        await client.request(
            "execute",
            "/soar/adom/root/indicator/block/",
            params={"apiver": 3, "indicator-uuid": ["indicator-id"]},
        )
        self.assertEqual(bodies[1]["method"], "execute")
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
