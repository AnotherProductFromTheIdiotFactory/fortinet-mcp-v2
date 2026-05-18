from __future__ import annotations

from typing import Any, Optional
import httpx

from clients.base import build_client
from config import FortiGateConfig


class FortiGateClient:
    """FortiGate REST API client (API v2)."""

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

    async def get(self, path: str, params: Optional[dict] = None) -> dict:
        client = await self._get_client()
        p = {**(params or {}), **self._auth_params()}
        resp = await client.get(path, params=p, headers=self._auth_headers())
        resp.raise_for_status()
        return resp.json()

    async def post(self, path: str, payload: dict, params: Optional[dict] = None) -> dict:
        client = await self._get_client()
        p = {**(params or {}), **self._auth_params()}
        resp = await client.post(path, json=payload, params=p, headers=self._auth_headers())
        resp.raise_for_status()
        return resp.json()

    async def put(self, path: str, payload: dict, params: Optional[dict] = None) -> dict:
        client = await self._get_client()
        p = {**(params or {}), **self._auth_params()}
        resp = await client.put(path, json=payload, params=p, headers=self._auth_headers())
        resp.raise_for_status()
        return resp.json()

    async def delete(self, path: str, params: Optional[dict] = None) -> dict:
        client = await self._get_client()
        p = {**(params or {}), **self._auth_params()}
        resp = await client.delete(path, params=p, headers=self._auth_headers())
        resp.raise_for_status()
        return resp.json()

    def _vdom_params(self, vdom: Optional[str] = None) -> dict:
        return {"vdom": vdom or self._cfg.vdom}

    # ── System ─────────────────────────────────────────────────────────────

    async def get_system_status(self) -> dict:
        return await self.get("/api/v2/monitor/system/status")

    async def get_system_resources(self) -> dict:
        return await self.get("/api/v2/monitor/system/resource/usage")

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
        return await self.post("/api/v2/monitor/system/cli", payload, self._vdom_params())

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

    async def get_service_groups(self, name: Optional[str] = None) -> dict:
        path = "/api/v2/cmdb/firewall.service/group"
        if name:
            path += f"/{name}"
        return await self.get(path, self._vdom_params())

    # ── Routing ─────────────────────────────────────────────────────────────

    async def get_static_routes(self) -> dict:
        return await self.get("/api/v2/cmdb/router/static", self._vdom_params())

    async def create_static_route(self, route: dict) -> dict:
        return await self.post("/api/v2/cmdb/router/static", route, self._vdom_params())

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
        return await self.get("/api/v2/monitor/system/ha-statistics")

    async def close(self):
        if self._client:
            await self._client.aclose()
            self._client = None
