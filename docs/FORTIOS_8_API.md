# FortiOS 8 API operations

This implementation was checked against the attached FortiOS 8 CMDB Swagger
export at `FortiOS_8.0_API_config_merged_all.yaml`. Although it was described
in the request as OpenAPI 3.0, the file itself declares `swagger: '2.0'`.

The supplied export describes 1,562 CMDB paths and 2,984 HTTP operations under
`/api/v2/cmdb`.

## Supported methods

| HTTP method | Official operations |
|---|---:|
| `get` | 1,360 |
| `post` | 616 |
| `put` | 596 |
| `delete` | 412 |

`fgt_api_request` and `fgt_api_batch` support all four documented REST
methods. This generic surface is how the MCP exposes the complete
version-dependent FortiOS REST API without creating and maintaining thousands
of individual tools.

## Request shape

Use the exact request fields documented for the selected endpoint.

- Use `fgt_api_request.path` with the full FortiGate REST path beginning with
  `/api/v2/`.
- Use `fgt_api_request.params` for query parameters such as `vdom`, `filter`,
  `start`, `count`, `scope`, or action controls.
- Use `fgt_api_request.data` only for the JSON body required by `post` and
  `put` operations.
- The client injects the configured default `vdom` automatically unless the
  request already supplies one.
- Session endpoints such as `/logincheck` and `/logout` are intentionally not
  exposed through the generic tool.

Authentication is handled by the client using either the configured API key or
FortiGate session login. Session-authenticated requests retry once on `401` or
`403` by re-establishing the session automatically.

## Typed coverage versus generic coverage

The attached Swagger file covers the configuration CMDB surface. The MCP keeps
a typed FortiGate toolset for common operational tasks such as:

- system status and resource usage
- interface inventory and configuration backup
- firewall policy, address, address-group, service, and service-group changes
- static routes, BGP, and routing table inspection
- IPsec and SSL-VPN inspection and configuration
- sessions, FortiView statistics, threat feeds, and disk logs

The generic `fgt_api_request` tool covers the remaining documented FortiOS 8
REST endpoints that do not have a dedicated typed tool.

## Verified common paths

The current typed FortiGate configuration tools align with documented paths in
the supplied FortiOS 8 export, including:

- `/api/v2/cmdb/firewall/policy`
- `/api/v2/cmdb/firewall/address`
- `/api/v2/cmdb/firewall/addrgrp`
- `/api/v2/cmdb/firewall.service/custom`
- `/api/v2/cmdb/firewall.service/group`
- `/api/v2/cmdb/router/static`
- `/api/v2/cmdb/system/interface`
- `/api/v2/cmdb/vpn.ipsec/phase1-interface`
- `/api/v2/cmdb/vpn.ssl/settings`

Operational monitor and log endpoints such as `/api/v2/monitor/...` and
`/api/v2/log/...` are outside the attached CMDB Swagger export, but they remain
supported by the MCP because they are part of the FortiGate REST API surface
used by the existing operational tools.
