# Security Guide

## Security Model

The server authenticates to Fortinet appliances. It does not authenticate MCP
clients connecting to its streamable HTTP endpoint. Anyone able to invoke the
MCP tools can exercise the permissions of the configured appliance accounts.

Treat access to the MCP endpoint as privileged network-management access.

## Production Checklist

- Bind to `127.0.0.1` or a dedicated management interface.
- Put remote access behind an authenticated TLS reverse proxy.
- Restrict source networks with host and network firewalls.
- Use individual, least-privilege appliance service accounts.
- Prefer FortiGate API keys over reusable administrator passwords.
- Restrict FortiManager and FortiAnalyzer accounts to required ADOMs.
- Enable `verify_ssl: true` and trust the issuing CA.
- Keep `.env` and `config.yaml` outside version control and ordinary logs.
- Rotate credentials on a defined schedule and after suspected exposure.
- Review write operations and retain appliance task/audit records.
- Back up appliance configuration before broad automation changes.

## Least Privilege

Separate read-only and change-capable deployments when possible. A monitoring
client does not need firewall-policy writes, script execution, installs, or
generic FortiAnalyzer mutation access.

FortiAnalyzer `faz_api_request` is intentionally broad. The server validates the
JSON-RPC method and URL form, but authorization is enforced by the appliance.
Use an account whose profile prevents unapproved API modules and ADOM access.

## Secret Handling

Reference secrets through environment variables:

```yaml
password: "${FAZ_PRIMARY_PASSWORD}"
```

Do not:

- Commit `.env` or `config.yaml`.
- Put credentials in command arguments recorded by shell history.
- Include sessions or passwords in MCP prompts, tickets, or test fixtures.
- Store production secrets in container images.
- Print raw HTTP request headers or login payloads while debugging.

For production, inject secrets from the platform's secret manager rather than a
long-lived `.env` file.

## TLS

`verify_ssl: false` disables certificate-chain and hostname verification. This
permits interception and appliance impersonation. Use it only in an isolated
lab while certificates are being established.

Production appliances should use certificates issued by a trusted internal or
public CA. Ensure the configured `host` matches the certificate identity.

## High-Risk Tools

High-risk categories include:

- FortiGate CLI execution and all create/update/delete tools
- FortiManager device deletion, scripts, installs, and policy changes
- FortiAnalyzer generic API calls, batches, and any add/set/update/delete/exec/
  execute operation

Require a current-state read, explicit target confirmation, change record,
rollback plan, and post-change verification.

## Network Exposure

The default Compose mapping publishes port 8000 on all host interfaces. For a
local-only deployment, change it to:

```yaml
ports:
  - "127.0.0.1:8000:8000"
```

When using a reverse proxy, authenticate every client and prevent direct access
to the backend port.

## Audit and Incident Response

Correlate MCP use with Fortinet administrator, task, configuration revision,
and event logs. Preserve:

- Time and initiating user
- MCP tool name and non-secret arguments
- Device ID, VDOM or ADOM
- Fortinet task ID or revision
- Pre-change and post-change state

If credentials may be exposed, isolate the MCP endpoint, rotate appliance
credentials, restart the service to clear in-memory sessions, review appliance
audit logs, and inspect recent configuration changes.
