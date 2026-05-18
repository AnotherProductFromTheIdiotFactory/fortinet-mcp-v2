from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from typing import Any, Optional
import yaml

_ENV_RE = re.compile(r"\$\{([^}]+)\}")


def _resolve(value: Any) -> Any:
    """Expand ${ENV_VAR} references in string config values."""
    if not isinstance(value, str):
        return value
    def _sub(m: re.Match) -> str:
        var = m.group(1)
        result = os.environ.get(var)
        if result is None:
            raise ValueError(f"Config references undefined environment variable: ${{{var}}}")
        return result
    return _ENV_RE.sub(_sub, value)


def _resolve_dict(d: dict) -> dict:
    return {k: _resolve(v) for k, v in d.items()}


@dataclass
class FortiGateConfig:
    id: str
    host: str
    name: str = ""
    port: int = 443
    api_key: Optional[str] = None
    username: Optional[str] = None
    password: Optional[str] = None
    verify_ssl: bool = False
    vdom: str = "root"

    def __post_init__(self):
        if not self.api_key and not (self.username and self.password):
            raise ValueError(f"FortiGate {self.id}: provide api_key or username+password")


@dataclass
class FortiManagerConfig:
    id: str
    host: str
    name: str = ""
    port: int = 443
    username: str = "admin"
    password: str = ""
    verify_ssl: bool = False
    adom: str = "root"


@dataclass
class FortiAnalyzerConfig:
    id: str
    host: str
    name: str = ""
    port: int = 443
    username: str = "admin"
    password: str = ""
    verify_ssl: bool = False
    adom: str = "root"


@dataclass
class Config:
    fortigates: list[FortiGateConfig] = field(default_factory=list)
    fortimanagers: list[FortiManagerConfig] = field(default_factory=list)
    fortianalyzers: list[FortiAnalyzerConfig] = field(default_factory=list)

    @classmethod
    def load(cls, path: Optional[str] = None) -> "Config":
        config_path = path or os.getenv("CONFIG_PATH", "config.yaml")
        if not os.path.exists(config_path):
            raise FileNotFoundError(f"Config file not found: {config_path}")

        with open(config_path) as f:
            data = yaml.safe_load(f) or {}

        fgts = [FortiGateConfig(**_resolve_dict(d)) for d in data.get("fortigates", [])]
        fmgs = [FortiManagerConfig(**_resolve_dict(d)) for d in data.get("fortimanagers", [])]
        fazs = [FortiAnalyzerConfig(**_resolve_dict(d)) for d in data.get("fortianalyzers", [])]

        return cls(fortigates=fgts, fortimanagers=fmgs, fortianalyzers=fazs)

    def get_fgt(self, device_id: str) -> FortiGateConfig:
        for d in self.fortigates:
            if d.id == device_id:
                return d
        ids = [d.id for d in self.fortigates]
        raise ValueError(f"FortiGate '{device_id}' not found. Available: {ids}")

    def get_fmg(self, device_id: str) -> FortiManagerConfig:
        for d in self.fortimanagers:
            if d.id == device_id:
                return d
        ids = [d.id for d in self.fortimanagers]
        raise ValueError(f"FortiManager '{device_id}' not found. Available: {ids}")

    def get_faz(self, device_id: str) -> FortiAnalyzerConfig:
        for d in self.fortianalyzers:
            if d.id == device_id:
                return d
        ids = [d.id for d in self.fortianalyzers]
        raise ValueError(f"FortiAnalyzer '{device_id}' not found. Available: {ids}")
