# Troubleshooting

## Container Is Unhealthy

```bash
docker compose ps
docker compose logs --tail=200 fortinet-mcp
docker inspect --format '{{json .State.Health}}' fortinet-mcp
```

The health check tests the local TCP listener. Common causes are startup
failure, invalid configuration, missing environment variables, or a port bind
failure.

## Configuration File Not Found

Typical log:

```text
Config file not found: /config/config.yaml
```

Check:

```bash
test -f config.yaml
docker compose config
docker compose exec fortinet-mcp ls -l /config/config.yaml
```

The Compose mount expects `config.yaml` in the repository root.

## Undefined Environment Variable

Startup fails when YAML contains `${NAME}` but `NAME` is absent.

```bash
grep -o '\${[^}]*}' config.yaml | sort -u
docker compose config
```

Ensure every referenced name exists in `.env` or the container environment.
Do not print the values while diagnosing.

## No Tools for a Product

Tool groups are registered only when the corresponding YAML list is non-empty.
Check startup logs and read `fortinet://health`. Restart after changing the
inventory.

## Device ID Not Found

Call the relevant list tool and use its exact `id`. The `name` and `host` are
not accepted as substitutes.

## Connection Timeout or Refused

From the MCP host:

```bash
nc -vz <appliance-host> 443
```

Check routing, DNS, management-interface policy, local-out policy, firewall
rules, API service enablement, and the configured port. A healthy MCP container
does not imply appliance connectivity.

## Certificate Verification Failure

Confirm that:

- The certificate is valid and not expired.
- Its SAN matches the configured `host`.
- The issuing CA is installed in the host or container trust store.
- Intermediate certificates are presented by the appliance.

Do not permanently resolve a production certificate problem by setting
`verify_ssl: false`.

## Authentication Failure

FortiGate:

- Confirm the API token is active and scoped correctly.
- Confirm the source IP is allowed by trusted-host settings.
- If using username/password, verify REST API authentication is permitted.

FortiManager/FortiAnalyzer:

- Confirm the JSON-RPC user and password.
- Confirm the user profile and ADOM access.
- Restart the MCP process after credential rotation.

## JSON-RPC Permission Error

An `FMG RPC error` or `FAZ RPC error` is returned by the appliance. Record the
code, message, method, URL, and ADOM, excluding secrets. Repeated permission
failures require a role/profile correction rather than retries.

## FortiAnalyzer Invalid Parameter

Check the exact 8.0 operation schema:

- Is `apiver: 3` required?
- Does the field belong directly in `params` or inside `data`?
- Is `device` an array of selector objects?
- Is `time-range` an object containing `start` and `end`?
- Is the filter a FortiAnalyzer expression string?
- Is the method `add`, `get`, `execute`, or another documented value?

See `FORTIANALYZER_8_API.md`.

## Task Never Completes

Keep the task ID and inspect it with the matching product tool. Check appliance
job queues, resource utilization, dataset size, permissions, and time range.
Avoid starting duplicate searches or reports while an equivalent task runs.

If the MCP client disconnects, the appliance task may continue.

## MCP Client Cannot Connect

Confirm transport alignment:

- Streamable HTTP client: `http://<host>:8000/mcp`
- Stdio client: launches `python src/server.py` with `MCP_TRANSPORT=stdio`

Check host binding, port publishing, reverse-proxy streaming settings, and client
authentication. `/health` is not an HTTP endpoint; health inventory is the MCP
resource `fortinet://health`.

## Collecting a Diagnostic Bundle

Collect only non-secret output:

```bash
docker compose ps
docker compose logs --since=30m fortinet-mcp
git rev-parse HEAD
docker image inspect fortinet-mcp-fortinet-mcp --format '{{.Id}}' 2>/dev/null || true
```

Redact IPs, hostnames, device names, policy content, usernames, tokens, sessions,
and passwords before sharing.
