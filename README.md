# Fortinet MCP Server

MCP server for managing **FortiGate**, **FortiManager**, and **FortiAnalyzer** via their REST/JSON-RPC APIs. Supports multiple instances of each product, configured via a single YAML file.

## Quick start

```bash
# 1. Copy and fill in the example config
cp config.example.yaml config.yaml
$EDITOR config.yaml

# 2. Build and start
docker compose up -d

# 3. Verify
curl http://localhost:8000/health
```

## Configuration

Edit `config.yaml` to describe your Fortinet inventory. Each device entry needs an `id` (used as the `device_id` argument in every tool call).

**FortiGate** authentication: supply either `api_key` (preferred) or `username` + `password`.

**FortiManager / FortiAnalyzer** authentication: `username` + `password` (JSON-RPC session auth).

```yaml
fortigates:
  - id: fgt-hq
    name: "HQ FortiGate"
    host: "192.168.1.1"
    api_key: "${FGT_HQ_API_KEY}"   # resolved from environment at startup
    verify_ssl: false
    vdom: "root"

fortimanagers:
  - id: fmg-01
    host: "192.168.1.10"
    username: "admin"
    password: "${FMG_01_PASSWORD}"
    verify_ssl: false

fortianalyzers:
  - id: faz-01
    host: "192.168.1.20"
    username: "admin"
    password: "${FAZ_01_PASSWORD}"
    verify_ssl: false
```

Any string value in the config supports `${ENV_VAR}` substitution. The server resolves these at startup — the actual secrets never need to be written to disk.

Pass them to Docker via an env file:
```bash
# .env  (add to .gitignore)
FGT_HQ_API_KEY=xxxxxxxxxxxx
FMG_01_PASSWORD=s3cr3t
FAZ_01_PASSWORD=s3cr3t
```
```yaml
# docker-compose.yml
env_file: .env
```

## Claude Desktop integration

Add to `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "fortinet": {
      "url": "http://localhost:8000/mcp"
    }
  }
}
```

Or for **stdio mode** (no Docker required):

```json
{
  "mcpServers": {
    "fortinet": {
      "command": "python",
      "args": ["src/server.py"],
      "env": {
        "MCP_TRANSPORT": "stdio",
        "CONFIG_PATH": "/path/to/config.yaml"
      }
    }
  }
}
```

## Environment variables

| Variable | Default | Description |
|---|---|---|
| `CONFIG_PATH` | `config.yaml` | Path to device config file |
| `MCP_TRANSPORT` | `streamable-http` | `streamable-http` or `stdio` |
| `MCP_HOST` | `0.0.0.0` | Bind address (HTTP mode only) |
| `MCP_PORT` | `8000` | Listen port (HTTP mode only) |
| `LOG_LEVEL` | `INFO` | Logging level |

## Available tools

### General (all product types)
| Tool | Description |
|---|---|
| `fgt_list_devices` | List configured FortiGate device IDs |
| `fmg_list_devices` | List configured FortiManager instance IDs |
| `faz_list_devices` | List configured FortiAnalyzer instance IDs |

### FortiGate (prefix `fgt_`)
| Tool | Description |
|---|---|
| `fgt_get_system_status` | Firmware, serial, uptime |
| `fgt_get_system_resources` | CPU and memory usage |
| `fgt_get_interfaces` | Network interfaces |
| `fgt_backup_config` | Download full config backup |
| `fgt_execute_cli` | Run CLI commands |
| `fgt_get_ha_status` | HA cluster status |
| `fgt_get_firewall_policies` | List/get firewall policies |
| `fgt_create_firewall_policy` | Create policy |
| `fgt_update_firewall_policy` | Update policy |
| `fgt_delete_firewall_policy` | Delete policy |
| `fgt_get_address_objects` | List address objects |
| `fgt_create_address_object` | Create address object |
| `fgt_update_address_object` | Update address object |
| `fgt_delete_address_object` | Delete address object |
| `fgt_get_address_groups` | List address groups |
| `fgt_create_address_group` | Create address group |
| `fgt_get_service_objects` | List services |
| `fgt_create_service_object` | Create service |
| `fgt_get_static_routes` | List static routes |
| `fgt_create_static_route` | Create static route |
| `fgt_delete_static_route` | Delete static route |
| `fgt_get_routing_table` | Active routing table |
| `fgt_get_bgp_neighbors` | BGP neighbor status |
| `fgt_get_ipsec_tunnels` | IPsec tunnel status |
| `fgt_get_ipsec_phase1_config` | IPsec phase1 config |
| `fgt_create_ipsec_phase1` | Create IPsec phase1 |
| `fgt_get_ssl_vpn_sessions` | Active SSL-VPN sessions |
| `fgt_get_active_sessions` | Active firewall sessions |
| `fgt_get_session_stats` | Session table statistics |
| `fgt_get_logs` | Retrieve disk logs |

### FortiManager (prefix `fmg_`)
| Tool | Description |
|---|---|
| `fmg_get_system_status` | Version, serial, uptime |
| `fmg_get_adoms` | List ADOMs |
| `fmg_get_managed_devices` | List managed FortiGates |
| `fmg_get_device_detail` | Details for one device |
| `fmg_add_device` | Add/import device |
| `fmg_delete_device` | Remove device |
| `fmg_get_unregistered_devices` | Devices pending auth |
| `fmg_set_device_metadata` | Set ZTP metadata variables |
| `fmg_get_policy_packages` | List policy packages |
| `fmg_create_policy_package` | Create policy package |
| `fmg_install_policy_package` | Push package to devices |
| `fmg_install_device_config` | Push device-level config |
| `fmg_get_firewall_policies` | List policies in package |
| `fmg_create_firewall_policy` | Create policy |
| `fmg_update_firewall_policy` | Update policy |
| `fmg_delete_firewall_policy` | Delete policy |
| `fmg_get_address_objects` | ADOM address objects |
| `fmg_create_address_object` | Create address object |
| `fmg_update_address_object` | Update address object |
| `fmg_delete_address_object` | Delete address object |
| `fmg_get_address_groups` | ADOM address groups |
| `fmg_create_address_group` | Create address group |
| `fmg_get_service_objects` | ADOM service objects |
| `fmg_create_service_object` | Create service object |
| `fmg_get_scripts` | List CLI scripts |
| `fmg_create_script` | Create CLI script |
| `fmg_run_script` | Execute script on devices |
| `fmg_get_task_status` | Get task status |
| `fmg_get_tasks` | List recent tasks |
| `fmg_wait_for_task` | Poll task to completion |

### FortiAnalyzer (prefix `faz_`)
| Tool | Description |
|---|---|
| `faz_api_request` | Call any documented v8 JSON-RPC method and URL |
| `faz_api_batch` | Run up to 50 ordered v8 JSON-RPC operations |
| `faz_get_system_status` | Version, serial, disk usage |
| `faz_get_adoms` | List ADOMs |
| `faz_get_registered_devices` | List log-sending devices |
| `faz_get_device_groups` | List device groups |
| `faz_register_device` | Register a new device |
| `faz_query_logs` | Query logs with filters |
| `faz_get_log_fields` | Available log fields |
| `faz_search_logs` | Start async log search |
| `faz_get_reports` | List generated reports |
| `faz_get_report_templates` | List report templates |
| `faz_run_report` | Generate a report |
| `faz_get_report_status` | Check report task status |
| `faz_download_report` | Download a completed report |
| `faz_get_incidents` | List security incidents |
| `faz_get_events` | List security events |
| `faz_get_event_handlers` | List event alert handlers |
| `faz_get_traffic_summary` | Traffic statistics |
| `faz_get_threat_summary` | Threat statistics |
| `faz_get_top_sources` | Top source IPs |
| `faz_get_top_threats` | Top detected threats |
| `faz_get_top_applications` | Top applications by traffic |

#### Full FortiAnalyzer v8 API coverage

FortiAnalyzer exposes a large, version-dependent JSON-RPC URL tree. The typed
tools above cover common system, device, log, report, incident, event, and
FortiView operations. `faz_api_request` provides access to the rest of the
documented v8 API without requiring a new MCP release for every endpoint.

The tool accepts all FortiAnalyzer JSON-RPC methods supported by this server:
`get`, `add`, `set`, `update`, `delete`, and `exec`. The `url` must be a
documented absolute API path. Put the endpoint body in `data`; put JSON-RPC
controls such as `filter`, `fields`, `option`, `loadsub`, `range`, `sortings`,
`target`, and `flags` in `params`.

Example read:

```json
{
  "device_id": "faz-01",
  "method": "get",
  "url": "/dvmdb/adom/root/device",
  "params": {
    "fields": ["name", "ip", "sn"],
    "range": [0, 99]
  }
}
```

Example configuration operation:

```json
{
  "device_id": "faz-01",
  "method": "update",
  "url": "/documented/v8/api/path/object-name",
  "data": {
    "description": "Managed through Fortinet MCP"
  }
}
```

`faz_api_batch` accepts the same fields as an array named `requests`, executes
them in order, and stops on the first API error. It is intentionally not
described as atomic because FortiAnalyzer does not roll back completed calls.

Login and logout URLs are reserved: the client creates, renews, and closes the
JSON-RPC session itself. API errors are raised with the FortiAnalyzer status
code and message rather than being returned as successful MCP results.

## Security notes

- Store credentials in `config.yaml` with restrictive permissions (`chmod 600 config.yaml`)
- Use Docker secrets or environment variable injection for production deployments
- The MCP server HTTP endpoint has no built-in authentication — place it behind a reverse proxy with auth if exposed beyond localhost
- Set `verify_ssl: true` and provision proper certs for production Fortinet devices
