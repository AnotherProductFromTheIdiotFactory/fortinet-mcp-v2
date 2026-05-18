from __future__ import annotations

import json
import logging
import os
import sys

from mcp.server.fastmcp import FastMCP

from config import Config
from tools.fortigate_tools import register_fortigate_tools
from tools.fortimanager_tools import register_fortimanager_tools
from tools.fortianalyzer_tools import register_fortianalyzer_tools

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    stream=sys.stderr,
)
log = logging.getLogger("fortinet-mcp")


def build_server() -> FastMCP:
    try:
        config = Config.load()
    except FileNotFoundError as e:
        log.error(str(e))
        sys.exit(1)

    fgt_count = len(config.fortigates)
    fmg_count = len(config.fortimanagers)
    faz_count = len(config.fortianalyzers)
    log.info(
        "Loaded config: %d FortiGate(s), %d FortiManager(s), %d FortiAnalyzer(s)",
        fgt_count,
        fmg_count,
        faz_count,
    )

    mcp = FastMCP(
        "Fortinet MCP Server",
        instructions=(
            "This server exposes tools for managing Fortinet FortiGate, FortiManager, "
            "and FortiAnalyzer devices. All tools require a device_id argument that "
            "matches an entry in the server's config file. "
            "Use fgt_list_devices / fmg_list_devices / faz_list_devices to discover "
            "available device IDs before calling other tools."
        ),
    )

    if fgt_count > 0:
        register_fortigate_tools(mcp, config)
        log.info("Registered FortiGate tools")

    if fmg_count > 0:
        register_fortimanager_tools(mcp, config)
        log.info("Registered FortiManager tools")

    if faz_count > 0:
        register_fortianalyzer_tools(mcp, config)
        log.info("Registered FortiAnalyzer tools")

    # Health check resource
    @mcp.resource("fortinet://health")
    async def health() -> str:
        """Server health and device inventory."""
        return json.dumps(
            {
                "status": "ok",
                "fortigates": [
                    {"id": d.id, "name": d.name, "host": d.host} for d in config.fortigates
                ],
                "fortimanagers": [
                    {"id": d.id, "name": d.name, "host": d.host} for d in config.fortimanagers
                ],
                "fortianalyzers": [
                    {"id": d.id, "name": d.name, "host": d.host} for d in config.fortianalyzers
                ],
            },
            indent=2,
        )

    return mcp


def main():
    transport = os.getenv("MCP_TRANSPORT", "streamable-http")
    host = os.getenv("MCP_HOST", "0.0.0.0")
    port = int(os.getenv("MCP_PORT", "8000"))

    mcp = build_server()

    if transport == "stdio":
        log.info("Starting with stdio transport")
        mcp.run(transport="stdio")
    else:
        log.info("Starting with %s transport on %s:%d", transport, host, port)
        mcp.run(transport="streamable-http", host=host, port=port)


if __name__ == "__main__":
    main()
