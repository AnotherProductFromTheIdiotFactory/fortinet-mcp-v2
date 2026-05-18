from __future__ import annotations

import json
from typing import Optional

from mcp.server.fastmcp import FastMCP

from clients.fortianalyzer import FortiAnalyzerClient
from config import Config


def _client_cache(config: Config) -> dict[str, FortiAnalyzerClient]:
    return {d.id: FortiAnalyzerClient(d) for d in config.fortianalyzers}


def register_fortianalyzer_tools(mcp: FastMCP, config: Config):
    clients: dict[str, FortiAnalyzerClient] = _client_cache(config)

    def get_client(device_id: str) -> FortiAnalyzerClient:
        config.get_faz(device_id)
        if device_id not in clients:
            clients[device_id] = FortiAnalyzerClient(config.get_faz(device_id))
        return clients[device_id]

    # ── Discovery ───────────────────────────────────────────────────────────

    @mcp.tool()
    async def faz_list_devices() -> str:
        """List all configured FortiAnalyzer instances."""
        devices = [
            {"id": d.id, "name": d.name, "host": d.host, "port": d.port, "adom": d.adom}
            for d in config.fortianalyzers
        ]
        return json.dumps(devices, indent=2)

    # ── System ──────────────────────────────────────────────────────────────

    @mcp.tool()
    async def faz_get_system_status(device_id: str) -> str:
        """Get FortiAnalyzer system status (version, serial, disk usage).

        Args:
            device_id: ID of the FortiAnalyzer instance from config.
        """
        c = get_client(device_id)
        await c.login()
        result = await c.get_system_status()
        return json.dumps(result, indent=2)

    @mcp.tool()
    async def faz_get_adoms(device_id: str) -> str:
        """List all ADOMs on a FortiAnalyzer.

        Args:
            device_id: ID of the FortiAnalyzer instance from config.
        """
        c = get_client(device_id)
        await c.login()
        result = await c.get_adoms()
        return json.dumps(result, indent=2)

    # ── Device Registration ──────────────────────────────────────────────────

    @mcp.tool()
    async def faz_get_registered_devices(device_id: str, adom: Optional[str] = None) -> str:
        """List all log-sending devices registered in a FortiAnalyzer ADOM.

        Args:
            device_id: ID of the FortiAnalyzer instance from config.
            adom: ADOM name (uses default from config if not specified).
        """
        c = get_client(device_id)
        await c.login()
        result = await c.get_devices(adom)
        return json.dumps(result, indent=2)

    @mcp.tool()
    async def faz_get_device_groups(device_id: str, adom: Optional[str] = None) -> str:
        """List device groups in a FortiAnalyzer ADOM.

        Args:
            device_id: ID of the FortiAnalyzer instance from config.
            adom: ADOM name (uses default from config if not specified).
        """
        c = get_client(device_id)
        await c.login()
        result = await c.get_device_groups(adom)
        return json.dumps(result, indent=2)

    @mcp.tool()
    async def faz_register_device(
        device_id: str, device_data: dict, adom: Optional[str] = None
    ) -> str:
        """Register a FortiGate device with a FortiAnalyzer for log collection.

        Args:
            device_id: ID of the FortiAnalyzer instance from config.
            device_data: Device registration data. Example:
                         {"name": "fgt-01", "ip": "192.168.1.1", "adm_usr": "admin",
                          "adm_pass": "password"}
            adom: ADOM name (uses default from config if not specified).
        """
        c = get_client(device_id)
        await c.login()
        result = await c.register_device(device_data, adom)
        return json.dumps(result, indent=2)

    # ── Log Queries ──────────────────────────────────────────────────────────

    @mcp.tool()
    async def faz_query_logs(
        device_id: str,
        log_type: str = "traffic",
        device: str = "All_FortiGate",
        filter: Optional[list] = None,
        time_from: Optional[int] = None,
        time_to: Optional[int] = None,
        limit: int = 100,
        offset: int = 0,
        fields: Optional[list[str]] = None,
        adom: Optional[str] = None,
    ) -> str:
        """Query logs on a FortiAnalyzer with optional filters.

        Args:
            device_id: ID of the FortiAnalyzer instance from config.
            log_type: Log type: traffic, event, utm, virus, webfilter, ips, app-ctrl, etc.
            device: Device name or "All_FortiGate" for all devices.
            filter: List of filter conditions. Example:
                    [["srcip", "==", "10.0.0.1"], "&&", ["action", "==", "deny"]]
            time_from: Start time as Unix timestamp (epoch seconds).
            time_to: End time as Unix timestamp (epoch seconds).
            limit: Max results to return (default 100).
            offset: Pagination offset (default 0).
            fields: List of specific fields to return (returns all if not specified).
            adom: ADOM name (uses default from config if not specified).
        """
        c = get_client(device_id)
        await c.login()
        result = await c.query_logs(
            adom=adom,
            device=device,
            log_type=log_type,
            filter=filter,
            time_from=time_from,
            time_to=time_to,
            limit=limit,
            offset=offset,
            fields=fields,
        )
        return json.dumps(result, indent=2)

    @mcp.tool()
    async def faz_get_log_fields(
        device_id: str, log_type: str = "traffic", adom: Optional[str] = None
    ) -> str:
        """Get available log fields for a log type on FortiAnalyzer.

        Args:
            device_id: ID of the FortiAnalyzer instance from config.
            log_type: Log type to inspect: traffic, event, utm, etc.
            adom: ADOM name (uses default from config if not specified).
        """
        c = get_client(device_id)
        await c.login()
        result = await c.get_log_fields(log_type, adom)
        return json.dumps(result, indent=2)

    @mcp.tool()
    async def faz_search_logs(
        device_id: str,
        log_type: str,
        filter: list,
        time_from: int,
        time_to: int,
        limit: int = 1000,
        adom: Optional[str] = None,
    ) -> str:
        """Start an async log search job on FortiAnalyzer. Returns a job ID for polling.

        Args:
            device_id: ID of the FortiAnalyzer instance from config.
            log_type: Log type: traffic, event, utm, virus, webfilter, ips, etc.
            filter: Filter conditions list. Example:
                    [["dstip", "==", "8.8.8.8"]]
            time_from: Search start time as Unix timestamp.
            time_to: Search end time as Unix timestamp.
            limit: Maximum results (default 1000).
            adom: ADOM name (uses default from config if not specified).
        """
        c = get_client(device_id)
        await c.login()
        result = await c.start_log_search(adom, log_type, filter, time_from, time_to, limit)
        return json.dumps(result, indent=2)

    # ── Reports ──────────────────────────────────────────────────────────────

    @mcp.tool()
    async def faz_get_reports(device_id: str, adom: Optional[str] = None) -> str:
        """List generated reports on a FortiAnalyzer.

        Args:
            device_id: ID of the FortiAnalyzer instance from config.
            adom: ADOM name (uses default from config if not specified).
        """
        c = get_client(device_id)
        await c.login()
        result = await c.get_reports(adom)
        return json.dumps(result, indent=2)

    @mcp.tool()
    async def faz_get_report_templates(device_id: str, adom: Optional[str] = None) -> str:
        """List available report templates on a FortiAnalyzer.

        Args:
            device_id: ID of the FortiAnalyzer instance from config.
            adom: ADOM name (uses default from config if not specified).
        """
        c = get_client(device_id)
        await c.login()
        result = await c.get_report_templates(adom)
        return json.dumps(result, indent=2)

    @mcp.tool()
    async def faz_run_report(
        device_id: str,
        template_name: str,
        time_from: int,
        time_to: int,
        device: str = "All_FortiGate",
        adom: Optional[str] = None,
    ) -> str:
        """Run a report from a template on FortiAnalyzer. Returns a task ID.

        Args:
            device_id: ID of the FortiAnalyzer instance from config.
            template_name: Name of the report template to use.
            time_from: Report start time as Unix timestamp.
            time_to: Report end time as Unix timestamp.
            device: Device or device group name (default: All_FortiGate).
            adom: ADOM name (uses default from config if not specified).
        """
        c = get_client(device_id)
        await c.login()
        result = await c.run_report(template_name, time_from, time_to, device, adom)
        return json.dumps(result, indent=2)

    @mcp.tool()
    async def faz_get_report_status(
        device_id: str, task_id: int, adom: Optional[str] = None
    ) -> str:
        """Check the status of a running FortiAnalyzer report task.

        Args:
            device_id: ID of the FortiAnalyzer instance from config.
            task_id: Report task ID returned by faz_run_report.
            adom: ADOM name (uses default from config if not specified).
        """
        c = get_client(device_id)
        await c.login()
        result = await c.get_report_status(task_id, adom)
        return json.dumps(result, indent=2)

    # ── Incidents & Events ───────────────────────────────────────────────────

    @mcp.tool()
    async def faz_get_incidents(
        device_id: str,
        status: Optional[str] = None,
        limit: int = 50,
        adom: Optional[str] = None,
    ) -> str:
        """List security incidents on a FortiAnalyzer.

        Args:
            device_id: ID of the FortiAnalyzer instance from config.
            status: Optional filter by status: open, closed, in-progress.
            limit: Maximum incidents to return (default 50).
            adom: ADOM name (uses default from config if not specified).
        """
        c = get_client(device_id)
        await c.login()
        result = await c.get_incidents(adom, status, limit)
        return json.dumps(result, indent=2)

    @mcp.tool()
    async def faz_get_events(
        device_id: str,
        severity: Optional[str] = None,
        limit: int = 100,
        adom: Optional[str] = None,
    ) -> str:
        """List security events on a FortiAnalyzer.

        Args:
            device_id: ID of the FortiAnalyzer instance from config.
            severity: Optional filter: critical, high, medium, low, info.
            limit: Maximum events to return (default 100).
            adom: ADOM name (uses default from config if not specified).
        """
        c = get_client(device_id)
        await c.login()
        result = await c.get_events(adom, severity, limit)
        return json.dumps(result, indent=2)

    @mcp.tool()
    async def faz_get_event_handlers(device_id: str, adom: Optional[str] = None) -> str:
        """List event alert handlers configured on a FortiAnalyzer.

        Args:
            device_id: ID of the FortiAnalyzer instance from config.
            adom: ADOM name (uses default from config if not specified).
        """
        c = get_client(device_id)
        await c.login()
        result = await c.get_event_handlers(adom)
        return json.dumps(result, indent=2)

    # ── FortiView / Statistics ───────────────────────────────────────────────

    @mcp.tool()
    async def faz_get_traffic_summary(
        device_id: str,
        time_period: int = 86400,
        device: str = "All_FortiGate",
        adom: Optional[str] = None,
    ) -> str:
        """Get traffic summary statistics from FortiAnalyzer.

        Args:
            device_id: ID of the FortiAnalyzer instance from config.
            time_period: Time window in seconds (default 86400 = 24 hours).
            device: Device name or "All_FortiGate".
            adom: ADOM name (uses default from config if not specified).
        """
        c = get_client(device_id)
        await c.login()
        result = await c.get_traffic_summary(adom, time_period, device)
        return json.dumps(result, indent=2)

    @mcp.tool()
    async def faz_get_threat_summary(
        device_id: str,
        time_period: int = 86400,
        device: str = "All_FortiGate",
        adom: Optional[str] = None,
    ) -> str:
        """Get threat/security summary statistics from FortiAnalyzer.

        Args:
            device_id: ID of the FortiAnalyzer instance from config.
            time_period: Time window in seconds (default 86400 = 24 hours).
            device: Device name or "All_FortiGate".
            adom: ADOM name (uses default from config if not specified).
        """
        c = get_client(device_id)
        await c.login()
        result = await c.get_threat_summary(adom, time_period, device)
        return json.dumps(result, indent=2)

    @mcp.tool()
    async def faz_get_top_sources(
        device_id: str,
        time_period: int = 3600,
        limit: int = 20,
        adom: Optional[str] = None,
    ) -> str:
        """Get top traffic source IPs from FortiAnalyzer FortiView.

        Args:
            device_id: ID of the FortiAnalyzer instance from config.
            time_period: Time window in seconds (default 3600 = 1 hour).
            limit: Number of top entries to return (default 20).
            adom: ADOM name (uses default from config if not specified).
        """
        c = get_client(device_id)
        await c.login()
        result = await c.get_top_sources(adom, time_period, limit)
        return json.dumps(result, indent=2)

    @mcp.tool()
    async def faz_get_top_threats(
        device_id: str,
        time_period: int = 3600,
        limit: int = 20,
        adom: Optional[str] = None,
    ) -> str:
        """Get top security threats detected by FortiAnalyzer FortiView.

        Args:
            device_id: ID of the FortiAnalyzer instance from config.
            time_period: Time window in seconds (default 3600 = 1 hour).
            limit: Number of top entries to return (default 20).
            adom: ADOM name (uses default from config if not specified).
        """
        c = get_client(device_id)
        await c.login()
        result = await c.get_top_threats(adom, time_period, limit)
        return json.dumps(result, indent=2)

    @mcp.tool()
    async def faz_get_top_applications(
        device_id: str,
        time_period: int = 3600,
        limit: int = 20,
        adom: Optional[str] = None,
    ) -> str:
        """Get top applications by traffic volume from FortiAnalyzer FortiView.

        Args:
            device_id: ID of the FortiAnalyzer instance from config.
            time_period: Time window in seconds (default 3600 = 1 hour).
            limit: Number of top entries to return (default 20).
            adom: ADOM name (uses default from config if not specified).
        """
        c = get_client(device_id)
        await c.login()
        result = await c.get_top_applications(adom, time_period, limit)
        return json.dumps(result, indent=2)
