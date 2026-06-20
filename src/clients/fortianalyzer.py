from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional
import httpx

from clients.base import build_client
from config import FortiAnalyzerConfig


class FortiAnalyzerClient:
    """FortiAnalyzer JSON-RPC API client."""

    SUPPORTED_METHODS = frozenset(
        {"get", "add", "set", "update", "delete", "exec", "execute"}
    )
    SESSION_ERROR_CODES = frozenset({-11})

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

    @staticmethod
    def _result_statuses(data: dict) -> list[dict]:
        result = data.get("result", [])
        items = result if isinstance(result, list) else [result]
        return [item.get("status", {}) for item in items if isinstance(item, dict)]

    @classmethod
    def _validate_request(cls, method: str, url: str) -> None:
        if method not in cls.SUPPORTED_METHODS:
            supported = ", ".join(sorted(cls.SUPPORTED_METHODS))
            raise ValueError(f"Unsupported FortiAnalyzer JSON-RPC method '{method}'. Use: {supported}")
        if not url.startswith("/") or url.startswith("//"):
            raise ValueError("FortiAnalyzer JSON-RPC URL must be an absolute API path starting with '/'")
        if url in {"/sys/login/user", "/sys/logout"}:
            raise ValueError("Session endpoints are managed by the FortiAnalyzer client")

    async def _rpc(
        self,
        method: str,
        params: list[dict],
        require_session: bool = True,
        retry_session: bool = True,
    ) -> dict:
        client = await self._get_client()
        if require_session and not self._session:
            await self.login()
        body: dict[str, Any] = {
            "id": self._next_id(),
            "method": method,
            "params": params,
            "jsonrpc": "2.0",
            "verbose": 1,
        }
        if self._session:
            body["session"] = self._session
        resp = await client.post("/jsonrpc", json=body)
        resp.raise_for_status()
        data = resp.json()
        statuses = self._result_statuses(data)
        failed = next((s for s in statuses if s.get("code", 0) not in (0, 200)), None)
        if failed:
            code = failed.get("code")
            if require_session and retry_session and code in self.SESSION_ERROR_CODES:
                self._session = None
                await self.login()
                return await self._rpc(method, params, require_session=True, retry_session=False)
            raise RuntimeError(f"FAZ RPC error {code}: {failed.get('message', 'unknown error')}")
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

    async def request(
        self,
        method: str,
        url: str,
        data: Any = None,
        params: Optional[dict] = None,
    ) -> dict:
        """Call any supported FortiAnalyzer v8 JSON-RPC API endpoint.

        ``params`` contains endpoint controls such as ``filter``, ``fields``,
        ``option``, ``loadsub``, ``range``, ``sortings``, and ``target``.
        ``data`` is placed in the JSON-RPC parameter's ``data`` member.
        """
        method = method.lower().strip()
        self._validate_request(method, url)
        p: dict[str, Any] = {"url": url}
        if params:
            reserved = {"url", "data"}.intersection(params)
            if reserved:
                names = ", ".join(sorted(reserved))
                raise ValueError(f"Use the dedicated argument for reserved parameter(s): {names}")
            p.update(params)
        if data is not None:
            p["data"] = data
        return await self._rpc(method, [p])

    async def get(self, url: str, params: Optional[dict] = None) -> dict:
        return await self.request("get", url, params=params)

    async def add(self, url: str, data: dict) -> dict:
        return await self.request("add", url, data=data)

    async def set(self, url: str, data: dict) -> dict:
        return await self.request("set", url, data=data)

    async def update(self, url: str, data: dict) -> dict:
        return await self.request("update", url, data=data)

    async def delete(self, url: str, data: Any = None) -> dict:
        return await self.request("delete", url, data=data)

    async def exec(self, url: str, data: Optional[dict] = None) -> dict:
        return await self.request("exec", url, data=data)

    @staticmethod
    def _time_range(time_from: str | int, time_to: str | int) -> dict[str, str]:
        def normalize(value: str | int) -> str:
            if isinstance(value, int):
                return datetime.fromtimestamp(value, tz=timezone.utc).isoformat().replace("+00:00", "Z")
            return value

        return {"start": normalize(time_from), "end": normalize(time_to)}

    @staticmethod
    def _devices(device: str | list[dict]) -> list[dict]:
        return [{"devid": device}] if isinstance(device, str) else device

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

    # ── Log Queries ──────────────────────────────────────────────────────────

    async def query_logs(
        self,
        adom: Optional[str] = None,
        device: str | list[dict] = "All_FortiGate",
        log_type: str = "traffic",
        filter: Optional[str] = None,
        time_from: str | int = 0,
        time_to: str | int = 0,
        limit: int = 100,
        offset: int = 0,
        timezone_name: Optional[str] = None,
        case_sensitive: bool = False,
        time_order: str = "desc",
    ) -> dict:
        """Start a v8 log search and return its task ID."""
        adom = adom or self._cfg.adom
        params: dict[str, Any] = {
            "apiver": 3,
            "device": self._devices(device),
            "logtype": log_type,
            "time-range": self._time_range(time_from, time_to),
            "limit": limit,
            "offset": offset,
            "case-sensitive": case_sensitive,
            "time-order": time_order,
        }
        if filter:
            params["filter"] = filter
        if timezone_name:
            params["timezone"] = timezone_name
        return await self.request("add", f"/logview/adom/{adom}/logsearch", params=params)

    async def get_log_fields(
        self,
        log_type: str = "traffic",
        adom: Optional[str] = None,
        device_type: str = "FortiGate",
        subtype: str = "",
    ) -> dict:
        adom = adom or self._cfg.adom
        return await self.get(
            f"/logview/adom/{adom}/logfields",
            {"apiver": 3, "devtype": device_type, "logtype": log_type, "subtype": subtype},
        )

    async def start_log_search(
        self,
        adom: Optional[str] = None,
        log_type: str = "traffic",
        filter: Optional[str] = None,
        time_from: str | int = 0,
        time_to: str | int = 0,
        limit: int = 100,
        device: str | list[dict] = "All_FortiGate",
    ) -> dict:
        return await self.query_logs(
            adom=adom,
            device=device,
            log_type=log_type,
            filter=filter,
            time_from=time_from,
            time_to=time_to,
            limit=limit,
        )

    async def get_log_search_results(
        self, task_id: int, adom: Optional[str] = None, limit: int = 50, offset: int = 0
    ) -> dict:
        adom = adom or self._cfg.adom
        return await self.get(
            f"/logview/adom/{adom}/logsearch/{task_id}",
            {"apiver": 3, "limit": limit, "offset": offset},
        )

    async def get_log_search_count(self, task_id: int, adom: Optional[str] = None) -> dict:
        adom = adom or self._cfg.adom
        return await self.get(
            f"/logview/adom/{adom}/logsearch/count/{task_id}", {"apiver": 3}
        )

    async def delete_log_search(self, task_id: int, adom: Optional[str] = None) -> dict:
        adom = adom or self._cfg.adom
        return await self.request(
            "delete", f"/logview/adom/{adom}/logsearch/{task_id}", params={"apiver": 3}
        )

    # ── Reports ──────────────────────────────────────────────────────────────

    async def get_reports(
        self,
        state: str,
        adom: Optional[str] = None,
        time_from: Optional[str | int] = None,
        time_to: Optional[str | int] = None,
        timezone_name: Optional[str] = None,
        title: Optional[str] = None,
    ) -> dict:
        adom = adom or self._cfg.adom
        params: dict[str, Any] = {"apiver": 3, "state": state}
        if time_from is not None and time_to is not None:
            params["time-range"] = self._time_range(time_from, time_to)
        if timezone_name:
            params["timezone"] = timezone_name
        if title:
            params["title"] = title
        return await self.get(f"/report/adom/{adom}/reports/state", params)

    async def get_report_templates(
        self, adom: Optional[str] = None, device_type: str = "fgt", language: str = "en"
    ) -> dict:
        adom = adom or self._cfg.adom
        return await self.get(
            f"/report/adom/{adom}/template/list",
            {"apiver": 3, "dev-type": device_type, "language": language},
        )

    async def run_report(
        self,
        schedule: Optional[str] = None,
        schedule_params: Optional[dict] = None,
        adom: Optional[str] = None,
    ) -> dict:
        adom = adom or self._cfg.adom
        if not schedule and not schedule_params:
            raise ValueError("run_report requires schedule or schedule_params")
        params: dict[str, Any] = {"apiver": 3}
        if schedule:
            params["schedule"] = schedule
        if schedule_params:
            params["schedule-param"] = schedule_params
        return await self.request(
            "add",
            f"/report/adom/{adom}/run",
            params=params,
        )

    async def get_report_status(self, tid: int, adom: Optional[str] = None) -> dict:
        adom = adom or self._cfg.adom
        return await self.get(f"/report/adom/{adom}/run/{tid}", {"apiver": 3})

    async def download_report(
        self,
        tid: int,
        adom: Optional[str] = None,
        report_format: str = "PDF",
        data_type: Optional[str] = None,
    ) -> dict:
        adom = adom or self._cfg.adom
        params: dict[str, Any] = {"apiver": 3, "format": report_format}
        if data_type:
            params["data-type"] = data_type
        return await self.get(f"/report/adom/{adom}/reports/data/{tid}", params)

    # ── Incidents & Events ───────────────────────────────────────────────────

    async def get_incidents(
        self,
        adom: Optional[str] = None,
        filter: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
        detail_level: Optional[str] = None,
    ) -> dict:
        adom = adom or self._cfg.adom
        params: dict[str, Any] = {"apiver": 3, "limit": limit, "offset": offset}
        if filter:
            params["filter"] = filter
        if detail_level:
            params["detail-level"] = detail_level
        return await self.get(f"/incidentmgmt/adom/{adom}/incidents", params)

    async def get_event_handlers(
        self, alert_ids: list[str], adom: Optional[str] = None, rule_id: Optional[str] = None
    ) -> dict:
        adom = adom or self._cfg.adom
        params: dict[str, Any] = {"apiver": 3, "alertid": alert_ids}
        if rule_id:
            params["ruleid"] = rule_id
        return await self.get(f"/eventmgmt/adom/{adom}/alertfilter", params)

    async def get_events(
        self,
        adom: Optional[str] = None,
        filter: Optional[str] = None,
        limit: int = 1000,
        offset: int = 0,
        time_from: Optional[str | int] = None,
        time_to: Optional[str | int] = None,
        timezone_name: Optional[str] = None,
    ) -> dict:
        adom = adom or self._cfg.adom
        params: dict[str, Any] = {"apiver": 3, "limit": limit, "offset": offset}
        if filter:
            params["filter"] = filter
        if time_from is not None and time_to is not None:
            params["time-range"] = self._time_range(time_from, time_to)
        if timezone_name:
            params["timezone"] = timezone_name
        return await self.get(f"/eventmgmt/adom/{adom}/alerts", params)

    # ── FortiView / Statistics ───────────────────────────────────────────────

    async def get_traffic_summary(
        self,
        adom: Optional[str] = None,
        device: str | list[dict] = "All_FortiGate",
    ) -> dict:
        adom = adom or self._cfg.adom
        return await self.get(
            f"/logview/adom/{adom}/logstats",
            {"apiver": 3, "device": self._devices(device)},
        )

    async def start_fortiview(
        self,
        view_name: str,
        time_from: str | int,
        time_to: str | int,
        adom: Optional[str] = None,
        device: Optional[str | list[dict]] = None,
        filter: Optional[str] = None,
        limit: int = 1000,
        offset: int = 0,
        timezone_name: Optional[str] = None,
    ) -> dict:
        adom = adom or self._cfg.adom
        params: dict[str, Any] = {
            "apiver": 3,
            "time-range": self._time_range(time_from, time_to),
            "limit": limit,
            "offset": offset,
        }
        if device:
            params["device"] = self._devices(device)
        if filter:
            params["filter"] = filter
        if timezone_name:
            params["timezone"] = timezone_name
        return await self.request(
            "add", f"/fortiview/adom/{adom}/{view_name}/run", params=params
        )

    async def get_fortiview_results(
        self, view_name: str, task_id: int, adom: Optional[str] = None
    ) -> dict:
        adom = adom or self._cfg.adom
        return await self.get(
            f"/fortiview/adom/{adom}/{view_name}/run/{task_id}", {"apiver": 3}
        )

    async def delete_fortiview(self, view_name: str, task_id: int, adom: Optional[str] = None) -> dict:
        adom = adom or self._cfg.adom
        return await self.request(
            "delete",
            f"/fortiview/adom/{adom}/{view_name}/run/{task_id}",
            params={"apiver": 3},
        )

    async def get_top_sources(
        self,
        time_from: str | int,
        time_to: str | int,
        adom: Optional[str] = None,
        limit: int = 20,
    ) -> dict:
        return await self.start_fortiview("top-sources", time_from, time_to, adom, limit=limit)

    async def get_top_threats(
        self,
        time_from: str | int,
        time_to: str | int,
        adom: Optional[str] = None,
        limit: int = 20,
    ) -> dict:
        return await self.start_fortiview("top-threats", time_from, time_to, adom, limit=limit)

    async def get_top_applications(
        self,
        time_from: str | int,
        time_to: str | int,
        adom: Optional[str] = None,
        limit: int = 20,
    ) -> dict:
        return await self.start_fortiview(
            "top-applications", time_from, time_to, adom, limit=limit
        )

    async def close(self):
        if self._client:
            await self._client.aclose()
            self._client = None
