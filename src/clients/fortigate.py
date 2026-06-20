from __future__ import annotations

from typing import Any, Optional
import httpx

from clients.base import build_client
from config import FortiGateConfig


class FortiGateClient:
    """FortiGate REST API client (API v2)."""

    SUPPORTED_METHODS = frozenset({"get", "post", "put", "delete"})
    SUPPORTED_DOMAINS = frozenset({"cmdb", "monitor", "log", "service"})
    SESSION_ERROR_STATUSES = frozenset({401, 403})
    SESSION_ENDPOINTS = frozenset({"/logincheck", "/logout"})

    def __init__(self, cfg: FortiGateConfig):
        self._cfg = cfg
        self._client: Optional[httpx.AsyncClient] = None
        self._session_key: Optional[str] = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = build_client(self._cfg.host, self._cfg.port, self._cfg.verify_ssl)
        return self._client

    def _auth_params(self) -> dict:
        if self._cfg.api_key:
            return {"access_token": self._cfg.api_key}
        if self._session_key:
            return {}
        return {}

    def _auth_headers(self) -> dict:
        if self._session_key:
            return {"Cookie": f"APSCOOKIE_{self._cfg.port}={self._session_key}"}
        return {}

    def _merge_params(self, params: Optional[dict] = None, include_vdom: bool = False) -> dict:
        merged = dict(params or {})
        if include_vdom and "vdom" not in merged and self._cfg.vdom:
            merged["vdom"] = self._cfg.vdom
        merged.update(self._auth_params())
        return merged

    @classmethod
    def _validate_request(cls, method: str, path: str) -> str:
        normalized_method = method.lower().strip()
        if normalized_method not in cls.SUPPORTED_METHODS:
            supported = ", ".join(sorted(cls.SUPPORTED_METHODS))
            raise ValueError(f"Unsupported FortiGate REST method '{method}'. Use: {supported}")
        if not path.startswith("/") or path.startswith("//"):
            raise ValueError("FortiGate API path must be an absolute path starting with '/'")
        if path in cls.SESSION_ENDPOINTS:
            raise ValueError("Session endpoints are managed by the FortiGate client")
        if not path.startswith("/api/v2/"):
            raise ValueError("FortiGate API path must start with '/api/v2/'")
        return normalized_method

    @staticmethod
    def _decode_response(resp: httpx.Response) -> Any:
        content_type = resp.headers.get("content-type", "").lower()
        if "json" in content_type:
            return resp.json()
        return resp.text

    @classmethod
    def _normalize_domain_path(cls, domain: str, path: str) -> str:
        normalized_domain = domain.lower().strip().strip("/")
        if normalized_domain not in cls.SUPPORTED_DOMAINS:
            supported = ", ".join(sorted(cls.SUPPORTED_DOMAINS))
            raise ValueError(f"Unsupported FortiGate API domain '{domain}'. Use: {supported}")

        normalized_path = path.strip()
        if not normalized_path:
            raise ValueError("FortiGate domain path must not be empty")
        if normalized_path.startswith("//"):
            raise ValueError("FortiGate domain path must not start with '//'")
        if normalized_path.startswith("/api/v2/"):
            expected_prefix = f"/api/v2/{normalized_domain}/"
            if not normalized_path.startswith(expected_prefix):
                raise ValueError(
                    f"FortiGate {normalized_domain} domain paths must start with '{expected_prefix}'"
                )
            return normalized_path

        relative_path = normalized_path.lstrip("/")
        if not relative_path:
            raise ValueError("FortiGate domain path must not be empty")
        return f"/api/v2/{normalized_domain}/{relative_path}"

    async def login(self):
        if self._cfg.api_key:
            return
        client = await self._get_client()
        resp = await client.post(
            "/logincheck",
            data={"username": self._cfg.username, "secretkey": self._cfg.password},
        )
        resp.raise_for_status()
        for cookie in resp.cookies:
            self._session_key = resp.cookies.get(cookie)
            break

    async def logout(self):
        if not self._session_key:
            return
        client = await self._get_client()
        await client.post("/logout", headers=self._auth_headers())
        self._session_key = None

    async def request(
        self,
        method: str,
        path: str,
        data: Any = None,
        params: Optional[dict] = None,
        include_vdom: bool = True,
        retry_session: bool = True,
    ) -> Any:
        """Call any FortiGate REST API v2 endpoint."""
        normalized_method = self._validate_request(method, path)
        if not self._cfg.api_key and not self._session_key:
            await self.login()

        client = await self._get_client()
        merged_params = self._merge_params(params, include_vdom=include_vdom)
        request_kwargs: dict[str, Any] = {
            "params": merged_params,
            "headers": self._auth_headers(),
        }
        if data is not None and normalized_method in {"post", "put"}:
            request_kwargs["json"] = data

        resp = await client.request(normalized_method.upper(), path, **request_kwargs)
        try:
            resp.raise_for_status()
        except httpx.HTTPStatusError:
            if (
                retry_session
                and not self._cfg.api_key
                and self._session_key
                and resp.status_code in self.SESSION_ERROR_STATUSES
            ):
                self._session_key = None
                await self.login()
                return await self.request(
                    normalized_method,
                    path,
                    data=data,
                    params=params,
                    include_vdom=include_vdom,
                    retry_session=False,
                )
            raise
        return self._decode_response(resp)

    async def domain_request(
        self,
        domain: str,
        method: str,
        path: str,
        data: Any = None,
        params: Optional[dict] = None,
        include_vdom: bool = True,
    ) -> Any:
        """Call a FortiGate REST API endpoint within a specific v2 domain."""
        return await self.request(
            method,
            self._normalize_domain_path(domain, path),
            data=data,
            params=params,
            include_vdom=include_vdom,
        )

    async def get(self, path: str, params: Optional[dict] = None, include_vdom: bool = True) -> Any:
        return await self.request("get", path, params=params, include_vdom=include_vdom)

    async def post(
        self,
        path: str,
        payload: Any,
        params: Optional[dict] = None,
        include_vdom: bool = True,
    ) -> Any:
        return await self.request("post", path, data=payload, params=params, include_vdom=include_vdom)

    async def put(
        self,
        path: str,
        payload: Any,
        params: Optional[dict] = None,
        include_vdom: bool = True,
    ) -> Any:
        return await self.request("put", path, data=payload, params=params, include_vdom=include_vdom)

    async def delete(
        self, path: str, params: Optional[dict] = None, include_vdom: bool = True
    ) -> Any:
        return await self.request("delete", path, params=params, include_vdom=include_vdom)

    def _vdom_params(self, vdom: Optional[str] = None) -> dict:
        return {"vdom": vdom or self._cfg.vdom}

    # ── System ─────────────────────────────────────────────────────────────

    async def get_system_status(self) -> dict:
        return await self.get("/api/v2/monitor/system/status", include_vdom=False)

    async def get_system_resources(self) -> dict:
        return await self.get("/api/v2/monitor/system/resource/usage", include_vdom=False)

    async def get_interfaces(self) -> dict:
        return await self.get("/api/v2/cmdb/system/interface", self._vdom_params())

    async def backup_config(self) -> str:
        client = await self._get_client()
        p = {**self._vdom_params(), **self._auth_params(), "scope": "global"}
        resp = await client.get(
            "/api/v2/monitor/system/config/backup",
            params=p,
            headers=self._auth_headers(),
        )
        resp.raise_for_status()
        return resp.text

    async def execute_cli(self, commands: list[str]) -> dict:
        payload = {"commands": commands}
        return await self.post(
            "/api/v2/monitor/system/cli", payload, self._vdom_params(), include_vdom=False
        )

    # ── Firewall Policies ───────────────────────────────────────────────────

    async def get_firewall_policies(self, policy_id: Optional[int] = None) -> dict:
        path = "/api/v2/cmdb/firewall/policy"
        if policy_id is not None:
            path += f"/{policy_id}"
        return await self.get(path, self._vdom_params())

    async def create_firewall_policy(self, policy: dict) -> dict:
        return await self.post("/api/v2/cmdb/firewall/policy", policy, self._vdom_params())

    async def update_firewall_policy(self, policy_id: int, policy: dict) -> dict:
        return await self.put(
            f"/api/v2/cmdb/firewall/policy/{policy_id}", policy, self._vdom_params()
        )

    async def delete_firewall_policy(self, policy_id: int) -> dict:
        return await self.delete(
            f"/api/v2/cmdb/firewall/policy/{policy_id}", self._vdom_params()
        )

    async def move_firewall_policy(self, policy_id: int, action: str, neighbor: int) -> dict:
        return await self.put(
            f"/api/v2/cmdb/firewall/policy/{policy_id}",
            {},
            {**self._vdom_params(), "action": action, "before": neighbor},
        )

    # ── Address Objects ─────────────────────────────────────────────────────

    async def get_address_objects(self, name: Optional[str] = None) -> dict:
        path = "/api/v2/cmdb/firewall/address"
        if name:
            path += f"/{name}"
        return await self.get(path, self._vdom_params())

    async def create_address_object(self, obj: dict) -> dict:
        return await self.post("/api/v2/cmdb/firewall/address", obj, self._vdom_params())

    async def update_address_object(self, name: str, obj: dict) -> dict:
        return await self.put(
            f"/api/v2/cmdb/firewall/address/{name}", obj, self._vdom_params()
        )

    async def delete_address_object(self, name: str) -> dict:
        return await self.delete(
            f"/api/v2/cmdb/firewall/address/{name}", self._vdom_params()
        )

    async def get_address_groups(self, name: Optional[str] = None) -> dict:
        path = "/api/v2/cmdb/firewall/addrgrp"
        if name:
            path += f"/{name}"
        return await self.get(path, self._vdom_params())

    async def create_address_group(self, obj: dict) -> dict:
        return await self.post("/api/v2/cmdb/firewall/addrgrp", obj, self._vdom_params())

    async def update_address_group(self, name: str, obj: dict) -> dict:
        return await self.put(f"/api/v2/cmdb/firewall/addrgrp/{name}", obj, self._vdom_params())

    async def delete_address_group(self, name: str) -> dict:
        return await self.delete(f"/api/v2/cmdb/firewall/addrgrp/{name}", self._vdom_params())

    # ── Service Objects ─────────────────────────────────────────────────────

    async def get_service_objects(self, name: Optional[str] = None) -> dict:
        path = "/api/v2/cmdb/firewall.service/custom"
        if name:
            path += f"/{name}"
        return await self.get(path, self._vdom_params())

    async def create_service_object(self, obj: dict) -> dict:
        return await self.post(
            "/api/v2/cmdb/firewall.service/custom", obj, self._vdom_params()
        )

    async def update_service_object(self, name: str, obj: dict) -> dict:
        return await self.put(
            f"/api/v2/cmdb/firewall.service/custom/{name}", obj, self._vdom_params()
        )

    async def delete_service_object(self, name: str) -> dict:
        return await self.delete(
            f"/api/v2/cmdb/firewall.service/custom/{name}", self._vdom_params()
        )

    async def get_service_groups(self, name: Optional[str] = None) -> dict:
        path = "/api/v2/cmdb/firewall.service/group"
        if name:
            path += f"/{name}"
        return await self.get(path, self._vdom_params())

    async def create_service_group(self, obj: dict) -> dict:
        return await self.post("/api/v2/cmdb/firewall.service/group", obj, self._vdom_params())

    async def update_service_group(self, name: str, obj: dict) -> dict:
        return await self.put(
            f"/api/v2/cmdb/firewall.service/group/{name}", obj, self._vdom_params()
        )

    async def delete_service_group(self, name: str) -> dict:
        return await self.delete(
            f"/api/v2/cmdb/firewall.service/group/{name}", self._vdom_params()
        )

    # ── Routing ─────────────────────────────────────────────────────────────

    async def get_static_routes(self) -> dict:
        return await self.get("/api/v2/cmdb/router/static", self._vdom_params())

    async def create_static_route(self, route: dict) -> dict:
        return await self.post("/api/v2/cmdb/router/static", route, self._vdom_params())

    async def update_static_route(self, seq_num: int, route: dict) -> dict:
        return await self.put(f"/api/v2/cmdb/router/static/{seq_num}", route, self._vdom_params())

    async def delete_static_route(self, seq_num: int) -> dict:
        return await self.delete(
            f"/api/v2/cmdb/router/static/{seq_num}", self._vdom_params()
        )

    async def get_routing_table(self) -> dict:
        return await self.get("/api/v2/monitor/router/ipv4", self._vdom_params())

    async def get_bgp_neighbors(self) -> dict:
        return await self.get("/api/v2/monitor/router/bgp/neighbors", self._vdom_params())

    # ── VPN ─────────────────────────────────────────────────────────────────

    async def get_ipsec_tunnels(self) -> dict:
        return await self.get("/api/v2/monitor/vpn/ipsec", self._vdom_params())

    async def get_ipsec_phase1(self, name: Optional[str] = None) -> dict:
        path = "/api/v2/cmdb/vpn.ipsec/phase1-interface"
        if name:
            path += f"/{name}"
        return await self.get(path, self._vdom_params())

    async def create_ipsec_phase1(self, config: dict) -> dict:
        return await self.post(
            "/api/v2/cmdb/vpn.ipsec/phase1-interface", config, self._vdom_params()
        )

    async def update_ipsec_phase1(self, name: str, config: dict) -> dict:
        return await self.put(
            f"/api/v2/cmdb/vpn.ipsec/phase1-interface/{name}",
            config,
            self._vdom_params(),
        )

    async def delete_ipsec_phase1(self, name: str) -> dict:
        return await self.delete(
            f"/api/v2/cmdb/vpn.ipsec/phase1-interface/{name}", self._vdom_params()
        )

    async def get_ssl_vpn_settings(self) -> dict:
        return await self.get("/api/v2/cmdb/vpn.ssl/settings", self._vdom_params())

    async def get_ssl_vpn_sessions(self) -> dict:
        return await self.get("/api/v2/monitor/vpn/ssl", self._vdom_params())

    # ── Sessions & Monitoring ───────────────────────────────────────────────

    async def get_active_sessions(self, count: int = 100) -> dict:
        return await self.get(
            "/api/v2/monitor/firewall/session",
            {**self._vdom_params(), "count": count},
        )

    async def get_session_stats(self) -> dict:
        return await self.get(
            "/api/v2/monitor/system/session/full-stat", self._vdom_params()
        )

    async def get_fortiview_top_sources(self) -> dict:
        return await self.get(
            "/api/v2/monitor/fortiview/statistics",
            {**self._vdom_params(), "filter": "top-sources"},
        )

    async def get_threat_feeds(self) -> dict:
        return await self.get("/api/v2/cmdb/system/threat-feed", self._vdom_params())

    # ── Logs ────────────────────────────────────────────────────────────────

    async def get_logs(
        self, log_type: str = "traffic", subtype: str = "forward", rows: int = 50
    ) -> dict:
        return await self.get(
            f"/api/v2/log/disk/{log_type}",
            {**self._vdom_params(), "subtype": subtype, "rows": rows},
        )

    async def get_ha_status(self) -> dict:
        return await self.get("/api/v2/monitor/system/ha-statistics", include_vdom=False)

    async def close(self):
        if self._client:
            await self._client.aclose()
            self._client = None
