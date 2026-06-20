# Fortinet MCP Server

An MCP server for operating Fortinet FortiGate, FortiManager, and
FortiAnalyzer systems through their supported REST and JSON-RPC APIs.

The server supports multiple appliances of each product type and registers
tools only for product types present in `config.yaml`.

## Capabilities

| Product | Tools | API style | Primary capabilities |
|---|---:|---|---|
| FortiGate | 56 | REST API | Configuration, monitoring, log, service, and typed operational access |
| FortiManager | 31 | JSON-RPC | Devices, policy packages, objects, scripts, installs, tasks |
| FortiAnalyzer | 29 | JSON-RPC | Logs, reports, incidents, alerts, FortiView, complete v8 access |

FortiGate 8 coverage includes typed operational tools, full REST access through
`fgt_api_request` / `fgt_api_batch`, and domain suites for configuration,
monitoring, log, and service endpoints through `fgt_cmdb_*`,
`fgt_monitor_*`, `fgt_log_*`, and `fgt_service_*`.

FortiAnalyzer 8 coverage includes typed operational tools and generic
`faz_api_request` / `faz_api_batch` tools for every operation described by the
official 8.0.0 OpenAPI export.

## Quick Start

Prerequisites: Docker Engine with Compose v2, network access to the Fortinet
appliances, and API credentials with the minimum required permissions.

```bash
git clone http://10.0.0.250:3052/codex-git/fortinet-mcp.git
cd fortinet-mcp
cp config.example.yaml config.yaml
cp .env.example .env
```

Edit `config.yaml` and `.env`, then start the service:

```bash
docker compose up -d --build
docker compose ps
docker compose logs --tail=100 fortinet-mcp
```

The container publishes the streamable HTTP MCP endpoint at:

```text
http://localhost:8000/mcp
```

Confirm that Docker reports the container as healthy:

```bash
docker inspect --format '{{.State.Health.Status}}' fortinet-mcp
```

## MCP Client Configuration

For clients that accept a remote streamable HTTP MCP server:

```json
{
  "mcpServers": {
    "fortinet": {
      "url": "http://localhost:8000/mcp"
    }
  }
}
```

For clients that launch an MCP server over stdio:

```json
{
  "mcpServers": {
    "fortinet": {
      "command": "python",
      "args": ["/path/to/fortinet-mcp/src/server.py"],
      "env": {
        "PYTHONPATH": "/path/to/fortinet-mcp/src",
        "MCP_TRANSPORT": "stdio",
        "CONFIG_PATH": "/path/to/fortinet-mcp/config.yaml"
      }
    }
  }
}
```

Use `fgt_list_devices`, `fmg_list_devices`, or `faz_list_devices` first. Every
other tool requires a configured `device_id`.

## Configuration

Secrets may be referenced from YAML with `${ENV_VAR}`. Docker Compose loads
those variables from `.env`; local runs inherit them from the process
environment.

```yaml
fortianalyzers:
  - id: faz-primary
    name: "Primary FortiAnalyzer"
    host: "192.168.1.20"
    port: 443
    username: "mcp-api"
    password: "${FAZ_PRIMARY_PASSWORD}"
    verify_ssl: true
    adom: "root"
```

See [Configuration](docs/CONFIGURATION.md) for every field, authentication
guidance, certificates, and multi-appliance examples.

## Documentation

- [Documentation index](docs/INDEX.md)
- [Installation and deployment](docs/INSTALLATION.md)
- [Configuration reference](docs/CONFIGURATION.md)
- [Operations guide](docs/OPERATIONS.md)
- [FortiGate operational runbook](docs/FORTIGATE_RUNBOOK.md)
- [FortiAnalyzer operational runbook](docs/FORTIANALYZER_RUNBOOK.md)
- [FortiOS 8 API contract](docs/FORTIOS_8_API.md)
- [Complete tool reference](docs/TOOL_REFERENCE.md)
- [Security guide](docs/SECURITY.md)
- [Troubleshooting](docs/TROUBLESHOOTING.md)
- [Development and testing](docs/DEVELOPMENT.md)
- [FortiAnalyzer 8 API contract](docs/FORTIANALYZER_8_API.md)
- [Agent instructions](AGENT.md)

## Runtime Environment

| Variable | Default | Purpose |
|---|---|---|
| `CONFIG_PATH` | `config.yaml` | YAML inventory path |
| `MCP_TRANSPORT` | `streamable-http` | `streamable-http` or `stdio` |
| `MCP_HOST` | `0.0.0.0` | HTTP bind address |
| `MCP_PORT` | `8000` | HTTP bind port |
| `LOG_LEVEL` | `INFO` | Python logging level |

## Safety

Many tools change production network configuration. Read operations should be
used to establish current state before writes. Treat create, update, delete,
install, script, CLI, generic API, and batch operations as change-controlled
actions. The MCP HTTP endpoint has no built-in client authentication; bind it
to a trusted interface or place it behind an authenticated reverse proxy.

See [Security](docs/SECURITY.md) for the production checklist.
