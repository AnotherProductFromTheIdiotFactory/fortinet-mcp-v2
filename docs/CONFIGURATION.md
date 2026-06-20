# Configuration Reference

## Inventory File

`CONFIG_PATH` selects the YAML inventory. The default is `config.yaml` in the
current working directory. The Docker image sets it to `/config/config.yaml`.

Top-level keys:

```yaml
fortigates: []
fortimanagers: []
fortianalyzers: []
```

Each entry requires a unique `id`. Tools use this value as `device_id`.

## Environment Substitution

Any string value may contain `${ENV_VAR}`. Startup fails when a referenced
variable is undefined.

```yaml
password: "${FAZ_PRIMARY_PASSWORD}"
```

For Docker Compose, copy `.env.example` to `.env`. For local or stdio runs,
export variables in the launching process or configure them in the MCP client.

## FortiGate

| Field | Required | Default | Description |
|---|---|---|---|
| `id` | yes | | MCP device selector |
| `host` | yes | | Hostname or IP, without scheme |
| `name` | no | empty | Display name |
| `port` | no | `443` | HTTPS API port |
| `api_key` | one auth mode | | Preferred REST API token |
| `username` | one auth mode | | Administrator username |
| `password` | with username | | Administrator password |
| `verify_ssl` | no | `false` | Verify appliance certificate |
| `vdom` | no | `root` | Default VDOM |

Prefer a scoped REST API administrator and `api_key`. Do not configure both
authentication modes unless the product client explicitly requires it.

## FortiManager

| Field | Required | Default | Description |
|---|---|---|---|
| `id` | yes | | MCP device selector |
| `host` | yes | | Hostname or IP |
| `name` | no | empty | Display name |
| `port` | no | `443` | JSON-RPC HTTPS port |
| `username` | no | `admin` | JSON-RPC user |
| `password` | operationally yes | empty | JSON-RPC password |
| `verify_ssl` | no | `false` | Verify appliance certificate |
| `adom` | no | `root` | Default ADOM |

Use an account restricted to the ADOMs and workflows exposed through MCP.

## FortiAnalyzer

The FortiAnalyzer fields are the same as FortiManager. Authentication uses
`exec /sys/login/user`; the client stores the returned session in memory and
renews it once after an expired-session response.

```yaml
fortianalyzers:
  - id: faz-production
    name: "Production FortiAnalyzer"
    host: "faz.example.net"
    port: 443
    username: "mcp-api"
    password: "${FAZ_PRODUCTION_PASSWORD}"
    verify_ssl: true
    adom: "root"
```

FortiAnalyzer typed tools use API version 3 fields required by FortiAnalyzer
8.0 operational endpoints.

## Multiple Appliances

```yaml
fortianalyzers:
  - id: faz-emea
    host: "faz-emea.example.net"
    username: "mcp-read"
    password: "${FAZ_EMEA_PASSWORD}"
    verify_ssl: true
    adom: "emea"

  - id: faz-lab
    host: "10.20.30.40"
    username: "mcp-lab"
    password: "${FAZ_LAB_PASSWORD}"
    verify_ssl: false
    adom: "root"
```

Call `faz_list_devices` to discover the configured IDs. Names do not need to
be unique, but IDs do.

## TLS

Production configuration should use `verify_ssl: true` and a certificate whose
subject matches `host`. Install private CA certificates in the host or image
trust store. `verify_ssl: false` disables certificate and hostname validation;
reserve it for isolated lab appliances.

## Transport and Logging

```text
MCP_TRANSPORT=streamable-http | stdio
MCP_HOST=0.0.0.0
MCP_PORT=8000
LOG_LEVEL=INFO
```

Use `127.0.0.1` as `MCP_HOST` when only a local reverse proxy or client should
connect. Avoid `DEBUG` in normal production operation because upstream library
logs may include request context.

## Validation

Before deployment:

```bash
docker compose config
```

After startup, inspect the startup log for the loaded product counts and read
the MCP resource `fortinet://health`. Then call each configured product's
`*_list_devices` and a read-only status tool.
