"""Load, validate, and summarize a NetLattice topology.

The console never talks to infrastructure. It reads the same declarative
topology as the deployment agent and exposes a read-only view plus safe
configuration previews.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from validate_topology import validate  # noqa: E402

DEFAULT_TOPOLOGY = ROOT / "topology.example.yaml"


class TopologyError(ValueError):
    """A topology file is missing, malformed, or fails validation."""

    def __init__(self, errors: list[str], warnings: list[str] | None = None) -> None:
        self.errors = errors
        self.warnings = warnings or []
        super().__init__("; ".join(errors))


def topology_path(path: str | os.PathLike[str] | None = None) -> Path:
    """Resolve the topology path from an argument or NETLATTICE_TOPOLOGY."""
    raw = path or os.environ.get("NETLATTICE_TOPOLOGY") or DEFAULT_TOPOLOGY
    return Path(raw).expanduser().resolve()


def load(path: str | os.PathLike[str] | None = None) -> dict[str, Any]:
    """Read and validate a topology document."""
    file = topology_path(path)
    if not file.is_file():
        raise TopologyError([f"topology not found: {file}"])

    try:
        document = yaml.safe_load(file.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise TopologyError([f"invalid YAML: {exc}"]) from exc

    report = validate(document)
    if report.errors:
        raise TopologyError(report.errors, report.warnings)
    if not isinstance(document, dict):
        raise TopologyError(["topology must be a mapping"])
    return document


def spec(document: dict[str, Any]) -> dict[str, Any]:
    value = document.get("spec")
    return value if isinstance(value, dict) else {}


def modules(document: dict[str, Any]) -> dict[str, Any]:
    value = spec(document).get("modules")
    return value if isinstance(value, dict) else {}


def module_config(document: dict[str, Any], name: str) -> dict[str, Any]:
    value = modules(document).get(name)
    return value if isinstance(value, dict) else {}


def networks(document: dict[str, Any]) -> dict[str, Any]:
    value = spec(document).get("networks")
    return value if isinstance(value, dict) else {}


def nodes(document: dict[str, Any]) -> list[dict[str, Any]]:
    value = spec(document).get("nodes")
    return value if isinstance(value, list) else []


def peers(document: dict[str, Any]) -> list[dict[str, Any]]:
    value = module_config(document, "vpn").get("peers")
    return value if isinstance(value, list) else []


def templates(document: dict[str, Any]) -> list[dict[str, Any]]:
    value = module_config(document, "compute").get("templates")
    return value if isinstance(value, list) else []


def find_peer(document: dict[str, Any], name: str) -> dict[str, Any]:
    for peer in peers(document):
        if peer.get("name") == name:
            return peer
    raise KeyError(name)


def _module_summary(document: dict[str, Any], name: str) -> str:
    config = module_config(document, name)
    if not config.get("enabled", False):
        return "disabled"
    if name == "dns":
        return f"{len(config.get('records', []))} records · {len(config.get('upstreams', []))} upstreams"
    if name == "vpn":
        return f"{len(config.get('peers', []))} peers · {config.get('endpoint', 'no endpoint')}"
    if name == "compute":
        return f"{len(config.get('templates', []))} templates · {config.get('api_url', 'no api_url')}"
    return "configured"


def module_view(document: dict[str, Any], name: str) -> dict[str, Any]:
    config = module_config(document, name)
    enabled = bool(config.get("enabled", False))
    return {
        "name": name,
        "enabled": enabled,
        "provider": config.get("provider"),
        "mode": "contract" if enabled else "disabled",
        "summary": _module_summary(document, name),
    }


def site_summary(document: dict[str, Any]) -> dict[str, Any]:
    """Return a safe, UI-friendly summary of the topology."""
    site = document.get("metadata", {}).get("name")
    network_view: dict[str, Any] = {}
    for name, network in networks(document).items():
        if isinstance(network, dict):
            network_view[name] = {
                "cidr": str(network.get("cidr", "")),
                "gateway": network.get("gateway"),
                "dns": network.get("dns"),
                "vlan": network.get("vlan"),
            }

    module_names = ["dns", "vpn", "compute"]
    dns_config = module_config(document, "dns")
    vpn_config = module_config(document, "vpn")
    compute_config = module_config(document, "compute")

    return {
        "site": site,
        "apiVersion": document.get("apiVersion"),
        "domains": spec(document).get("domains", {}),
        "networks": network_view,
        "nodes": nodes(document),
        "modules": {name: module_view(document, name) for name in module_names},
        "counts": {
            "nodes": len(nodes(document)),
            "networks": len(network_view),
            "dnsRecords": len(dns_config.get("records", [])),
            "vpnPeers": len(vpn_config.get("peers", [])),
            "computeTemplates": len(compute_config.get("templates", [])),
        },
    }


def display_path(path: str | os.PathLike[str] | None = None) -> str:
    """Return a repository-relative path for UI/API display."""
    file = topology_path(path)
    try:
        return str(file.relative_to(ROOT))
    except ValueError:
        return file.name
