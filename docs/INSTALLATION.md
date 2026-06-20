# Installation and Deployment

## Requirements

- Python 3.12 for a local installation, or Docker Engine with Compose v2.
- IP routing and TCP 443 access from the MCP host to each appliance.
- A Fortinet account or API token with the required product permissions.
- A trusted certificate chain when `verify_ssl: true` is enabled.
- An MCP client supporting stdio or streamable HTTP.

## Docker Compose

From the repository root:

```bash
cp config.example.yaml config.yaml
cp .env.example .env
```

Edit both files. Remove unused example devices so the server does not register
tools for appliances that do not exist.

Build and start:

```bash
docker compose config
docker compose up -d --build
docker compose ps
docker compose logs --tail=100 fortinet-mcp
```

Expected state:

- Container name: `fortinet-mcp`
- Published endpoint: `http://localhost:8000/mcp`
- Health: `healthy` after the TCP listener starts
- Configuration mount: `/config/config.yaml`, read-only

Check health and the listener:

```bash
docker inspect --format '{{.State.Health.Status}}' fortinet-mcp
docker compose exec fortinet-mcp python -c "import socket; socket.create_connection(('127.0.0.1',8000),5).close(); print('ok')"
```

The health check proves that the MCP listener is accepting connections. Use an
MCP client to read `fortinet://health` for the loaded device inventory.

## Local Python Installation

Linux or macOS:

```bash
python3.12 -m venv .venv
. .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
export PYTHONPATH="$PWD/src"
export CONFIG_PATH="$PWD/config.yaml"
python src/server.py
```

Windows PowerShell:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
$env:PYTHONPATH = (Resolve-Path .\src).Path
$env:CONFIG_PATH = (Resolve-Path .\config.yaml).Path
python .\src\server.py
```

The default local transport is streamable HTTP on `0.0.0.0:8000`.

## Stdio Deployment

Set `MCP_TRANSPORT=stdio`. The process must keep stdout reserved for MCP
protocol messages; application logs are written to stderr.

```bash
export MCP_TRANSPORT=stdio
export PYTHONPATH="$PWD/src"
export CONFIG_PATH="$PWD/config.yaml"
python src/server.py
```

The MCP client should launch this command directly rather than connecting to a
URL.

## Reverse Proxy

The application does not authenticate incoming MCP clients. For shared or
remote use, place it behind a reverse proxy that provides:

- TLS termination
- Client authentication
- Source-network restrictions
- Request size and rate limits
- Access logs with secret redaction

Preserve streaming behavior and use timeouts long enough for MCP operations.
Do not publish port 8000 directly to an untrusted network.

## Uninstall

Stop and remove the container without deleting local configuration:

```bash
docker compose down
```

Remove the locally built image only when required:

```bash
docker compose down --rmi local
```

Keep `config.yaml` and `.env` until credential rotation and recovery decisions
are complete.
