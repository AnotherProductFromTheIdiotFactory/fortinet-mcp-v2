# Agent Instructions

This file is the working contract for coding agents modifying this repository.

## Mission

Maintain a small, predictable MCP server that maps Fortinet product APIs to
well-described tools. Prefer correctness against official product API contracts
over speculative convenience wrappers.

## Architecture

```text
src/server.py                 server construction and transport
src/config.py                 YAML inventory and environment substitution
src/clients/base.py           shared HTTP client construction
src/clients/fortigate.py      FortiGate REST client
src/clients/fortimanager.py   FortiManager JSON-RPC client
src/clients/fortianalyzer.py  FortiAnalyzer JSON-RPC v8 client
src/tools/*.py                FastMCP tool registration and schemas
tests/                        contract tests
docs/                         operator and developer documentation
```

Configuration is loaded once at startup. Tool modules keep one cached client
per configured device ID. Product tools are registered only when at least one
device of that product type exists.

## Required Invariants

- Never log, return, commit, or embed credentials, API keys, sessions, or tokens.
- Keep `config.yaml` and `.env` ignored.
- Preserve `device_id` as the MCP-side appliance selector.
- Use the existing client and tool module for the relevant product.
- Keep tool descriptions accurate enough for an agent to select safely.
- Raise Fortinet API failures as errors; do not return failed API status as a
  successful MCP response.
- Do not disable TLS verification in examples intended for production.
- Do not invent Fortinet URLs or payload shapes.

## FortiAnalyzer Rules

The official FortiAnalyzer 8.0.0 OpenAPI export is the contract.

- All appliance API calls are HTTP `POST` requests to `/jsonrpc`.
- Supported JSON-RPC methods are `get`, `add`, `set`, `update`, `delete`,
  `exec`, and `execute`.
- Operational APIs commonly require fields directly in `params[0]`, including
  `apiver: 3`, `device`, `time-range`, `filter`, `limit`, and `offset`.
- Use `data` only when the operation schema defines a `data` property.
- Log search, report generation, and FortiView use asynchronous task lifecycles.
- New typed URLs must be checked against the official OpenAPI export.
- Complete version-dependent coverage belongs in `faz_api_request`; add a typed
  tool only when it provides a meaningful, well-tested operational workflow.

See `docs/FORTIANALYZER_8_API.md` and
`docs/FORTIANALYZER_RUNBOOK.md` before changing FortiAnalyzer behavior.

## FortiGate Rules

The FortiGate contract is split across FortiOS REST domains.

- The generic REST entry point is `/api/v2/...`.
- Configuration APIs live under `/api/v2/cmdb/...`.
- Monitoring APIs live under `/api/v2/monitor/...`.
- Log APIs live under `/api/v2/log/...`.
- Service APIs live under `/api/v2/service/...`.
- New domain-specific behavior should prefer `fgt_cmdb_request`,
  `fgt_monitor_request`, `fgt_log_request`, or `fgt_service_request` over
  adding thin one-off wrappers.
- New typed FortiGate tools should be reserved for common operational
  workflows that are safer or easier than raw domain requests.
- Preserve the client's default `vdom` injection behavior unless the request
  explicitly overrides it.
- Session endpoints such as `/logincheck` and `/logout` remain client-managed.

See `docs/FORTIOS_8_API.md` before changing FortiGate behavior.

## Change Workflow

1. Read the client, tool registration, tests, and relevant documentation.
2. Confirm the official API method, URL, required fields, and response lifecycle.
3. Make the smallest coherent implementation change.
4. Add or update contract tests that inspect the emitted request.
5. Update tool descriptions and operator documentation in the same commit.
6. Run the verification commands below.
7. Review `git diff --check` and confirm no secrets or generated caches are staged.

## Verification

Create a virtual environment and install dependencies if needed:

```bash
python -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements.txt
```

On Windows PowerShell use `.venv\Scripts\Activate.ps1`.

Run:

```bash
python -m unittest discover -s tests -v
python -m compileall -q src tests
git diff --check
```

For changes to tool registration, also instantiate `FastMCP`, register the
affected module, and verify that `list_tools()` produces valid schemas.

## Documentation Expectations

- `README.md`: short orientation and links.
- `docs/TOOL_REFERENCE.md`: complete registered tool inventory.
- `docs/OPERATIONS.md`: server lifecycle and routine administration.
- Product runbooks: appliance workflows and examples.
- `docs/TROUBLESHOOTING.md`: symptoms, causes, and concrete diagnostics.

Commands in documentation must work from the repository root unless the guide
explicitly says otherwise.
