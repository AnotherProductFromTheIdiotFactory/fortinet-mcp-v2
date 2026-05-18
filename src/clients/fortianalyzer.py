from __future__ import annotations

from typing import Any, Optional
import httpx

from clients.base import build_client
from config import FortiAnalyzerConfig


class FortiAnalyzerClient:
    """FortiAnalyzer JSON-RPC API client."""

    def __init__(self, cfg: FortiAnalyzerConfig):
        self._cfg = cfg
        self._client: Optional[httpx.AsyncClient] = None
        self._session: Optional[str] = None
        self._req_id = 0

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = build_client(self._cfg.host, self._cfg.port, self._cfg.verify_ssl)
        return self._client

    def _next_id(self) -> int:
        self._req_id += 1
        return self._req_id

    async def _rpc(self, method: str, params: list[dict], require_session: bool = True) -> dict:
        client = await self._get_client()
        if require_session and not self._session:
            await self.login()
        body: dict[str, Any] = {
            "id": self._next_id(),
            "method": method,
            "params": params,
            "jsonrpc": "2.0",
        }
        if self._session:
            body["session"] = self._session
        resp = await client.post("/jsonrpc", json=body)
        resp.raise_for_status()
        data = resp.json()
        result = data.get("result", [{}])
        first = result[0] if isinstance(result, list) else result
        status = first.get("status", {})
        if status.get("code", 0) not in (0, 200) and require_session:
            raise RuntimeError(f"FAZ RPC error {status.get('code')}: {status.get('message')}")
        return data

    async def login(self):
        data = await self._rpc(
            "exec",
            [{"url": "/sys/login/user", "data": {"user": self._cfg.username, "passwd": self._cfg.password}}],
            require_session=False,
        )
        self._session = data.get("session")
        if not self._session:
            raise RuntimeError("FortiAnalyzer login failed: no session returned")

    async def logout(self):
        if self._session:
            await self._rpc("exec", [{"url": "/sys/logout"}])
            self._session = None

    async def get(self, url: str, params: Optional[dict] = None) -> dict:
        p = {"url": url}
        if params:
            p.update(params)
        return await self._rpc("get", [p])

    async def add(self, url: str, data: dict) -> dict:
        return await self._rpc("add", [{"url": url, "data": data}])

    async def exec(self, url: str, data: Optional[dict] = None) -> dict:
        p: dict[str, Any] = {"url": url}
        if data:
            p["data"] = data
        return await self._rpc("exec", [p])

    # ── System ─────────────────────────────────────────────────────────────

    async def get_system_status(self) -> dict:
        return await self.get("/sys/status")

    async def get_adoms(self) -> dict:
        return await self.get("/dvmdb/adom")

    # ── Device Registration ──────────────────────────────────────────────────

    async def get_devices(self, adom: Optional[str] = None) -> dict:
        adom = adom or self._cfg.adom
        return await self.get(f"/dvmdb/adom/{adom}/device")

    async def get_device_groups(self, adom: Optional[str] = None) -> dict:
        adom = adom or self._cfg.adom
        return await self.get(f"/dvmdb/adom/{adom}/group")

    async def register_device(self, device_data: dict, adom: Optional[str] = None) -> dict:
        adom = adom or self._cfg.adom
        return await self.exec(
            "/dvm/cmd/add/device",
            {"adom": adom, "device": device_data},
        )

    # ── Log Queries ──────────────────────────────────────────────────────────

    async def query_logs(
        self,
        adom: Optional[str] = None,
        device: str = "All_FortiGate",
        log_type: str = "traffic",
        filter: Optional[list] = None,
        time_from: Optional[int] = None,
        time_to: Optional[int] = None,
        limit: int = 100,
        offset: int = 0,
        fields: Optional[list[str]] = None,
    ) -> dict:
        adom = adom or self._cfg.adom
        data: dict[str, Any] = {
            "device": device,
            "logtype": log_type,
            "limit": limit,
            "offset": offset,
        }
        if filter:
            data["filter"] = filter
        if time_from:
            data["time-from"] = time_from
        if time_to:
            data["time-to"] = time_to
        if fields:
            data["fields"] = fields
        return await self.exec(f"/logview/adom/{adom}/logsearch", data)

    async def get_log_fields(
        self, log_type: str = "traffic", adom: Optional[str] = None
    ) -> dict:
        adom = adom or self._cfg.adom
        return await self.get(
            f"/logview/adom/{adom}/log/fields",
            {"logtype": log_type},
        )

    async def start_log_search(
        self,
        adom: Optional[str] = None,
        log_type: str = "traffic",
        filter: Optional[list] = None,
        time_from: Optional[int] = None,
        time_to: Optional[int] = None,
        limit: int = 1000,
    ) -> dict:
        adom = adom or self._cfg.adom
        data: dict[str, Any] = {"logtype": log_type, "limit": limit}
        if filter:
            data["filter"] = filter
        if time_from:
            data["time-from"] = time_from
        if time_to:
            data["time-to"] = time_to
        return await self.exec(f"/logview/adom/{adom}/logsearch/start", data)

    # ── Reports ──────────────────────────────────────────────────────────────

    async def get_reports(self, adom: Optional[str] = None) -> dict:
        adom = adom or self._cfg.adom
        return await self.get(f"/report/adom/{adom}/reports/browse")

    async def get_report_templates(self, adom: Optional[str] = None) -> dict:
        adom = adom or self._cfg.adom
        return await self.get(f"/report/adom/{adom}/template")

    async def run_report(
        self,
        template_name: str,
        time_from: int,
        time_to: int,
        device: str = "All_FortiGate",
        adom: Optional[str] = None,
    ) -> dict:
        adom = adom or self._cfg.adom
        return await self.exec(
            f"/report/adom/{adom}/run",
            {
                "template": template_name,
                "device": device,
                "time-from": time_from,
                "time-to": time_to,
            },
        )

    async def get_report_status(self, tid: int, adom: Optional[str] = None) -> dict:
        adom = adom or self._cfg.adom
        return await self.get(f"/report/adom/{adom}/run/{tid}")

    async def download_report(self, tid: int, adom: Optional[str] = None) -> dict:
        adom = adom or self._cfg.adom
        return await self.exec(f"/report/adom/{adom}/run/{tid}/download", {"format": "pdf"})

    # ── Incidents & Events ───────────────────────────────────────────────────

    async def get_incidents(
        self,
        adom: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 50,
    ) -> dict:
        adom = adom or self._cfg.adom
        data: dict[str, Any] = {"limit": limit}
        if status:
            data["filter"] = [["status", "==", status]]
        return await self.exec(f"/incidentmgmt/adom/{adom}/incidents/list", data)

    async def get_event_handlers(self, adom: Optional[str] = None) -> dict:
        adom = adom or self._cfg.adom
        return await self.get(f"/eventmgmt/adom/{adom}/alertfilter")

    async def get_events(
        self,
        adom: Optional[str] = None,
        severity: Optional[str] = None,
        limit: int = 100,
    ) -> dict:
        adom = adom or self._cfg.adom
        data: dict[str, Any] = {"limit": limit}
        if severity:
            data["filter"] = [["severity", "==", severity]]
        return await self.exec(f"/eventmgmt/adom/{adom}/events", data)

    # ── FortiView / Statistics ───────────────────────────────────────────────

    async def get_traffic_summary(
        self,
        adom: Optional[str] = None,
        time_period: int = 86400,
        device: str = "All_FortiGate",
    ) -> dict:
        adom = adom or self._cfg.adom
        return await self.exec(
            f"/logview/adom/{adom}/stats",
            {"device": device, "period": time_period, "logtype": "traffic"},
        )

    async def get_threat_summary(
        self,
        adom: Optional[str] = None,
        time_period: int = 86400,
        device: str = "All_FortiGate",
    ) -> dict:
        adom = adom or self._cfg.adom
        return await self.exec(
            f"/logview/adom/{adom}/stats",
            {"device": device, "period": time_period, "logtype": "threat"},
        )

    async def get_top_sources(
        self,
        adom: Optional[str] = None,
        time_period: int = 3600,
        limit: int = 20,
    ) -> dict:
        adom = adom or self._cfg.adom
        return await self.exec(
            f"/fortiview/adom/{adom}/browse",
            {"view": "top-source-ip", "period": time_period, "limit": limit},
        )

    async def get_top_threats(
        self,
        adom: Optional[str] = None,
        time_period: int = 3600,
        limit: int = 20,
    ) -> dict:
        adom = adom or self._cfg.adom
        return await self.exec(
            f"/fortiview/adom/{adom}/browse",
            {"view": "top-threat", "period": time_period, "limit": limit},
        )

    async def get_top_applications(
        self,
        adom: Optional[str] = None,
        time_period: int = 3600,
        limit: int = 20,
    ) -> dict:
        adom = adom or self._cfg.adom
        return await self.exec(
            f"/fortiview/adom/{adom}/browse",
            {"view": "top-application", "period": time_period, "limit": limit},
        )

    async def close(self):
        if self._client:
            await self._client.aclose()
            self._client = None
