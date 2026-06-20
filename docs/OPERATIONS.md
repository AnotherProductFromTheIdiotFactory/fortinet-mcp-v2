# Operations Guide

## Daily Checks

```bash
docker compose ps
docker inspect --format '{{.State.Health.Status}}' fortinet-mcp
docker compose logs --since=24h fortinet-mcp
```

From an MCP client:

1. Read `fortinet://health`.
2. Run the relevant `*_list_devices` tool.
3. Run read-only system-status tools for critical appliances.
4. Investigate repeated login, timeout, TLS, or API status errors.

Container health only confirms that the listener accepts TCP connections. It
does not confirm appliance reachability or credential validity.

## Start, Stop, and Restart

```bash
docker compose up -d
docker compose stop
docker compose start
docker compose restart fortinet-mcp
```

Configuration is loaded at process startup. Restart after changing
`config.yaml`, `.env`, or runtime environment variables.

## Logs

```bash
docker compose logs -f fortinet-mcp
docker compose logs --since=30m --tail=500 fortinet-mcp
```

Expected startup messages include the number of configured FortiGate,
FortiManager, and FortiAnalyzer systems and which tool groups were registered.

Do not paste logs into tickets before checking for hostnames, device names,
policy data, or other sensitive operational context.

## Change Procedure

For any write operation:

1. Identify the exact `device_id`, VDOM or ADOM, and target object.
2. Read current state using the corresponding get/list tool.
3. Record the intended change and rollback data.
4. Execute one narrowly scoped change.
5. Poll any returned FortiManager or FortiAnalyzer task to completion.
6. Read state again and verify the expected result.
7. Record the Fortinet task ID and MCP tool arguments in the change record.

Do not place independent changes into `faz_api_batch` merely for convenience.
The batch is ordered but not atomic and does not roll back earlier operations.
The same warning applies to `fgt_api_batch` for FortiGate REST changes.

## Backup and Recovery

Before upgrades or broad changes, preserve:

- `config.yaml` with access controls intact
- The set of environment variable names, but not secrets in ordinary backups
- Reverse proxy and service configuration
- The deployed image tag or Git commit
- Appliance-native configuration backups

FortiGate configuration can be retrieved with `fgt_backup_config`. FortiManager
and FortiAnalyzer should also be backed up using their supported appliance
procedures; the MCP server is not a substitute for platform backups.

For FortiGate workflow examples and the domain-scoped request tools, see
`docs/FORTIGATE_RUNBOOK.md`.

## Upgrade

```bash
git fetch --all --prune
git checkout <approved-tag-or-commit>
docker compose build --pull
docker compose up -d
docker compose ps
docker compose logs --tail=100 fortinet-mcp
```

After upgrade, repeat read-only smoke tests. Review release changes for renamed
tools or changed schemas before allowing automation clients to reconnect.

## Rollback

```bash
git checkout <previous-approved-tag-or-commit>
docker compose up -d --build
```

Restore the previous inventory only if its schema changed. Verify health and
read-only appliance access before resuming writes.

## Credential Rotation

1. Create or rotate the credential on the Fortinet appliance.
2. Update the secret store or `.env` without editing `config.yaml` when the
   environment variable name remains unchanged.
3. Restart the MCP service.
4. Test list/status tools.
5. Revoke the previous credential.

FortiManager and FortiAnalyzer sessions are in memory and disappear on restart.

## Shutdown During Tasks

Stopping the MCP process does not necessarily cancel a task already created on
FortiManager or FortiAnalyzer. Record task IDs, restart the MCP service, and use
the product's task-status tool or generic API request to inspect the appliance.

For FortiAnalyzer log-search and FortiView tasks, delete completed task objects
using the matching cleanup tool.
