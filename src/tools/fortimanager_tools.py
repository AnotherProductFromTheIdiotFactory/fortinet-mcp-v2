from __future__ import annotations

import json
from typing import Optional

from mcp.server.fastmcp import FastMCP

from clients.fortimanager import FortiManagerClient
from config import Config


def _client_cache(config: Config) -> dict[str, FortiManagerClient]:
    return {d.id: FortiManagerClient(d) for d in config.fortimanagers}


def register_fortimanager_tools(mcp: FastMCP, config: Config):
    clients: dict[str, FortiManagerClient] = _client_cache(config)

    def get_client(device_id: str) -> FortiManagerClient:
        config.get_fmg(device_id)
        if device_id not in clients:
            clients[device_id] = FortiManagerClient(config.get_fmg(device_id))
        return clients[device_id]

    # ── Discovery ───────────────────────────────────────────────────────────

    @mcp.tool()
    async def fmg_list_devices() -> str:
        """List all configured FortiManager instances."""
        devices = [
            {"id": d.id, "name": d.name, "host": d.host, "port": d.port, "adom": d.adom}
            for d in config.fortimanagers
        ]
        return json.dumps(devices, indent=2)

    # ── System ──────────────────────────────────────────────────────────────

    @mcp.tool()
    async def fmg_get_system_status(device_id: str) -> str:
        """Get FortiManager system status (version, serial, uptime).

        Args:
            device_id: ID of the FortiManager instance from config.
        """
        c = get_client(device_id)
        await c.login()
        result = await c.get_system_status()
        return json.dumps(result, indent=2)

    @mcp.tool()
    async def fmg_get_adoms(device_id: str) -> str:
        """List all ADOMs on a FortiManager.

        Args:
            device_id: ID of the FortiManager instance from config.
        """
        c = get_client(device_id)
        await c.login()
        result = await c.get_adoms()
        return json.dumps(result, indent=2)

    # ── Device Management ───────────────────────────────────────────────────

    @mcp.tool()
    async def fmg_get_managed_devices(device_id: str, adom: Optional[str] = None) -> str:
        """List all managed devices under an ADOM on FortiManager.

        Args:
            device_id: ID of the FortiManager instance from config.
            adom: ADOM name (uses default from config if not specified).
        """
        c = get_client(device_id)
        await c.login()
        result = await c.get_devices(adom)
        return json.dumps(result, indent=2)

    @mcp.tool()
    async def fmg_get_device_detail(
        device_id: str, managed_device_name: str, adom: Optional[str] = None
    ) -> str:
        """Get details for a specific managed device on FortiManager.

        Args:
            device_id: ID of the FortiManager instance from config.
            managed_device_name: Name of the managed FortiGate.
            adom: ADOM name (uses default from config if not specified).
        """
        c = get_client(device_id)
        await c.login()
        result = await c.get_device(managed_device_name, adom)
        return json.dumps(result, indent=2)

    @mcp.tool()
    async def fmg_add_device(device_id: str, device_data: dict, adom: Optional[str] = None) -> str:
        """Add a new FortiGate device to FortiManager.

        Args:
            device_id: ID of the FortiManager instance from config.
            device_data: Device registration data. Example:
                         {"name": "fgt-01", "ip": "192.168.1.1", "adm_usr": "admin",
                          "adm_pass": "password", "mgmt_mode": "fmg"}
            adom: ADOM name (uses default from config if not specified).
        """
        c = get_client(device_id)
        await c.login()
        result = await c.add_device(device_data, adom)
        return json.dumps(result, indent=2)

    @mcp.tool()
    async def fmg_delete_device(
        device_id: str, managed_device_name: str, adom: Optional[str] = None
    ) -> str:
        """Remove a managed device from FortiManager.

        Args:
            device_id: ID of the FortiManager instance from config.
            managed_device_name: Name of the managed FortiGate to remove.
            adom: ADOM name (uses default from config if not specified).
        """
        c = get_client(device_id)
        await c.login()
        result = await c.delete_device(managed_device_name, adom)
        return json.dumps(result, indent=2)

    @mcp.tool()
    async def fmg_get_unregistered_devices(device_id: str) -> str:
        """List devices that have connected but are not yet registered in FortiManager.

        Args:
            device_id: ID of the FortiManager instance from config.
        """
        c = get_client(device_id)
        await c.login()
        result = await c.get_unregistered_devices()
        return json.dumps(result, indent=2)

    @mcp.tool()
    async def fmg_set_device_metadata(
        device_id: str,
        managed_device_name: str,
        meta: dict,
        adom: Optional[str] = None,
    ) -> str:
        """Set metadata variables on a managed device (used for provisioning templates).

        Args:
            device_id: ID of the FortiManager instance from config.
            managed_device_name: Name of the managed FortiGate.
            meta: Dict of metadata key/value pairs.
                  Example: {"hostname": "fgt-branch-01", "wan_ip": "203.0.113.1"}
            adom: ADOM name (uses default from config if not specified).
        """
        c = get_client(device_id)
        await c.login()
        result = await c.set_device_metadata(managed_device_name, meta, adom)
        return json.dumps(result, indent=2)

    # ── Policy Packages ─────────────────────────────────────────────────────

    @mcp.tool()
    async def fmg_get_policy_packages(device_id: str, adom: Optional[str] = None) -> str:
        """List all policy packages in an ADOM on FortiManager.

        Args:
            device_id: ID of the FortiManager instance from config.
            adom: ADOM name (uses default from config if not specified).
        """
        c = get_client(device_id)
        await c.login()
        result = await c.get_policy_packages(adom)
        return json.dumps(result, indent=2)

    @mcp.tool()
    async def fmg_create_policy_package(
        device_id: str, pkg: dict, adom: Optional[str] = None
    ) -> str:
        """Create a policy package on FortiManager.

        Args:
            device_id: ID of the FortiManager instance from config.
            pkg: Package definition. Example:
                 {"name": "pkg-branch", "type": "pkg", "ngfw-mode": "profile-based"}
            adom: ADOM name (uses default from config if not specified).
        """
        c = get_client(device_id)
        await c.login()
        result = await c.create_policy_package(pkg, adom)
        return json.dumps(result, indent=2)

    @mcp.tool()
    async def fmg_install_policy_package(
        device_id: str,
        pkg_name: str,
        targets: list[dict],
        adom: Optional[str] = None,
    ) -> str:
        """Install a policy package to target FortiGate devices.

        Args:
            device_id: ID of the FortiManager instance from config.
            pkg_name: Name of the policy package to install.
            targets: List of target scope dicts. Example:
                     [{"name": "fgt-01", "vdom": "root"}]
            adom: ADOM name (uses default from config if not specified).
        """
        c = get_client(device_id)
        await c.login()
        result = await c.install_policy_package(pkg_name, targets, adom)
        return json.dumps(result, indent=2)

    @mcp.tool()
    async def fmg_install_device_config(
        device_id: str,
        managed_device_name: str,
        vdom: str = "root",
        adom: Optional[str] = None,
    ) -> str:
        """Push device-level configuration to a managed FortiGate.

        Args:
            device_id: ID of the FortiManager instance from config.
            managed_device_name: Name of the target FortiGate.
            vdom: VDOM name (default: root).
            adom: ADOM name (uses default from config if not specified).
        """
        c = get_client(device_id)
        await c.login()
        result = await c.install_device_config(managed_device_name, vdom, adom)
        return json.dumps(result, indent=2)

    # ── Firewall Policies ───────────────────────────────────────────────────

    @mcp.tool()
    async def fmg_get_firewall_policies(
        device_id: str, pkg_name: str, adom: Optional[str] = None
    ) -> str:
        """List firewall policies in a policy package on FortiManager.

        Args:
            device_id: ID of the FortiManager instance from config.
            pkg_name: Name of the policy package.
            adom: ADOM name (uses default from config if not specified).
        """
        c = get_client(device_id)
        await c.login()
        result = await c.get_firewall_policies(pkg_name, adom)
        return json.dumps(result, indent=2)

    @mcp.tool()
    async def fmg_create_firewall_policy(
        device_id: str, pkg_name: str, policy: dict, adom: Optional[str] = None
    ) -> str:
        """Create a firewall policy in a FortiManager policy package.

        Args:
            device_id: ID of the FortiManager instance from config.
            pkg_name: Name of the policy package.
            policy: Policy definition dict. Example:
                    {"name": "allow-web", "srcintf": [{"name": "any"}],
                     "dstintf": [{"name": "any"}], "srcaddr": [{"name": "all"}],
                     "dstaddr": [{"name": "all"}], "action": "accept",
                     "schedule": "always", "service": [{"name": "HTTP"}]}
            adom: ADOM name (uses default from config if not specified).
        """
        c = get_client(device_id)
        await c.login()
        result = await c.create_firewall_policy(pkg_name, policy, adom)
        return json.dumps(result, indent=2)

    @mcp.tool()
    async def fmg_update_firewall_policy(
        device_id: str,
        pkg_name: str,
        policy_id: int,
        policy: dict,
        adom: Optional[str] = None,
    ) -> str:
        """Update a firewall policy in a FortiManager policy package.

        Args:
            device_id: ID of the FortiManager instance from config.
            pkg_name: Name of the policy package.
            policy_id: Policy ID to update.
            policy: Dict of fields to update.
            adom: ADOM name (uses default from config if not specified).
        """
        c = get_client(device_id)
        await c.login()
        result = await c.update_firewall_policy(pkg_name, policy_id, policy, adom)
        return json.dumps(result, indent=2)

    @mcp.tool()
    async def fmg_delete_firewall_policy(
        device_id: str, pkg_name: str, policy_id: int, adom: Optional[str] = None
    ) -> str:
        """Delete a firewall policy from a FortiManager policy package.

        Args:
            device_id: ID of the FortiManager instance from config.
            pkg_name: Name of the policy package.
            policy_id: Policy ID to delete.
            adom: ADOM name (uses default from config if not specified).
        """
        c = get_client(device_id)
        await c.login()
        result = await c.delete_firewall_policy(pkg_name, policy_id, adom)
        return json.dumps(result, indent=2)

    # ── Address Objects ─────────────────────────────────────────────────────

    @mcp.tool()
    async def fmg_get_address_objects(device_id: str, adom: Optional[str] = None) -> str:
        """List address objects in a FortiManager ADOM.

        Args:
            device_id: ID of the FortiManager instance from config.
            adom: ADOM name (uses default from config if not specified).
        """
        c = get_client(device_id)
        await c.login()
        result = await c.get_address_objects(adom)
        return json.dumps(result, indent=2)

    @mcp.tool()
    async def fmg_create_address_object(
        device_id: str, obj: dict, adom: Optional[str] = None
    ) -> str:
        """Create an address object in a FortiManager ADOM.

        Args:
            device_id: ID of the FortiManager instance from config.
            obj: Address object dict. Example:
                 {"name": "dc-servers", "type": "ipmask", "subnet": ["10.0.1.0", "255.255.255.0"]}
            adom: ADOM name (uses default from config if not specified).
        """
        c = get_client(device_id)
        await c.login()
        result = await c.create_address_object(obj, adom)
        return json.dumps(result, indent=2)

    @mcp.tool()
    async def fmg_update_address_object(
        device_id: str, name: str, obj: dict, adom: Optional[str] = None
    ) -> str:
        """Update an address object in a FortiManager ADOM.

        Args:
            device_id: ID of the FortiManager instance from config.
            name: Name of the address object to update.
            obj: Dict of fields to update.
            adom: ADOM name (uses default from config if not specified).
        """
        c = get_client(device_id)
        await c.login()
        result = await c.update_address_object(name, obj, adom)
        return json.dumps(result, indent=2)

    @mcp.tool()
    async def fmg_delete_address_object(
        device_id: str, name: str, adom: Optional[str] = None
    ) -> str:
        """Delete an address object from a FortiManager ADOM.

        Args:
            device_id: ID of the FortiManager instance from config.
            name: Name of the address object to delete.
            adom: ADOM name (uses default from config if not specified).
        """
        c = get_client(device_id)
        await c.login()
        result = await c.delete_address_object(name, adom)
        return json.dumps(result, indent=2)

    @mcp.tool()
    async def fmg_get_address_groups(device_id: str, adom: Optional[str] = None) -> str:
        """List address groups in a FortiManager ADOM.

        Args:
            device_id: ID of the FortiManager instance from config.
            adom: ADOM name (uses default from config if not specified).
        """
        c = get_client(device_id)
        await c.login()
        result = await c.get_address_groups(adom)
        return json.dumps(result, indent=2)

    @mcp.tool()
    async def fmg_create_address_group(
        device_id: str, obj: dict, adom: Optional[str] = None
    ) -> str:
        """Create an address group in a FortiManager ADOM.

        Args:
            device_id: ID of the FortiManager instance from config.
            obj: Group dict. Example:
                 {"name": "all-servers", "member": [{"name": "dc-servers"}, {"name": "web-servers"}]}
            adom: ADOM name (uses default from config if not specified).
        """
        c = get_client(device_id)
        await c.login()
        result = await c.create_address_group(obj, adom)
        return json.dumps(result, indent=2)

    # ── Service Objects ─────────────────────────────────────────────────────

    @mcp.tool()
    async def fmg_get_service_objects(device_id: str, adom: Optional[str] = None) -> str:
        """List service objects in a FortiManager ADOM.

        Args:
            device_id: ID of the FortiManager instance from config.
            adom: ADOM name (uses default from config if not specified).
        """
        c = get_client(device_id)
        await c.login()
        result = await c.get_service_objects(adom)
        return json.dumps(result, indent=2)

    @mcp.tool()
    async def fmg_create_service_object(
        device_id: str, obj: dict, adom: Optional[str] = None
    ) -> str:
        """Create a service object in a FortiManager ADOM.

        Args:
            device_id: ID of the FortiManager instance from config.
            obj: Service object dict.
            adom: ADOM name (uses default from config if not specified).
        """
        c = get_client(device_id)
        await c.login()
        result = await c.create_service_object(obj, adom)
        return json.dumps(result, indent=2)

    # ── Scripts ──────────────────────────────────────────────────────────────

    @mcp.tool()
    async def fmg_get_scripts(device_id: str, adom: Optional[str] = None) -> str:
        """List scripts available in a FortiManager ADOM.

        Args:
            device_id: ID of the FortiManager instance from config.
            adom: ADOM name (uses default from config if not specified).
        """
        c = get_client(device_id)
        await c.login()
        result = await c.get_scripts(adom)
        return json.dumps(result, indent=2)

    @mcp.tool()
    async def fmg_create_script(
        device_id: str, script: dict, adom: Optional[str] = None
    ) -> str:
        """Create a CLI script in a FortiManager ADOM.

        Args:
            device_id: ID of the FortiManager instance from config.
            script: Script definition. Example:
                    {"name": "disable-ssh", "type": "cli",
                     "content": "config system global\\nset admin-ssh-port 0\\nend"}
            adom: ADOM name (uses default from config if not specified).
        """
        c = get_client(device_id)
        await c.login()
        result = await c.create_script(script, adom)
        return json.dumps(result, indent=2)

    @mcp.tool()
    async def fmg_run_script(
        device_id: str,
        script_name: str,
        targets: list[dict],
        adom: Optional[str] = None,
    ) -> str:
        """Run a script on target managed devices via FortiManager.

        Args:
            device_id: ID of the FortiManager instance from config.
            script_name: Name of the script to execute.
            targets: List of target scope dicts. Example:
                     [{"name": "fgt-01", "vdom": "root"}]
            adom: ADOM name (uses default from config if not specified).
        """
        c = get_client(device_id)
        await c.login()
        result = await c.run_script(script_name, targets, adom)
        return json.dumps(result, indent=2)

    # ── Tasks ────────────────────────────────────────────────────────────────

    @mcp.tool()
    async def fmg_get_task_status(device_id: str, task_id: int) -> str:
        """Get the status of a FortiManager task (install, script run, etc.).

        Args:
            device_id: ID of the FortiManager instance from config.
            task_id: Numeric task ID returned by install or script operations.
        """
        c = get_client(device_id)
        await c.login()
        result = await c.get_task(task_id)
        return json.dumps(result, indent=2)

    @mcp.tool()
    async def fmg_get_tasks(device_id: str) -> str:
        """List recent tasks on a FortiManager.

        Args:
            device_id: ID of the FortiManager instance from config.
        """
        c = get_client(device_id)
        await c.login()
        result = await c.get_tasks()
        return json.dumps(result, indent=2)

    @mcp.tool()
    async def fmg_wait_for_task(
        device_id: str, task_id: int, timeout_seconds: float = 300.0
    ) -> str:
        """Wait for a FortiManager task to complete and return the final status.

        Args:
            device_id: ID of the FortiManager instance from config.
            task_id: Numeric task ID to poll.
            timeout_seconds: Maximum time to wait in seconds (default 300).
        """
        c = get_client(device_id)
        await c.login()
        result = await c.wait_for_task(task_id, timeout=timeout_seconds)
        return json.dumps(result, indent=2)
