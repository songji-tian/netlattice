"""Render safe configuration previews from a topology.

These functions intentionally emit placeholders for private keys and never
contact DNS, WireGuard, or Proxmox endpoints.
"""

from __future__ import annotations

import ipaddress
import json
from typing import Any

import yaml

from . import topology

PLACEHOLDER = "__REPLACE_ME__"


def _networks(document: dict[str, Any]) -> dict[str, Any]:
    return topology.networks(document)


def _dns_config(document: dict[str, Any]) -> dict[str, Any]:
    return topology.module_config(document, "dns")


def _vpn_config(document: dict[str, Any]) -> dict[str, Any]:
    return topology.module_config(document, "vpn")


def _compute_config(document: dict[str, Any]) -> dict[str, Any]:
    return topology.module_config(document, "compute")


def _vpn_network(document: dict[str, Any]) -> ipaddress.IPv4Network | ipaddress.IPv6Network:
    raw = _networks(document).get("vpn", {}).get("cidr")
    if not raw:
        raise ValueError("spec.networks.vpn.cidr is required")
    return ipaddress.ip_network(str(raw), strict=False)


def _slug(value: str) -> str:
    return "".join(ch if ch.isalnum() else "_" for ch in value).strip("_").upper()


def _server_address(document: dict[str, Any]) -> str:
    network = _vpn_network(document)
    config = _networks(document).get("vpn", {})
    raw = str(config.get("gateway") or (network.network_address + 1)).split("/", 1)[0]
    return f"{raw}/{network.prefixlen}"


def render_dns(document: dict[str, Any]) -> str:
    """Render an AdGuard Home-style YAML preview."""
    config = _dns_config(document)
    admin_port = int(config.get("admin_port", 3000))
    upstreams = config.get("upstreams") or ["1.1.1.1", "9.9.9.9"]
    rewrites = [
        {
            "domain": record.get("name"),
            "answer": record.get("value"),
        }
        for record in config.get("records", [])
        if record.get("type") in {"A", "AAAA", "CNAME"}
    ]
    filters = [
        {"enabled": True, "url": url}
        for url in (config.get("filters") or [])
        if isinstance(url, str) and url
    ]

    payload = {
        "http": {"address": f"0.0.0.0:{admin_port}"},
        "dns": {
            "bind_hosts": ["0.0.0.0"],
            "port": 53,
            "upstream_dns": upstreams,
            "rewrites": rewrites,
        },
    }
    if filters:
        payload["filters"] = filters

    header = (
        "# NetLattice DNS preview — generated from topology, not applied.\n"
        "# Review before copying into AdGuardHome.yaml.\n"
    )
    return header + yaml.safe_dump(payload, sort_keys=False)


def render_wireguard_server(document: dict[str, Any]) -> str:
    """Render a server-side WireGuard config with key placeholders."""
    config = _vpn_config(document)
    endpoint = str(config.get("endpoint", "vpn.example.com:51820"))
    _, _, port = endpoint.rpartition(":")
    interface = config.get("interface", "wg0")

    lines = [
        "# NetLattice WireGuard server preview — generated, not applied.",
        f"# interface: {interface}",
        "[Interface]",
        f"Address = {_server_address(document)}",
        f"ListenPort = {port or '51820'}",
        f"PrivateKey = {PLACEHOLDER}  # server private key",
        "",
    ]
    for peer in topology.peers(document):
        name = str(peer.get("name", "peer"))
        public_key = peer.get("public_key") or f"__REPLACE_{_slug(name)}_PUBLIC_KEY__"
        lines.extend(
            [
                f"# peer: {name}",
                "[Peer]",
                f"PublicKey = {public_key}",
                f"AllowedIPs = {', '.join(str(item) for item in peer.get('allowed_ips', []))}",
                "",
            ]
        )
    return "\n".join(lines).rstrip() + "\n"


def render_wireguard_peer(document: dict[str, Any], peer_name: str) -> str:
    """Render a client-side WireGuard config for one peer."""
    peer = topology.find_peer(document, peer_name)
    config = _vpn_config(document)
    endpoint = str(config.get("endpoint", "vpn.example.com:51820"))
    dns = peer.get("dns") or _networks(document).get("lan", {}).get("dns")
    keepalive = int(peer.get("persistent_keepalive", 25))

    allowed = []
    for network in _networks(document).values():
        cidr = str(network.get("cidr", ""))
        if cidr:
            allowed.append(cidr)

    lines = [
        f"# NetLattice WireGuard client preview for peer: {peer_name}",
        "# Private key placeholder: generate one on the client, never commit it.",
        "[Interface]",
        f"PrivateKey = {PLACEHOLDER}  # client private key",
        f"Address = {', '.join(str(item) for item in peer.get('allowed_ips', []))}",
    ]
    if dns:
        lines.append(f"DNS = {dns}")
    lines.extend(
        [
            "",
            "[Peer]",
            f"PublicKey = {PLACEHOLDER}  # server public key",
            f"Endpoint = {endpoint}",
            f"AllowedIPs = {', '.join(allowed)}",
            f"PersistentKeepalive = {keepalive}",
        ]
    )
    return "\n".join(lines).rstrip() + "\n"


def render_compute_plan(document: dict[str, Any]) -> dict[str, Any]:
    """Render a read-only clone plan; no Proxmox call is made."""
    config = _compute_config(document)
    planned = []
    for template in topology.templates(document):
        os_name = template.get("os", "linux")
        cloud_init = template.get("cloud_init", os_name == "linux")
        planned.append(
            {
                "name": template.get("name"),
                "vmid": template.get("vmid"),
                "os": os_name,
                "cloud_init": bool(cloud_init),
                "action": "clone-on-apply",
            }
        )
    return {
        "provider": config.get("provider", "proxmox"),
        "api_url": config.get("api_url"),
        "defaults": config.get("defaults", {}),
        "templates": planned,
        "live": False,
        "note": "Contract preview only. The v0.2 console does not call Proxmox.",
    }


def render_plan(document: dict[str, Any]) -> dict[str, Any]:
    """Return a compact, secret-free resource plan."""
    dns = _dns_config(document)
    vpn = _vpn_config(document)
    compute = render_compute_plan(document)

    resources: list[dict[str, Any]] = []
    for record in dns.get("records", []):
        resources.append(
            {
                "module": "dns",
                "action": "render",
                "resource": f"rewrite:{record.get('name')}",
                "reason": f"{record.get('type')} {record.get('value')}",
                "destructive": False,
            }
        )
    for peer in vpn.get("peers", []):
        resources.append(
            {
                "module": "vpn",
                "action": "render",
                "resource": f"peer:{peer.get('name')}",
                "reason": ", ".join(str(item) for item in peer.get("allowed_ips", [])),
                "destructive": False,
            }
        )
    for template in compute["templates"]:
        resources.append(
            {
                "module": "compute",
                "action": "render",
                "resource": f"template:{template.get('name')}",
                "reason": f"vmid={template.get('vmid')} ({template.get('os')})",
                "destructive": False,
            }
        )

    return {
        "site": document.get("metadata", {}).get("name"),
        "mode": "render-only",
        "resources": resources,
        "live": False,
    }


def render_bundle(document: dict[str, Any]) -> dict[str, str]:
    """Return every safe preview keyed by a relative output path."""
    bundle: dict[str, str] = {
        "dns/AdGuardHome.yaml": render_dns(document),
        "vpn/wg0.conf": render_wireguard_server(document),
        "compute/plan.json": json.dumps(render_compute_plan(document), indent=2) + "\n",
        "plan.json": json.dumps(render_plan(document), indent=2) + "\n",
    }
    for peer in topology.peers(document):
        name = str(peer.get("name", "peer"))
        bundle[f"vpn/peers/{name}.conf"] = render_wireguard_peer(document, name)
    return bundle
