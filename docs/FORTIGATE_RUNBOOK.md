# FortiGate Runbook

This runbook covers the FortiGate MCP tools used for day-to-day FortiOS
operations. Use `fgt_list_devices` first to discover available `device_id`
values.

## Tool Families

- Typed tools: common operational and configuration workflows.
- Domain suites:
  `fgt_cmdb_request`/`batch`,
  `fgt_monitor_request`/`batch`,
  `fgt_log_request`/`batch`,
  `fgt_service_request`/`batch`
- Full REST suite:
  `fgt_api_request`/`batch`

Prefer typed tools for routine work. Prefer a domain suite when the endpoint
belongs clearly to one FortiOS API area. Use `fgt_api_request` only when the
request must cross domains or when the exact full path already comes from the
official API reference.

## Configuration Workflows

### Read a CMDB object

```json
{
  "device_id": "fgt-primary",
  "method": "get",
  "path": "firewall/address",
  "params": {
    "filter": "name==web-server"
  }
}
```

Use with `fgt_cmdb_request`.

### Update a CMDB object

```json
{
  "device_id": "fgt-primary",
  "method": "put",
  "path": "firewall/address/web-server",
  "data": {
    "comment": "Managed by MCP"
  }
}
```

### Batch related configuration reads

```json
{
  "device_id": "fgt-primary",
  "requests": [
    {"method": "get", "path": "firewall/address"},
    {"method": "get", "path": "firewall/addrgrp"},
    {"method": "get", "path": "firewall.service/custom"}
  ]
}
```

Use with `fgt_cmdb_batch`. Batches are ordered but not atomic.

## Monitoring Workflows

### System status

Use `fgt_get_system_status` for the usual health check.

For a raw monitor endpoint:

```json
{
  "device_id": "fgt-primary",
  "method": "get",
  "path": "system/status"
}
```

Use with `fgt_monitor_request`.

### Sessions and routing

- `fgt_get_active_sessions`
- `fgt_get_session_stats`
- `fgt_get_routing_table`
- `fgt_get_bgp_neighbors`
- `fgt_get_ipsec_tunnels`
- `fgt_get_ssl_vpn_sessions`

For endpoints without a typed wrapper, use `fgt_monitor_request`.

## Log Workflows

### Read disk logs

Use `fgt_get_logs` for the common path.

Equivalent raw request:

```json
{
  "device_id": "fgt-primary",
  "method": "get",
  "path": "disk/traffic",
  "params": {
    "subtype": "forward",
    "rows": 100
  }
}
```

Use with `fgt_log_request`.

## Service Workflows

The service domain is available through `fgt_service_request` and
`fgt_service_batch` for FortiOS endpoints documented under `/api/v2/service/`.
These are narrower and easier to prompt than the all-path `fgt_api_request`
tool.

```json
{
  "device_id": "fgt-primary",
  "method": "get",
  "path": "some/service/path"
}
```

Replace `some/service/path` with the documented FortiOS service path from the
official API reference.

## Typed FortiGate Changes

Common write-capable typed tools include:

- `fgt_create_firewall_policy`
- `fgt_update_firewall_policy`
- `fgt_delete_firewall_policy`
- `fgt_move_firewall_policy`
- `fgt_create_address_object`
- `fgt_update_address_object`
- `fgt_delete_address_object`
- `fgt_create_address_group`
- `fgt_update_address_group`
- `fgt_delete_address_group`
- `fgt_create_service_object`
- `fgt_update_service_object`
- `fgt_delete_service_object`
- `fgt_create_service_group`
- `fgt_update_service_group`
- `fgt_delete_service_group`
- `fgt_create_static_route`
- `fgt_update_static_route`
- `fgt_delete_static_route`
- `fgt_create_ipsec_phase1`
- `fgt_update_ipsec_phase1`
- `fgt_delete_ipsec_phase1`
- `fgt_execute_cli`

Read current state before using these tools and capture rollback information in
the change record.

## VDOM Behavior

FortiGate requests automatically include the configured default `vdom` unless:

- the endpoint does not use VDOM scope, or
- the request explicitly provides a `vdom` query parameter

This applies to `fgt_api_request` and the domain-scoped request tools.

## Safety Notes

- `fgt_api_batch`, `fgt_cmdb_batch`, `fgt_monitor_batch`, `fgt_log_batch`, and
  `fgt_service_batch` stop on the first API error and do not roll back earlier
  operations.
- `fgt_execute_cli` should be treated as a high-risk change tool.
- The attached FortiOS 8 Swagger file documents the CMDB surface only. Monitor,
  log, and service coverage comes from the broader FortiGate `/api/v2` REST API
  surface.
