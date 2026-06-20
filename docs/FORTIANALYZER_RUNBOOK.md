# FortiAnalyzer Operational Runbook

This runbook applies to the FortiAnalyzer 8.0 JSON-RPC implementation.

## Preconditions

1. Confirm the appliance with `faz_list_devices`.
2. Confirm access with `faz_get_system_status`.
3. Confirm the intended ADOM with `faz_get_adoms`.
4. Use RFC 3339 times with a timezone, preferably UTC (`Z`).
5. Use the appliance's official filter expression syntax.

The configured ADOM is used when a tool's `adom` argument is omitted.

## Inventory

Recommended read-only sequence:

```text
faz_list_devices
faz_get_system_status(device_id="faz-primary")
faz_get_adoms(device_id="faz-primary")
faz_get_registered_devices(device_id="faz-primary", adom="root")
faz_get_device_groups(device_id="faz-primary", adom="root")
```

## Log Search

Log search is asynchronous.

### 1. Discover fields

```json
{
  "device_id": "faz-primary",
  "log_type": "traffic",
  "device_type": "FortiGate",
  "adom": "root"
}
```

Call `faz_get_log_fields` with this object.

### 2. Start search

Call `faz_query_logs` or the equivalent `faz_search_logs`:

```json
{
  "device_id": "faz-primary",
  "adom": "root",
  "time_from": "2026-06-19T00:00:00Z",
  "time_to": "2026-06-20T00:00:00Z",
  "log_type": "traffic",
  "device": "All_FortiGate",
  "filter": "action='deny'",
  "limit": 100
}
```

Record the returned task ID (`tid`).

### 3. Poll and page

```json
{
  "device_id": "faz-primary",
  "task_id": 42,
  "limit": 50,
  "offset": 0,
  "adom": "root"
}
```

Call `faz_get_log_search_results`. Use `faz_get_log_search_count` when the total
is needed. Increase `offset` to retrieve additional pages.

### 4. Clean up

Call `faz_delete_log_search` with the task ID after results have been consumed.

## Reports

### Discover templates and reports

```text
faz_get_report_templates(device_id="faz-primary", device_type="fgt", language="en")
faz_get_reports(device_id="faz-primary", state="finished")
```

Use the state value supported by the target appliance.

### Start a report

Run an existing schedule:

```json
{
  "device_id": "faz-primary",
  "schedule": "Daily Security Summary",
  "adom": "root"
}
```

Or provide the official `schedule-param` object:

```json
{
  "device_id": "faz-primary",
  "adom": "root",
  "schedule_params": {
    "layout-id": 12,
    "device": "All_FortiGate",
    "time-period": "last-n-days",
    "period-last-n": 1,
    "timezone": "UTC"
  }
}
```

The exact schedule fields are version-dependent. Confirm them in the official
API reference before using a generic schedule object.

Poll `faz_get_report_status`, then retrieve the completed output:

```json
{
  "device_id": "faz-primary",
  "task_id": 77,
  "report_format": "PDF",
  "adom": "root"
}
```

Call `faz_download_report`. The JSON-RPC response may contain encoded or
appliance-specific output metadata; the MCP does not write files automatically.

## Incidents and Alerts

List incidents:

```json
{
  "device_id": "faz-primary",
  "adom": "root",
  "filter": "status='Open'",
  "limit": 50,
  "offset": 0
}
```

List security alerts through `faz_get_events`:

```json
{
  "device_id": "faz-primary",
  "adom": "root",
  "filter": "severity='high'",
  "time_from": "2026-06-19T00:00:00Z",
  "time_to": "2026-06-20T00:00:00Z",
  "timezone": "UTC",
  "limit": 100
}
```

Retrieve handler filters for known alerts:

```json
{
  "device_id": "faz-primary",
  "alert_ids": ["12345", "12346"],
  "adom": "root"
}
```

## FortiView

FortiView is asynchronous. Convenience tools start `top-sources`,
`top-threats`, and `top-applications` tasks. Use `faz_start_fortiview` for any
view documented by the target release.

```json
{
  "device_id": "faz-primary",
  "view_name": "top-sources",
  "time_from": "2026-06-19T00:00:00Z",
  "time_to": "2026-06-20T00:00:00Z",
  "device": "All_FortiGate",
  "limit": 100,
  "adom": "root"
}
```

Record the task ID, poll with `faz_get_fortiview_results`, and delete with
`faz_delete_fortiview` when complete.

## Generic v8 API Calls

Use a typed tool when one matches the workflow. Use `faz_api_request` for an
official operation without a typed tool.

Read example:

```json
{
  "device_id": "faz-primary",
  "method": "get",
  "url": "/dvmdb/adom/root/device",
  "params": {
    "fields": ["name", "ip", "sn"],
    "range": [0, 99]
  }
}
```

Operational example with flattened parameters:

```json
{
  "device_id": "faz-primary",
  "method": "get",
  "url": "/logview/adom/root/logstats",
  "params": {
    "apiver": 3,
    "device": [{"devid": "All_FortiGate"}]
  }
}
```

Configuration example with `data`:

```json
{
  "device_id": "faz-primary",
  "method": "update",
  "url": "/cli/global/system/example/object-name",
  "data": {
    "description": "Managed through Fortinet MCP"
  }
}
```

Replace the example URL with a real operation from the official reference.
Never infer a URL from CLI syntax.

## Batch Operations

`faz_api_batch` executes up to 50 requests in order and stops on the first API
error. It is not transactional. Use it for related reads or a change sequence
with an independently tested rollback. Avoid mixing unrelated devices or
high-impact changes in one batch.

## Error Handling

- HTTP errors indicate connectivity, TLS, proxy, or appliance web-service issues.
- `FAZ RPC error <code>` is an appliance JSON-RPC status failure.
- An expired session is renewed once automatically.
- Repeated permission failures require an appliance role change, not a retry loop.
- Retain task IDs when a client disconnects so work can be inspected later.
