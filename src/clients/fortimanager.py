from __future__ import annotations

import asyncio
from typing import Any, Optional
import httpx

from clients.base import build_client
from config import FortiManagerConfig


class FortiManagerClient:
    """FortiManager JSON-RPC API client."""

    def __init__(self, cfg: FortiManagerConfig):
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
            "verbose": 1,
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
            raise RuntimeError(f"FMG RPC error {status.get('code')}: {status.get('message')}")
        return data

    async def login(self):
        data = await self._rpc(
            "exec",
            [{"url": "/sys/login/user", "data": {"user": self._cfg.username, "passwd": self._cfg.password}}],
            require_session=False,
        )
        self._session = data.get("session")
        if not self._session:
            raise RuntimeError("FortiManager login failed: no session returned")

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

    async def set(self, url: str, data: dict) -> dict:
        return await self._rpc("set", [{"url": url, "data": data}])

    async def update(self, url: str, data: dict) -> dict:
        return await self._rpc("update", [{"url": url, "data": data}])

    async def delete(self, url: str, confirm: int = 1) -> dict:
        return await self._rpc("delete", [{"url": url, "confirm": confirm}])

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

    async def get_global_settings(self) -> dict:
        return await self.get("/cli/global/system/global")

    # ── Device Management ───────────────────────────────────────────────────

    async def get_devices(self, adom: Optional[str] = None) -> dict:
        adom = adom or self._cfg.adom
        return await self.get(f"/dvmdb/adom/{adom}/device")

    async def get_device(self, device_name: str, adom: Optional[str] = None) -> dict:
        adom = adom or self._cfg.adom
        return await self.get(f"/dvmdb/adom/{adom}/device/{device_name}")

    async def add_device(self, device_data: dict, adom: Optional[str] = None) -> dict:
        adom = adom or self._cfg.adom
        return await self.exec(
            "/dvm/cmd/add/device",
            {"adom": adom, "device": device_data, "flags": ["create_task", "nonblocking"]},
        )

    async def delete_device(self, device_name: str, adom: Optional[str] = None) -> dict:
        adom = adom or self._cfg.adom
        return await self.exec(
            "/dvm/cmd/del/device",
            {"adom": adom, "device": device_name, "flags": ["create_task", "nonblocking"]},
        )

    async def promote_device(self, device_name: str, adom: Optional[str] = None) -> dict:
        adom = adom or self._cfg.adom
        return await self.exec(
            "/dvm/cmd/promote/dev-list",
            {"adom": adom, "dev-list": [{"name": device_name}]},
        )

    async def get_device_vdoms(self, device_name: str) -> dict:
        return await self.get(f"/dvmdb/device/{device_name}/vdom")

    async def get_unregistered_devices(self) -> dict:
        return await self.get("/dvmdb/device", {"filter": ["mgmt_mode", "==", "unreg"]})

    # ── Policy Packages ─────────────────────────────────────────────────────

    async def get_policy_packages(self, adom: Optional[str] = None) -> dict:
        adom = adom or self._cfg.adom
        return await self.get(f"/pm/pkg/adom/{adom}")

    async def get_policy_package(self, pkg_name: str, adom: Optional[str] = None) -> dict:
        adom = adom or self._cfg.adom
        return await self.get(f"/pm/pkg/adom/{adom}/{pkg_name}")

    async def create_policy_package(self, pkg: dict, adom: Optional[str] = None) -> dict:
        adom = adom or self._cfg.adom
        return await self.add(f"/pm/pkg/adom/{adom}", pkg)

    async def install_policy_package(
        self, pkg_name: str, targets: list[dict], adom: Optional[str] = None
    ) -> dict:
        adom = adom or self._cfg.adom
        return await self.exec(
            "/securityconsole/install/package",
            {
                "adom": adom,
                "pkg": pkg_name,
                "scope": targets,
                "flags": ["generate_rev"],
            },
        )

    async def install_device_config(
        self, device_name: str, vdom: str = "root", adom: Optional[str] = None
    ) -> dict:
        adom = adom or self._cfg.adom
        return await self.exec(
            "/securityconsole/install/devobj",
            {
                "adom": adom,
                "scope": [{"name": device_name, "vdom": vdom}],
                "flags": ["copy_assigned_pkg"],
            },
        )

    # ── Firewall Policies ───────────────────────────────────────────────────

    async def get_firewall_policies(self, pkg_name: str, adom: Optional[str] = None) -> dict:
        adom = adom or self._cfg.adom
        return await self.get(f"/pm/config/adom/{adom}/pkg/{pkg_name}/firewall/policy")

    async def create_firewall_policy(
        self, pkg_name: str, policy: dict, adom: Optional[str] = None
    ) -> dict:
        adom = adom or self._cfg.adom
        return await self.add(
            f"/pm/config/adom/{adom}/pkg/{pkg_name}/firewall/policy", policy
        )

    async def update_firewall_policy(
        self, pkg_name: str, policy_id: int, policy: dict, adom: Optional[str] = None
    ) -> dict:
        adom = adom or self._cfg.adom
        return await self.update(
            f"/pm/config/adom/{adom}/pkg/{pkg_name}/firewall/policy/{policy_id}", policy
        )

    async def delete_firewall_policy(
        self, pkg_name: str, policy_id: int, adom: Optional[str] = None
    ) -> dict:
        adom = adom or self._cfg.adom
        return await self.delete(
            f"/pm/config/adom/{adom}/pkg/{pkg_name}/firewall/policy/{policy_id}"
        )

    async def move_policy(
        self, pkg_name: str, policy_id: int, action: str, target: int, adom: Optional[str] = None
    ) -> dict:
        adom = adom or self._cfg.adom
        return await self.exec(
            "/securityconsole/move/obj",
            {
                "adom": adom,
                "pkg": pkg_name,
                "obj": f"firewall/policy/{policy_id}",
                "action": action,
                "target": str(target),
            },
        )

    # ── Address Objects ─────────────────────────────────────────────────────

    async def get_address_objects(self, adom: Optional[str] = None) -> dict:
        adom = adom or self._cfg.adom
        return await self.get(f"/pm/config/adom/{adom}/obj/firewall/address")

    async def create_address_object(self, obj: dict, adom: Optional[str] = None) -> dict:
        adom = adom or self._cfg.adom
        return await self.add(f"/pm/config/adom/{adom}/obj/firewall/address", obj)

    async def update_address_object(
        self, name: str, obj: dict, adom: Optional[str] = None
    ) -> dict:
        adom = adom or self._cfg.adom
        return await self.update(
            f"/pm/config/adom/{adom}/obj/firewall/address/{name}", obj
        )

    async def delete_address_object(self, name: str, adom: Optional[str] = None) -> dict:
        adom = adom or self._cfg.adom
        return await self.delete(f"/pm/config/adom/{adom}/obj/firewall/address/{name}")

    async def get_address_groups(self, adom: Optional[str] = None) -> dict:
        adom = adom or self._cfg.adom
        return await self.get(f"/pm/config/adom/{adom}/obj/firewall/addrgrp")

    async def create_address_group(self, obj: dict, adom: Optional[str] = None) -> dict:
        adom = adom or self._cfg.adom
        return await self.add(f"/pm/config/adom/{adom}/obj/firewall/addrgrp", obj)

    # ── Service Objects ─────────────────────────────────────────────────────

    async def get_service_objects(self, adom: Optional[str] = None) -> dict:
        adom = adom or self._cfg.adom
        return await self.get(f"/pm/config/adom/{adom}/obj/firewall.service/custom")

    async def create_service_object(self, obj: dict, adom: Optional[str] = None) -> dict:
        adom = adom or self._cfg.adom
        return await self.add(f"/pm/config/adom/{adom}/obj/firewall.service/custom", obj)

    # ── Scripts ──────────────────────────────────────────────────────────────

    async def get_scripts(self, adom: Optional[str] = None) -> dict:
        adom = adom or self._cfg.adom
        return await self.get(f"/dvmdb/adom/{adom}/script")

    async def create_script(self, script: dict, adom: Optional[str] = None) -> dict:
        adom = adom or self._cfg.adom
        return await self.add(f"/dvmdb/adom/{adom}/script", script)

    async def run_script(
        self,
        script_name: str,
        targets: list[dict],
        adom: Optional[str] = None,
    ) -> dict:
        adom = adom or self._cfg.adom
        return await self.exec(
            "/dvmdb/adom/{adom}/script/execute".replace("{adom}", adom),
            {"adom": adom, "script": script_name, "scope": targets},
        )

    # ── Tasks ────────────────────────────────────────────────────────────────

    async def get_task(self, task_id: int) -> dict:
        return await self.get(f"/task/task/{task_id}")

    async def get_tasks(self) -> dict:
        return await self.get("/task/task")

    async def wait_for_task(self, task_id: int, poll_interval: float = 3.0, timeout: float = 300.0) -> dict:
        import asyncio
        elapsed = 0.0
        while elapsed < timeout:
            result = await self.get_task(task_id)
            data = result.get("result", [{}])
            first = data[0] if isinstance(data, list) else data
            task_data = first.get("data", {})
            percent = task_data.get("percent", 0)
            if percent >= 100:
                return result
            await asyncio.sleep(poll_interval)
            elapsed += poll_interval
        raise TimeoutError(f"Task {task_id} did not complete within {timeout}s")

    # ── Zero-Touch Provisioning ──────────────────────────────────────────────

    async def get_provisioning_templates(self, adom: Optional[str] = None) -> dict:
        adom = adom or self._cfg.adom
        return await self.get(f"/pm/config/adom/{adom}/obj/fsp/vlan")

    async def get_metadata_variables(self, adom: Optional[str] = None) -> dict:
        adom = adom or self._cfg.adom
        return await self.get(f"/dvmdb/adom/{adom}/device/scope/meta fields")

    async def set_device_metadata(
        self, device_name: str, meta: dict, adom: Optional[str] = None
    ) -> dict:
        adom = adom or self._cfg.adom
        return await self.update(
            f"/dvmdb/adom/{adom}/device/{device_name}",
            {"meta fields": meta},
        )

    async def close(self):
        if self._client:
            await self._client.aclose()
            self._client = None
