from __future__ import annotations

import json
from typing import Optional, Any

from mcp.server.fastmcp import FastMCP

from clients.fortigate import FortiGateClient
from config import Config


def _client_cache(config: Config) -> dict[str, FortiGateClient]:
    return {d.id: FortiGateClient(d) for d in config.fortigates}


def register_fortigate_tools(mcp: FastMCP, config: Config):
    clients: dict[str, FortiGateClient] = _client_cache(config)

    def get_client(device_id: str) -> FortiGateClient:
        config.get_fgt(device_id)  # validates existence
        if device_id not in clients:
            clients[device_id] = FortiGateClient(config.get_fgt(device_id))
        return clients[device_id]

    def dump(result: Any) -> str:
        if isinstance(result, str):
            return result
        return json.dumps(result, indent=2)

    async def domain_request(
        device_id: str,
        domain: str,
        method: str,
        path: str,
        data: Optional[Any] = None,
        params: Optional[dict] = None,
    ) -> str:
        c = get_client(device_id)
        result = await c.domain_request(domain, method, path, data=data, params=params)
        return dump(result)

    async def domain_batch(device_id: str, domain: str, requests: list[dict]) -> str:
        if not requests:
            raise ValueError("requests must contain at least one operation")
        if len(requests) > 50:
            raise ValueError(f"fgt_{domain}_batch accepts at most 50 operations")

        c = get_client(device_id)
        results = []
        for index, request in enumerate(requests):
            if not isinstance(request, dict):
                raise ValueError(f"requests[{index}] must be an object")
            unknown = set(request) - {"method", "path", "data", "params"}
            if unknown:
                names = ", ".join(sorted(unknown))
                raise ValueError(f"requests[{index}] has unsupported key(s): {names}")
            if "method" not in request or "path" not in request:
                raise ValueError(f"requests[{index}] requires method and path")
            results.append(
                await c.domain_request(
                    domain,
                    request["method"],
                    request["path"],
                    data=request.get("data"),
                    params=request.get("params"),
                )
            )
        return dump(results)

    # ── Discovery ───────────────────────────────────────────────────────────

    @mcp.tool()
    async def fgt_list_devices() -> str:
        """List all configured FortiGate devices."""
        devices = [
            {"id": d.id, "name": d.name, "host": d.host, "port": d.port, "vdom": d.vdom}
            for d in config.fortigates
        ]
        return json.dumps(devices, indent=2)

    @mcp.tool()
    async def fgt_api_request(
        device_id: str,
        method: str,
        path: str,
        data: Optional[Any] = None,
        params: Optional[dict] = None,
    ) -> str:
        """Call any FortiGate REST API v2 endpoint.

        This is the complete-coverage tool for documented FortiOS 8 REST
        endpoints that do not have a dedicated ``fgt_`` convenience tool.
        Authentication and one retry for an expired session are handled
        automatically. Paths must begin with ``/api/v2/``.

        Args:
            device_id: ID of the FortiGate device from config.
            method: HTTP method: get, post, put, or delete.
            path: Documented FortiGate REST path beginning with '/api/v2/'.
            data: Optional JSON request body for post and put requests.
            params: Optional query parameters such as vdom, filter, start, count,
                    action, or scope.
        """
        c = get_client(device_id)
        result = await c.request(method, path, data=data, params=params)
        return dump(result)

    @mcp.tool()
    async def fgt_api_batch(device_id: str, requests: list[dict]) -> str:
        """Run a sequence of FortiGate REST API operations.

        Requests execute in order and stop on the first API error. Each item
        accepts ``method``, ``path``, and optional ``data`` and ``params`` keys.
        Use this for related reads or carefully ordered configuration changes.

        Args:
            device_id: ID of the FortiGate device from config.
            requests: REST operation objects, limited to 50 per call.
        """
        if not requests:
            raise ValueError("requests must contain at least one operation")
        if len(requests) > 50:
            raise ValueError("fgt_api_batch accepts at most 50 operations")

        c = get_client(device_id)
        results = []
        for index, request in enumerate(requests):
            if not isinstance(request, dict):
                raise ValueError(f"requests[{index}] must be an object")
            unknown = set(request) - {"method", "path", "data", "params"}
            if unknown:
                names = ", ".join(sorted(unknown))
                raise ValueError(f"requests[{index}] has unsupported key(s): {names}")
            if "method" not in request or "path" not in request:
                raise ValueError(f"requests[{index}] requires method and path")
            results.append(
                await c.request(
                    request["method"],
                    request["path"],
                    data=request.get("data"),
                    params=request.get("params"),
                )
            )
        return dump(results)

    @mcp.tool()
    async def fgt_cmdb_request(
        device_id: str,
        method: str,
        path: str,
        data: Optional[Any] = None,
        params: Optional[dict] = None,
    ) -> str:
        """Call a FortiGate configuration endpoint under `/api/v2/cmdb/`.

        Args:
            device_id: ID of the FortiGate device from config.
            method: HTTP method: get, post, put, or delete.
            path: Relative CMDB path like `firewall/policy` or absolute
                  `/api/v2/cmdb/...` path.
            data: Optional JSON request body for post and put requests.
            params: Optional query parameters such as vdom, filter, start, or count.
        """
        return await domain_request(device_id, "cmdb", method, path, data, params)

    @mcp.tool()
    async def fgt_cmdb_batch(device_id: str, requests: list[dict]) -> str:
        """Run an ordered batch of FortiGate configuration requests under `/api/v2/cmdb/`."""
        return await domain_batch(device_id, "cmdb", requests)

    @mcp.tool()
    async def fgt_monitor_request(
        device_id: str,
        method: str,
        path: str,
        data: Optional[Any] = None,
        params: Optional[dict] = None,
    ) -> str:
        """Call a FortiGate monitoring endpoint under `/api/v2/monitor/`.

        Args:
            device_id: ID of the FortiGate device from config.
            method: HTTP method: get, post, put, or delete.
            path: Relative monitor path like `system/status` or absolute
                  `/api/v2/monitor/...` path.
            data: Optional JSON request body for post and put requests.
            params: Optional query parameters such as vdom, count, filter, or scope.
        """
        return await domain_request(device_id, "monitor", method, path, data, params)

    @mcp.tool()
    async def fgt_monitor_batch(device_id: str, requests: list[dict]) -> str:
        """Run an ordered batch of FortiGate monitoring requests under `/api/v2/monitor/`."""
        return await domain_batch(device_id, "monitor", requests)

    @mcp.tool()
    async def fgt_log_request(
        device_id: str,
        method: str,
        path: str,
        data: Optional[Any] = None,
        params: Optional[dict] = None,
    ) -> str:
        """Call a FortiGate log endpoint under `/api/v2/log/`.

        Args:
            device_id: ID of the FortiGate device from config.
            method: HTTP method: get, post, put, or delete.
            path: Relative log path like `disk/traffic` or absolute
                  `/api/v2/log/...` path.
            data: Optional JSON request body for post and put requests.
            params: Optional query parameters such as vdom, subtype, rows, or filter.
        """
        return await domain_request(device_id, "log", method, path, data, params)

    @mcp.tool()
    async def fgt_log_batch(device_id: str, requests: list[dict]) -> str:
        """Run an ordered batch of FortiGate log requests under `/api/v2/log/`."""
        return await domain_batch(device_id, "log", requests)

    @mcp.tool()
    async def fgt_service_request(
        device_id: str,
        method: str,
        path: str,
        data: Optional[Any] = None,
        params: Optional[dict] = None,
    ) -> str:
        """Call a FortiGate service endpoint under `/api/v2/service/`.

        Args:
            device_id: ID of the FortiGate device from config.
            method: HTTP method: get, post, put, or delete.
            path: Relative service path or absolute `/api/v2/service/...` path.
            data: Optional JSON request body for post and put requests.
            params: Optional query parameters documented for the service endpoint.
        """
        return await domain_request(device_id, "service", method, path, data, params)

    @mcp.tool()
    async def fgt_service_batch(device_id: str, requests: list[dict]) -> str:
        """Run an ordered batch of FortiGate service requests under `/api/v2/service/`."""
        return await domain_batch(device_id, "service", requests)

    # ── System ──────────────────────────────────────────────────────────────

    @mcp.tool()
    async def fgt_get_system_status(device_id: str) -> str:
        """Get system status of a FortiGate device (firmware, serial, uptime).

        Args:
            device_id: ID of the FortiGate device from config.
        """
        c = get_client(device_id)
        await c.login()
        result = await c.get_system_status()
        return dump(result)

    @mcp.tool()
    async def fgt_get_system_resources(device_id: str) -> str:
        """Get CPU and memory usage for a FortiGate device.

        Args:
            device_id: ID of the FortiGate device from config.
        """
        c = get_client(device_id)
        await c.login()
        result = await c.get_system_resources()
        return dump(result)

    @mcp.tool()
    async def fgt_get_interfaces(device_id: str) -> str:
        """List all network interfaces on a FortiGate.

        Args:
            device_id: ID of the FortiGate device from config.
        """
        c = get_client(device_id)
        await c.login()
        result = await c.get_interfaces()
        return dump(result)

    @mcp.tool()
    async def fgt_backup_config(device_id: str) -> str:
        """Download a full configuration backup from a FortiGate.

        Args:
            device_id: ID of the FortiGate device from config.
        """
        c = get_client(device_id)
        await c.login()
        return await c.backup_config()

    @mcp.tool()
    async def fgt_execute_cli(device_id: str, commands: list[str]) -> str:
        """Execute CLI commands on a FortiGate and return output.

        Args:
            device_id: ID of the FortiGate device from config.
            commands: List of CLI commands to execute (e.g. ["get system status"]).
        """
        c = get_client(device_id)
        await c.login()
        result = await c.execute_cli(commands)
        return dump(result)

    @mcp.tool()
    async def fgt_get_ha_status(device_id: str) -> str:
        """Get HA cluster status for a FortiGate.

        Args:
            device_id: ID of the FortiGate device from config.
        """
        c = get_client(device_id)
        await c.login()
        result = await c.get_ha_status()
        return dump(result)

    # ── Firewall Policies ───────────────────────────────────────────────────

    @mcp.tool()
    async def fgt_get_firewall_policies(device_id: str, policy_id: Optional[int] = None) -> str:
        """List firewall policies on a FortiGate, optionally filtered by policy ID.

        Args:
            device_id: ID of the FortiGate device from config.
            policy_id: Optional specific policy ID to retrieve.
        """
        c = get_client(device_id)
        await c.login()
        result = await c.get_firewall_policies(policy_id)
        return dump(result)

    @mcp.tool()
    async def fgt_create_firewall_policy(device_id: str, policy: dict) -> str:
        """Create a firewall policy on a FortiGate.

        Args:
            device_id: ID of the FortiGate device from config.
            policy: Policy definition dict. Required keys: name, srcintf, dstintf,
                    srcaddr, dstaddr, action, schedule, service.
                    Example:
                    {
                      "name": "allow-web",
                      "srcintf": [{"name": "port1"}],
                      "dstintf": [{"name": "port2"}],
                      "srcaddr": [{"name": "all"}],
                      "dstaddr": [{"name": "all"}],
                      "action": "accept",
                      "schedule": "always",
                      "service": [{"name": "HTTP"}],
                      "nat": "enable"
                    }
        """
        c = get_client(device_id)
        await c.login()
        result = await c.create_firewall_policy(policy)
        return dump(result)

    @mcp.tool()
    async def fgt_update_firewall_policy(device_id: str, policy_id: int, policy: dict) -> str:
        """Update an existing firewall policy on a FortiGate.

        Args:
            device_id: ID of the FortiGate device from config.
            policy_id: Numeric ID of the policy to update.
            policy: Dict of fields to update.
        """
        c = get_client(device_id)
        await c.login()
        result = await c.update_firewall_policy(policy_id, policy)
        return dump(result)

    @mcp.tool()
    async def fgt_delete_firewall_policy(device_id: str, policy_id: int) -> str:
        """Delete a firewall policy from a FortiGate.

        Args:
            device_id: ID of the FortiGate device from config.
            policy_id: Numeric ID of the policy to delete.
        """
        c = get_client(device_id)
        await c.login()
        result = await c.delete_firewall_policy(policy_id)
        return dump(result)

    @mcp.tool()
    async def fgt_move_firewall_policy(
        device_id: str, policy_id: int, action: str, neighbor: int
    ) -> str:
        """Move a firewall policy relative to another policy.

        Args:
            device_id: ID of the FortiGate device from config.
            policy_id: Policy ID to move.
            action: Reorder action such as before or after.
            neighbor: Neighbor policy ID used by the action.
        """
        c = get_client(device_id)
        await c.login()
        result = await c.move_firewall_policy(policy_id, action, neighbor)
        return dump(result)

    # ── Address Objects ─────────────────────────────────────────────────────

    @mcp.tool()
    async def fgt_get_address_objects(device_id: str, name: Optional[str] = None) -> str:
        """List firewall address objects on a FortiGate.

        Args:
            device_id: ID of the FortiGate device from config.
            name: Optional specific address object name.
        """
        c = get_client(device_id)
        await c.login()
        result = await c.get_address_objects(name)
        return dump(result)

    @mcp.tool()
    async def fgt_create_address_object(device_id: str, obj: dict) -> str:
        """Create an address object on a FortiGate.

        Args:
            device_id: ID of the FortiGate device from config.
            obj: Address object dict. Example for subnet:
                 {"name": "web-server", "type": "ipmask", "subnet": "10.0.0.10 255.255.255.255"}
                 Example for FQDN:
                 {"name": "example-com", "type": "fqdn", "fqdn": "example.com"}
        """
        c = get_client(device_id)
        await c.login()
        result = await c.create_address_object(obj)
        return dump(result)

    @mcp.tool()
    async def fgt_update_address_object(device_id: str, name: str, obj: dict) -> str:
        """Update an address object on a FortiGate.

        Args:
            device_id: ID of the FortiGate device from config.
            name: Name of the address object to update.
            obj: Dict of fields to update.
        """
        c = get_client(device_id)
        await c.login()
        result = await c.update_address_object(name, obj)
        return dump(result)

    @mcp.tool()
    async def fgt_delete_address_object(device_id: str, name: str) -> str:
        """Delete an address object from a FortiGate.

        Args:
            device_id: ID of the FortiGate device from config.
            name: Name of the address object to delete.
        """
        c = get_client(device_id)
        await c.login()
        result = await c.delete_address_object(name)
        return dump(result)

    @mcp.tool()
    async def fgt_get_address_groups(device_id: str, name: Optional[str] = None) -> str:
        """List firewall address groups on a FortiGate.

        Args:
            device_id: ID of the FortiGate device from config.
            name: Optional specific group name.
        """
        c = get_client(device_id)
        await c.login()
        result = await c.get_address_groups(name)
        return dump(result)

    @mcp.tool()
    async def fgt_create_address_group(device_id: str, obj: dict) -> str:
        """Create an address group on a FortiGate.

        Args:
            device_id: ID of the FortiGate device from config.
            obj: Group dict. Example:
                 {"name": "web-servers", "member": [{"name": "web1"}, {"name": "web2"}]}
        """
        c = get_client(device_id)
        await c.login()
        result = await c.create_address_group(obj)
        return dump(result)

    @mcp.tool()
    async def fgt_update_address_group(device_id: str, name: str, obj: dict) -> str:
        """Update an address group on a FortiGate."""
        c = get_client(device_id)
        await c.login()
        result = await c.update_address_group(name, obj)
        return dump(result)

    @mcp.tool()
    async def fgt_delete_address_group(device_id: str, name: str) -> str:
        """Delete an address group from a FortiGate."""
        c = get_client(device_id)
        await c.login()
        result = await c.delete_address_group(name)
        return dump(result)

    # ── Services ────────────────────────────────────────────────────────────

    @mcp.tool()
    async def fgt_get_service_objects(device_id: str, name: Optional[str] = None) -> str:
        """List service objects on a FortiGate.

        Args:
            device_id: ID of the FortiGate device from config.
            name: Optional specific service name.
        """
        c = get_client(device_id)
        await c.login()
        result = await c.get_service_objects(name)
        return dump(result)

    @mcp.tool()
    async def fgt_create_service_object(device_id: str, obj: dict) -> str:
        """Create a service object on a FortiGate.

        Args:
            device_id: ID of the FortiGate device from config.
            obj: Service object dict. Example:
                 {"name": "custom-8080", "protocol": "TCP/UDP/SCTP", "tcp-portrange": "8080"}
        """
        c = get_client(device_id)
        await c.login()
        result = await c.create_service_object(obj)
        return dump(result)

    @mcp.tool()
    async def fgt_update_service_object(device_id: str, name: str, obj: dict) -> str:
        """Update a service object on a FortiGate."""
        c = get_client(device_id)
        await c.login()
        result = await c.update_service_object(name, obj)
        return dump(result)

    @mcp.tool()
    async def fgt_delete_service_object(device_id: str, name: str) -> str:
        """Delete a service object from a FortiGate."""
        c = get_client(device_id)
        await c.login()
        result = await c.delete_service_object(name)
        return dump(result)

    @mcp.tool()
    async def fgt_get_service_groups(device_id: str, name: Optional[str] = None) -> str:
        """List service groups on a FortiGate."""
        c = get_client(device_id)
        await c.login()
        result = await c.get_service_groups(name)
        return dump(result)

    @mcp.tool()
    async def fgt_create_service_group(device_id: str, obj: dict) -> str:
        """Create a service group on a FortiGate."""
        c = get_client(device_id)
        await c.login()
        result = await c.create_service_group(obj)
        return dump(result)

    @mcp.tool()
    async def fgt_update_service_group(device_id: str, name: str, obj: dict) -> str:
        """Update a service group on a FortiGate."""
        c = get_client(device_id)
        await c.login()
        result = await c.update_service_group(name, obj)
        return dump(result)

    @mcp.tool()
    async def fgt_delete_service_group(device_id: str, name: str) -> str:
        """Delete a service group from a FortiGate."""
        c = get_client(device_id)
        await c.login()
        result = await c.delete_service_group(name)
        return dump(result)

    # ── Routing ─────────────────────────────────────────────────────────────

    @mcp.tool()
    async def fgt_get_static_routes(device_id: str) -> str:
        """List static routes configured on a FortiGate.

        Args:
            device_id: ID of the FortiGate device from config.
        """
        c = get_client(device_id)
        await c.login()
        result = await c.get_static_routes()
        return dump(result)

    @mcp.tool()
    async def fgt_create_static_route(device_id: str, route: dict) -> str:
        """Create a static route on a FortiGate.

        Args:
            device_id: ID of the FortiGate device from config.
            route: Route dict. Example:
                   {"dst": "10.0.0.0 255.255.255.0", "gateway": "192.168.1.254",
                    "device": "port1", "distance": 10}
        """
        c = get_client(device_id)
        await c.login()
        result = await c.create_static_route(route)
        return dump(result)

    @mcp.tool()
    async def fgt_update_static_route(device_id: str, seq_num: int, route: dict) -> str:
        """Update a static route on a FortiGate."""
        c = get_client(device_id)
        await c.login()
        result = await c.update_static_route(seq_num, route)
        return dump(result)

    @mcp.tool()
    async def fgt_delete_static_route(device_id: str, seq_num: int) -> str:
        """Delete a static route from a FortiGate.

        Args:
            device_id: ID of the FortiGate device from config.
            seq_num: Sequence number of the static route to delete.
        """
        c = get_client(device_id)
        await c.login()
        result = await c.delete_static_route(seq_num)
        return dump(result)

    @mcp.tool()
    async def fgt_get_routing_table(device_id: str) -> str:
        """Get the active routing table from a FortiGate.

        Args:
            device_id: ID of the FortiGate device from config.
        """
        c = get_client(device_id)
        await c.login()
        result = await c.get_routing_table()
        return dump(result)

    @mcp.tool()
    async def fgt_get_bgp_neighbors(device_id: str) -> str:
        """Get BGP neighbor status from a FortiGate.

        Args:
            device_id: ID of the FortiGate device from config.
        """
        c = get_client(device_id)
        await c.login()
        result = await c.get_bgp_neighbors()
        return dump(result)

    # ── VPN ─────────────────────────────────────────────────────────────────

    @mcp.tool()
    async def fgt_get_ipsec_tunnels(device_id: str) -> str:
        """Get active IPsec VPN tunnel status from a FortiGate.

        Args:
            device_id: ID of the FortiGate device from config.
        """
        c = get_client(device_id)
        await c.login()
        result = await c.get_ipsec_tunnels()
        return dump(result)

    @mcp.tool()
    async def fgt_get_ipsec_phase1_config(device_id: str, name: Optional[str] = None) -> str:
        """Get IPsec Phase1 interface configuration from a FortiGate.

        Args:
            device_id: ID of the FortiGate device from config.
            name: Optional specific tunnel name.
        """
        c = get_client(device_id)
        await c.login()
        result = await c.get_ipsec_phase1(name)
        return dump(result)

    @mcp.tool()
    async def fgt_create_ipsec_phase1(device_id: str, config: dict) -> str:
        """Create an IPsec Phase1 tunnel interface on a FortiGate.

        Args:
            device_id: ID of the FortiGate device from config.
            config: Phase1 configuration dict including name, interface, remote-gw, psksecret, etc.
        """
        c = get_client(device_id)
        await c.login()
        result = await c.create_ipsec_phase1(config)
        return dump(result)

    @mcp.tool()
    async def fgt_update_ipsec_phase1(device_id: str, name: str, config: dict) -> str:
        """Update an IPsec Phase1 tunnel interface on a FortiGate."""
        c = get_client(device_id)
        await c.login()
        result = await c.update_ipsec_phase1(name, config)
        return dump(result)

    @mcp.tool()
    async def fgt_delete_ipsec_phase1(device_id: str, name: str) -> str:
        """Delete an IPsec Phase1 tunnel interface from a FortiGate."""
        c = get_client(device_id)
        await c.login()
        result = await c.delete_ipsec_phase1(name)
        return dump(result)

    @mcp.tool()
    async def fgt_get_ssl_vpn_settings(device_id: str) -> str:
        """Get SSL-VPN settings from a FortiGate."""
        c = get_client(device_id)
        await c.login()
        result = await c.get_ssl_vpn_settings()
        return dump(result)

    @mcp.tool()
    async def fgt_get_ssl_vpn_sessions(device_id: str) -> str:
        """Get active SSL-VPN sessions on a FortiGate.

        Args:
            device_id: ID of the FortiGate device from config.
        """
        c = get_client(device_id)
        await c.login()
        result = await c.get_ssl_vpn_sessions()
        return dump(result)

    # ── Sessions & Monitoring ───────────────────────────────────────────────

    @mcp.tool()
    async def fgt_get_active_sessions(device_id: str, count: int = 100) -> str:
        """Get active firewall sessions on a FortiGate.

        Args:
            device_id: ID of the FortiGate device from config.
            count: Maximum number of sessions to return (default 100).
        """
        c = get_client(device_id)
        await c.login()
        result = await c.get_active_sessions(count)
        return dump(result)

    @mcp.tool()
    async def fgt_get_session_stats(device_id: str) -> str:
        """Get session table statistics from a FortiGate.

        Args:
            device_id: ID of the FortiGate device from config.
        """
        c = get_client(device_id)
        await c.login()
        result = await c.get_session_stats()
        return dump(result)

    @mcp.tool()
    async def fgt_get_fortiview_top_sources(device_id: str) -> str:
        """Get top FortiView sources from a FortiGate."""
        c = get_client(device_id)
        await c.login()
        result = await c.get_fortiview_top_sources()
        return dump(result)

    @mcp.tool()
    async def fgt_get_threat_feeds(device_id: str) -> str:
        """List configured threat feeds on a FortiGate."""
        c = get_client(device_id)
        await c.login()
        result = await c.get_threat_feeds()
        return dump(result)

    # ── Logs ────────────────────────────────────────────────────────────────

    @mcp.tool()
    async def fgt_get_logs(
        device_id: str,
        log_type: str = "traffic",
        subtype: str = "forward",
        rows: int = 50,
    ) -> str:
        """Retrieve logs from a FortiGate's disk log.

        Args:
            device_id: ID of the FortiGate device from config.
            log_type: Log type: traffic, event, utm, virus, webfilter, etc. (default: traffic).
            subtype: Log subtype, e.g. forward, local, multicast (default: forward).
            rows: Number of log entries to return (default 50).
        """
        c = get_client(device_id)
        await c.login()
        result = await c.get_logs(log_type, subtype, rows)
        return dump(result)
