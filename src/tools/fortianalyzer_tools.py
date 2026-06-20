from __future__ import annotations

import json
from typing import Any, Optional

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

    @mcp.tool()
    async def faz_api_request(
        device_id: str,
        method: str,
        url: str,
        data: Optional[Any] = None,
        params: Optional[dict] = None,
    ) -> str:
        """Call any FortiAnalyzer v8 JSON-RPC endpoint.

        This is the complete-coverage tool for documented API functions that do
        not have a dedicated ``faz_`` convenience tool. Authentication and
        session renewal are handled automatically.

        Args:
            device_id: ID of the FortiAnalyzer instance from config.
            method: JSON-RPC method: get, add, set, update, delete, exec, or execute.
            url: Documented API URL beginning with '/', for example '/sys/status'.
            data: Optional endpoint request body placed in the RPC data member.
            params: Optional RPC controls such as filter, fields, option, loadsub,
                    range, sortings, target, or flags.
        """
        c = get_client(device_id)
        result = await c.request(method, url, data=data, params=params)
        return json.dumps(result, indent=2)

    @mcp.tool()
    async def faz_api_batch(device_id: str, requests: list[dict]) -> str:
        """Run a sequence of FortiAnalyzer v8 JSON-RPC operations.

        Requests execute in order and stop on the first API error. Each item
        accepts ``method``, ``url``, and optional ``data`` and ``params`` keys.
        Use this for related reads or carefully ordered configuration changes.

        Args:
            device_id: ID of the FortiAnalyzer instance from config.
            requests: JSON-RPC operation objects, limited to 50 per call.
        """
        if not requests:
            raise ValueError("requests must contain at least one operation")
        if len(requests) > 50:
            raise ValueError("faz_api_batch accepts at most 50 operations")

        c = get_client(device_id)
        results = []
        for index, request in enumerate(requests):
            if not isinstance(request, dict):
                raise ValueError(f"requests[{index}] must be an object")
            unknown = set(request) - {"method", "url", "data", "params"}
            if unknown:
                names = ", ".join(sorted(unknown))
                raise ValueError(f"requests[{index}] has unsupported key(s): {names}")
            if "method" not in request or "url" not in request:
                raise ValueError(f"requests[{index}] requires method and url")
            results.append(
                await c.request(
                    request["method"],
                    request["url"],
                    data=request.get("data"),
                    params=request.get("params"),
                )
            )
        return json.dumps(results, indent=2)

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

    # ── Log Queries ──────────────────────────────────────────────────────────

    @mcp.tool()
    async def faz_query_logs(
        device_id: str,
        time_from: str | int,
        time_to: str | int,
        log_type: str = "traffic",
        device: str | list[dict] = "All_FortiGate",
        filter: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
        timezone: Optional[str] = None,
        adom: Optional[str] = None,
    ) -> str:
        """Start a FortiAnalyzer v8 log search and return its task ID.

        Args:
            device_id: ID of the FortiAnalyzer instance from config.
            time_from: RFC 3339 date-time or Unix timestamp for the search start.
            time_to: RFC 3339 date-time or Unix timestamp for the search end.
            log_type: Official v8 log type such as traffic, event, virus, or webfilter.
            device: All-device ID or list of official device selector objects.
            filter: FortiAnalyzer filter expression string.
            limit: Max results to return (default 100).
            offset: Pagination offset (default 0).
            timezone: Optional FortiAnalyzer timezone name or index.
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
            timezone_name=timezone,
        )
        return json.dumps(result, indent=2)

    @mcp.tool()
    async def faz_get_log_fields(
        device_id: str,
        log_type: str = "traffic",
        device_type: str = "FortiGate",
        subtype: str = "",
        adom: Optional[str] = None,
    ) -> str:
        """Get available log fields for a log type on FortiAnalyzer.

        Args:
            device_id: ID of the FortiAnalyzer instance from config.
            log_type: Official v8 log type to inspect.
            device_type: Device family, such as FortiGate or FortiAnalyzer.
            subtype: Optional log subtype.
            adom: ADOM name (uses default from config if not specified).
        """
        c = get_client(device_id)
        await c.login()
        result = await c.get_log_fields(log_type, adom, device_type, subtype)
        return json.dumps(result, indent=2)

    @mcp.tool()
    async def faz_search_logs(
        device_id: str,
        time_from: str | int,
        time_to: str | int,
        log_type: str = "traffic",
        filter: Optional[str] = None,
        device: str | list[dict] = "All_FortiGate",
        limit: int = 100,
        adom: Optional[str] = None,
    ) -> str:
        """Start an async log search job on FortiAnalyzer. Returns a job ID for polling.

        Args:
            device_id: ID of the FortiAnalyzer instance from config.
            time_from: RFC 3339 date-time or Unix timestamp for the search start.
            time_to: RFC 3339 date-time or Unix timestamp for the search end.
            log_type: Official v8 log type.
            filter: FortiAnalyzer filter expression string.
            device: All-device ID or list of official device selector objects.
            limit: Maximum results requested from the search task.
            adom: ADOM name (uses default from config if not specified).
        """
        c = get_client(device_id)
        await c.login()
        result = await c.start_log_search(
            adom, log_type, filter, time_from, time_to, limit, device
        )
        return json.dumps(result, indent=2)

    @mcp.tool()
    async def faz_get_log_search_results(
        device_id: str,
        task_id: int,
        limit: int = 50,
        offset: int = 0,
        adom: Optional[str] = None,
    ) -> str:
        """Poll or page through results from a FortiAnalyzer v8 log-search task."""
        result = await get_client(device_id).get_log_search_results(task_id, adom, limit, offset)
        return json.dumps(result, indent=2)

    @mcp.tool()
    async def faz_get_log_search_count(
        device_id: str, task_id: int, adom: Optional[str] = None
    ) -> str:
        """Get the current result count for a FortiAnalyzer v8 log-search task."""
        result = await get_client(device_id).get_log_search_count(task_id, adom)
        return json.dumps(result, indent=2)

    @mcp.tool()
    async def faz_delete_log_search(
        device_id: str, task_id: int, adom: Optional[str] = None
    ) -> str:
        """Delete a completed FortiAnalyzer v8 log-search task."""
        result = await get_client(device_id).delete_log_search(task_id, adom)
        return json.dumps(result, indent=2)

    # ── Reports ──────────────────────────────────────────────────────────────

    @mcp.tool()
    async def faz_get_reports(
        device_id: str,
        state: str,
        time_from: Optional[str | int] = None,
        time_to: Optional[str | int] = None,
        timezone: Optional[str] = None,
        title: Optional[str] = None,
        adom: Optional[str] = None,
    ) -> str:
        """List generated reports in an official FortiAnalyzer report state.

        Args:
            device_id: ID of the FortiAnalyzer instance from config.
            adom: ADOM name (uses default from config if not specified).
        """
        c = get_client(device_id)
        await c.login()
        result = await c.get_reports(state, adom, time_from, time_to, timezone, title)
        return json.dumps(result, indent=2)

    @mcp.tool()
    async def faz_get_report_templates(
        device_id: str,
        device_type: str = "fgt",
        language: str = "en",
        adom: Optional[str] = None,
    ) -> str:
        """List available report templates on a FortiAnalyzer.

        Args:
            device_id: ID of the FortiAnalyzer instance from config.
            adom: ADOM name (uses default from config if not specified).
        """
        c = get_client(device_id)
        await c.login()
        result = await c.get_report_templates(adom, device_type, language)
        return json.dumps(result, indent=2)

    @mcp.tool()
    async def faz_run_report(
        device_id: str,
        schedule: Optional[str] = None,
        schedule_params: Optional[dict] = None,
        adom: Optional[str] = None,
    ) -> str:
        """Start a v8 report task from a schedule or schedule parameters.

        Args:
            device_id: ID of the FortiAnalyzer instance from config.
            schedule: Existing report schedule name or ID.
            schedule_params: Official schedule-param object. Without a schedule,
                             layout-id, device, and time-period are required by v8.
            adom: ADOM name (uses default from config if not specified).
        """
        c = get_client(device_id)
        await c.login()
        result = await c.run_report(schedule, schedule_params, adom)
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

    @mcp.tool()
    async def faz_download_report(
        device_id: str,
        task_id: int,
        report_format: str = "PDF",
        data_type: Optional[str] = None,
        adom: Optional[str] = None,
    ) -> str:
        """Download a completed FortiAnalyzer report through JSON-RPC.

        Args:
            device_id: ID of the FortiAnalyzer instance from config.
            task_id: Completed report task ID returned by faz_run_report.
            adom: ADOM name (uses default from config if not specified).
        """
        c = get_client(device_id)
        result = await c.download_report(task_id, adom, report_format, data_type)
        return json.dumps(result, indent=2)

    # ── Incidents & Events ───────────────────────────────────────────────────

    @mcp.tool()
    async def faz_get_incidents(
        device_id: str,
        filter: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
        detail_level: Optional[str] = None,
        adom: Optional[str] = None,
    ) -> str:
        """List security incidents on a FortiAnalyzer.

        Args:
            device_id: ID of the FortiAnalyzer instance from config.
            filter: FortiAnalyzer incident filter expression string.
            limit: Maximum incidents to return (default 50).
            offset: Pagination offset.
            detail_level: Optional response detail level.
            adom: ADOM name (uses default from config if not specified).
        """
        c = get_client(device_id)
        await c.login()
        result = await c.get_incidents(adom, filter, limit, offset, detail_level)
        return json.dumps(result, indent=2)

    @mcp.tool()
    async def faz_get_events(
        device_id: str,
        filter: Optional[str] = None,
        limit: int = 1000,
        offset: int = 0,
        time_from: Optional[str | int] = None,
        time_to: Optional[str | int] = None,
        timezone: Optional[str] = None,
        adom: Optional[str] = None,
    ) -> str:
        """List security events on a FortiAnalyzer.

        Args:
            device_id: ID of the FortiAnalyzer instance from config.
            filter: FortiAnalyzer alert filter expression string.
            limit: Maximum alerts to return (default 1000).
            offset: Pagination offset.
            time_from: Optional RFC 3339 date-time or Unix timestamp.
            time_to: Optional RFC 3339 date-time or Unix timestamp.
            timezone: Optional FortiAnalyzer timezone name or index.
            adom: ADOM name (uses default from config if not specified).
        """
        c = get_client(device_id)
        await c.login()
        result = await c.get_events(
            adom, filter, limit, offset, time_from, time_to, timezone
        )
        return json.dumps(result, indent=2)

    @mcp.tool()
    async def faz_get_event_handlers(
        device_id: str,
        alert_ids: list[str],
        rule_id: Optional[str] = None,
        adom: Optional[str] = None,
    ) -> str:
        """Get event-handler filters associated with specific alert IDs.

        Args:
            device_id: ID of the FortiAnalyzer instance from config.
            alert_ids: Alert IDs required by the v8 alertfilter endpoint.
            rule_id: Optional handler rule ID.
            adom: ADOM name (uses default from config if not specified).
        """
        c = get_client(device_id)
        await c.login()
        result = await c.get_event_handlers(alert_ids, adom, rule_id)
        return json.dumps(result, indent=2)

    # ── FortiView / Statistics ───────────────────────────────────────────────

    @mcp.tool()
    async def faz_get_traffic_summary(
        device_id: str,
        device: str | list[dict] = "All_FortiGate",
        adom: Optional[str] = None,
    ) -> str:
        """Get official v8 log statistics for selected devices.

        Args:
            device_id: ID of the FortiAnalyzer instance from config.
            device: All-device ID or list of official device selector objects.
            adom: ADOM name (uses default from config if not specified).
        """
        c = get_client(device_id)
        await c.login()
        result = await c.get_traffic_summary(adom, device)
        return json.dumps(result, indent=2)

    @mcp.tool()
    async def faz_get_threat_summary(
        device_id: str,
        time_from: str | int,
        time_to: str | int,
        limit: int = 1000,
        adom: Optional[str] = None,
    ) -> str:
        """Start the official v8 top-threats FortiView task.

        Args:
            device_id: ID of the FortiAnalyzer instance from config.
            time_from: RFC 3339 date-time or Unix timestamp.
            time_to: RFC 3339 date-time or Unix timestamp.
            limit: Maximum rows requested from the task.
            adom: ADOM name (uses default from config if not specified).
        """
        c = get_client(device_id)
        await c.login()
        result = await c.get_top_threats(time_from, time_to, adom, limit)
        return json.dumps(result, indent=2)

    @mcp.tool()
    async def faz_start_fortiview(
        device_id: str,
        view_name: str,
        time_from: str | int,
        time_to: str | int,
        device: Optional[str | list[dict]] = None,
        filter: Optional[str] = None,
        limit: int = 1000,
        offset: int = 0,
        timezone: Optional[str] = None,
        adom: Optional[str] = None,
    ) -> str:
        """Start any documented v8 FortiView task and return its task ID."""
        result = await get_client(device_id).start_fortiview(
            view_name,
            time_from,
            time_to,
            adom,
            device,
            filter,
            limit,
            offset,
            timezone,
        )
        return json.dumps(result, indent=2)

    @mcp.tool()
    async def faz_get_fortiview_results(
        device_id: str,
        view_name: str,
        task_id: int,
        adom: Optional[str] = None,
    ) -> str:
        """Poll results from a v8 FortiView task."""
        result = await get_client(device_id).get_fortiview_results(view_name, task_id, adom)
        return json.dumps(result, indent=2)

    @mcp.tool()
    async def faz_delete_fortiview(
        device_id: str,
        view_name: str,
        task_id: int,
        adom: Optional[str] = None,
    ) -> str:
        """Delete a completed v8 FortiView task."""
        result = await get_client(device_id).delete_fortiview(view_name, task_id, adom)
        return json.dumps(result, indent=2)

    @mcp.tool()
    async def faz_get_top_sources(
        device_id: str,
        time_from: str | int,
        time_to: str | int,
        limit: int = 20,
        adom: Optional[str] = None,
    ) -> str:
        """Start the official v8 top-sources FortiView task.

        Args:
            device_id: ID of the FortiAnalyzer instance from config.
            time_from: RFC 3339 date-time or Unix timestamp.
            time_to: RFC 3339 date-time or Unix timestamp.
            limit: Number of top entries to return (default 20).
            adom: ADOM name (uses default from config if not specified).
        """
        c = get_client(device_id)
        await c.login()
        result = await c.get_top_sources(time_from, time_to, adom, limit)
        return json.dumps(result, indent=2)

    @mcp.tool()
    async def faz_get_top_threats(
        device_id: str,
        time_from: str | int,
        time_to: str | int,
        limit: int = 20,
        adom: Optional[str] = None,
    ) -> str:
        """Start the official v8 top-threats FortiView task.

        Args:
            device_id: ID of the FortiAnalyzer instance from config.
            time_from: RFC 3339 date-time or Unix timestamp.
            time_to: RFC 3339 date-time or Unix timestamp.
            limit: Number of top entries to return (default 20).
            adom: ADOM name (uses default from config if not specified).
        """
        c = get_client(device_id)
        await c.login()
        result = await c.get_top_threats(time_from, time_to, adom, limit)
        return json.dumps(result, indent=2)

    @mcp.tool()
    async def faz_get_top_applications(
        device_id: str,
        time_from: str | int,
        time_to: str | int,
        limit: int = 20,
        adom: Optional[str] = None,
    ) -> str:
        """Start the official v8 top-applications FortiView task.

        Args:
            device_id: ID of the FortiAnalyzer instance from config.
            time_from: RFC 3339 date-time or Unix timestamp.
            time_to: RFC 3339 date-time or Unix timestamp.
            limit: Number of top entries to return (default 20).
            adom: ADOM name (uses default from config if not specified).
        """
        c = get_client(device_id)
        await c.login()
        result = await c.get_top_applications(time_from, time_to, adom, limit)
        return json.dumps(result, indent=2)
