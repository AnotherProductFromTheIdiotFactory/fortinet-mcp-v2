from __future__ import annotations

import ssl
import httpx


def build_client(host: str, port: int, verify_ssl: bool) -> httpx.AsyncClient:
    base_url = f"https://{host}:{port}"
    if verify_ssl:
        return httpx.AsyncClient(base_url=base_url, timeout=30.0)
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    return httpx.AsyncClient(base_url=base_url, verify=False, timeout=30.0)


def raise_for_status(response: httpx.Response) -> dict:
    response.raise_for_status()
    return response.json()
