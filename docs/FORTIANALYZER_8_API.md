# FortiAnalyzer 8 API operations

This implementation was checked against the official FortiAnalyzer 8.0.0
OpenAPI 3.0 export. The source document describes 1,185 JSON-RPC operations
across 423 distinct API URLs. Every operation is sent as an HTTP `POST` to
`/jsonrpc`; the operation's own action and resource are carried in the JSON
body as `method` and `params[].url`.

## Supported methods

| JSON-RPC method | Official operations |
|---|---:|
| `get` | 352 |
| `update` | 286 |
| `set` | 271 |
| `add` | 152 |
| `delete` | 112 |
| `exec` | 10 |
| `execute` | 2 |

`faz_api_request` and `faz_api_batch` support all seven methods. This generic
surface is how the MCP exposes the complete version-dependent API without
creating and maintaining 1,185 individual tools.

## Request shape

Use the exact request fields documented for the selected operation.

- CLI and DVM configuration operations normally use `data` for the object.
- Operational APIs frequently require fields directly beside `url` in the
  JSON-RPC parameter object. Examples include `apiver: 3`, `device`, `filter`,
  `time-range`, `limit`, `offset`, `fields`, `loadsub`, and `option`.
- Do not wrap operational parameters in `data` unless the operation schema
  explicitly defines a `data` property.
- Use `faz_api_request.params` for fields that belong directly in `params[0]`.
- Use `faz_api_request.data` only for the schema's `data` property.

Authentication is handled by the client using `exec /sys/login/user`. The
resulting session is attached to subsequent calls and renewed once if the
appliance reports an expired session.

## Log searches

FortiAnalyzer 8 log search is asynchronous:

1. Start with `add /logview/adom/<adom>/logsearch`, including `apiver: 3`, a
   device-selector array, `time-range`, and `logtype`.
2. Poll or page results with `get /logview/adom/<adom>/logsearch/<tid>`.
3. Optionally retrieve the count with
   `get /logview/adom/<adom>/logsearch/count/<tid>`.
4. Delete the completed task with
   `delete /logview/adom/<adom>/logsearch/<tid>`.

The matching MCP tools are `faz_query_logs`/`faz_search_logs`,
`faz_get_log_search_results`, `faz_get_log_search_count`, and
`faz_delete_log_search`.

## Reports

1. List templates with `get /report/adom/<adom>/template/list` and `apiver: 3`.
2. Start a report with `add /report/adom/<adom>/run`, supplying a `schedule`,
   a `schedule-param` object, or both.
3. Poll with `get /report/adom/<adom>/run/<tid>`.
4. Retrieve output with `get /report/adom/<adom>/reports/data/<tid>` and an
   output `format`, normally `PDF`.

Generated reports are listed by state using
`get /report/adom/<adom>/reports/state`; there is no v8 `reports/browse` URL.

## Incidents and alerts

- Incidents use `get /incidentmgmt/adom/<adom>/incidents`.
- Security events are represented by the v8 alerts API at
  `get /eventmgmt/adom/<adom>/alerts`.
- Alert-handler filters use
  `get /eventmgmt/adom/<adom>/alertfilter` and require an `alertid` array.

These APIs use FortiAnalyzer filter-expression strings rather than the nested
condition arrays used by some FortiManager configuration APIs.

The older `/dvm/cmd/add/device` operation is not present in the supplied 8.0.0
OpenAPI export, so the MCP does not advertise device registration as a typed v8
operation. Use only a documented DVM API through `faz_api_request` when the
target appliance exposes one.

## FortiView

FortiView is also asynchronous:

1. Start with `add /fortiview/adom/<adom>/<view-name>/run`, including
   `apiver: 3` and `time-range`.
2. Poll with `get /fortiview/adom/<adom>/<view-name>/run/<tid>`.
3. Delete with `delete /fortiview/adom/<adom>/<view-name>/run/<tid>`.

The official view names include `top-sources`, `top-threats`, and
`top-applications`. The old `/fortiview/.../browse` approach is not present in
the FortiAnalyzer 8.0.0 OpenAPI export.
