# Development Guide

## Local Setup

```bash
python3.12 -m venv .venv
. .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
export PYTHONPATH="$PWD/src"
```

Windows PowerShell:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
$env:PYTHONPATH = (Resolve-Path .\src).Path
```

## Architecture

- `server.py` loads configuration and registers product tool modules.
- `config.py` owns inventory types and `${ENV_VAR}` substitution.
- `clients/` translate Python methods into Fortinet HTTP requests.
- `tools/` define MCP-facing names, argument schemas, and descriptions.
- Tool modules cache one client object per configured appliance.

Keep protocol handling in clients and MCP presentation in tools.

## Adding a Tool

1. Identify an official API operation and target product version.
2. Add or reuse a client method.
3. Add a narrowly named tool with complete argument documentation.
4. Validate inputs that affect method names, URLs, or task lifecycles.
5. Add a request-contract test using `httpx.MockTransport`.
6. Update `TOOL_REFERENCE.md` and the relevant runbook.
7. Verify FastMCP schema registration.

Avoid thin typed wrappers for obscure version-specific FortiAnalyzer or
FortiGate endpoints; `faz_api_request` and `fgt_api_request` already provide
complete official API coverage for those products.

## Tests

```bash
python -m unittest discover -s tests -v
python -m compileall -q src tests
git diff --check
```

FortiAnalyzer tests should assert the emitted JSON-RPC method, URL, session,
required `apiver`, and whether fields are flattened in `params` or nested in
`data`.

## Tool Schema Smoke Test

Instantiate `FastMCP`, create a `Config` containing dummy devices, register the
tool modules, and await `mcp.list_tools()`. This catches annotations that cannot
be represented as MCP JSON schemas.

The expected counts for this branch are:

| Product | Tools |
|---|---:|
| FortiGate | 48 |
| FortiManager | 31 |
| FortiAnalyzer | 29 |
| Total | 108 |

Update this table and `TOOL_REFERENCE.md` whenever tools are added or removed.

## FortiAnalyzer OpenAPI Validation

For a typed FortiAnalyzer change:

1. Find the pseudo-path in the official OpenAPI export.
2. Resolve its request schema.
3. Record `method`, `params[].url`, required fields, and field placement.
4. Confirm asynchronous start/get/delete behavior where applicable.
5. Add a test that inspects the exact outgoing JSON object.

Do not rely on FortiManager similarity; the products share JSON-RPC transport
but not every URL or operational payload.

## FortiOS Swagger Validation

For a typed FortiGate change:

1. Find the REST path in the official FortiOS Swagger export.
2. Record the HTTP method and whether the endpoint is CMDB, monitor, or log.
3. Confirm whether `vdom` belongs in the query string.
4. Add a test that inspects the exact outgoing request path, query, and auth.
5. Prefer `fgt_api_request` instead of adding a thin tool for one-off CMDB objects.

## Documentation Review

Before commit:

- Confirm every relative Markdown link resolves.
- Confirm commands run from the repository root.
- Confirm tool names exist in FastMCP registration output.
- Remove secrets, real credentials, and private infrastructure values.
- Keep examples obviously synthetic.

## Release Procedure

1. Run tests and schema smoke checks.
2. Review security-sensitive changes.
3. Update documentation and release notes or PR description.
4. Build the container without cache when dependency behavior changed.
5. Smoke test stdio or HTTP transport.
6. Commit with a scoped message and push a review branch.
7. After merge, deploy an immutable tag or commit and run read-only smoke tests.
