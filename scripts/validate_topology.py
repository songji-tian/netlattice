#!/usr/bin/env python3
"""Validate a NetLattice topology.yaml without touching infrastructure."""

from __future__ import annotations

import argparse
import ipaddress
import sys
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError:
    sys.exit("PyYAML is required: python3 -m pip install pyyaml")


class Report:
    def __init__(self) -> None:
        self.errors: list[str] = []
        self.warnings: list[str] = []

    def error(self, message: str) -> None:
        self.errors.append(message)

    def warn(self, message: str) -> None:
        self.warnings.append(message)


def is_dns_name(value: str) -> bool:
    if not value or len(value) > 253:
        return False
    labels = value.rstrip(".").split(".")
    return all(
        0 < len(label) <= 63
        and label[0] != "-"
        and label[-1] != "-"
        and all(ch.isalnum() or ch == "-" for ch in label)
        for label in labels
    )


def parse_ip(value: Any) -> ipaddress.IPv4Address | ipaddress.IPv6Address | None:
    try:
        return ipaddress.ip_address(str(value))
    except ValueError:
        return None


def parse_net(value: Any) -> ipaddress.IPv4Network | ipaddress.IPv6Network | None:
    try:
        return ipaddress.ip_network(str(value), strict=False)
    except ValueError:
        return None


def inside(name: str, zone: str) -> bool:
    return name == zone or name.endswith("." + zone)


def validate(doc: Any) -> Report:
    r = Report()
    if not isinstance(doc, dict):
        r.error("top-level document must be a mapping")
        return r

    if doc.get("apiVersion") != "netlattice/v1":
        r.error("apiVersion must be netlattice/v1")
    if doc.get("kind") != "Site":
        r.error("kind must be Site")

    metadata = doc.get("metadata")
    if not isinstance(metadata, dict):
        r.error("metadata must be a mapping")
        metadata = {}
    site = metadata.get("name")
    if not isinstance(site, str) or not is_dns_name(site):
        r.error("metadata.name must be a DNS-label-safe string")

    spec = doc.get("spec")
    if not isinstance(spec, dict):
        r.error("spec must be a mapping")
        return r

    domains = spec.get("domains")
    if not isinstance(domains, dict):
        r.error("spec.domains must be a mapping")
        domains = {}
    internal = domains.get("internal")
    if not isinstance(internal, str) or not is_dns_name(internal):
        r.error("spec.domains.internal must be a DNS name")
        internal = ""
    public = domains.get("public")
    if public is not None and (not isinstance(public, str) or not is_dns_name(public)):
        r.error("spec.domains.public must be a DNS name when set")

    networks: dict[str, Any] = {}
    raw_networks = spec.get("networks")
    if not isinstance(raw_networks, dict) or not raw_networks:
        r.error("spec.networks must be a non-empty mapping")
        raw_networks = {}
    for name, net in raw_networks.items():
        if not isinstance(net, dict):
            r.error(f"networks.{name} must be a mapping")
            continue
        network = parse_net(net.get("cidr"))
        if network is None:
            r.error(f"networks.{name}.cidr is invalid")
            continue
        networks[name] = network
        gateway = net.get("gateway")
        if gateway is not None:
            ip = parse_ip(gateway)
            if ip is None or ip not in network:
                r.error(f"networks.{name}.gateway must be inside {network}")
        dns = net.get("dns")
        if dns is not None and parse_ip(dns) is None:
            r.error(f"networks.{name}.dns must be an IP address")

    nodes = spec.get("nodes")
    if not isinstance(nodes, list) or not nodes:
        r.error("spec.nodes must be a non-empty list")
        nodes = []
    node_names: set[str] = set()
    node_addresses: set[str] = set()
    for index, node in enumerate(nodes):
        prefix = f"nodes[{index}]"
        if not isinstance(node, dict):
            r.error(f"{prefix} must be a mapping")
            continue
        name = node.get("name")
        if not isinstance(name, str) or not is_dns_name(name):
            r.error(f"{prefix}.name must be a DNS-label-safe string")
        elif name in node_names:
            r.error(f"{prefix}.name duplicated: {name}")
        else:
            node_names.add(name)
        role = node.get("role")
        if role not in {"edge", "compute", "control", "client"}:
            r.error(f"{prefix}.role must be edge/compute/control/client")
        address = node.get("address")
        ip = parse_ip(address)
        if ip is None:
            r.error(f"{prefix}.address must be an IP address")
        elif str(ip) in node_addresses:
            r.warn(f"{prefix}.address duplicated: {ip}")
        else:
            node_addresses.add(str(ip))
        if ip is not None and networks and not any(ip in net for net in networks.values()):
            r.warn(f"{prefix}.address {ip} is not inside any declared network")

    modules = spec.get("modules")
    if not isinstance(modules, dict):
        r.error("spec.modules must be a mapping")
        modules = {}

    dns_cfg = modules.get("dns")
    if isinstance(dns_cfg, dict) and dns_cfg.get("enabled", True):
        if dns_cfg.get("provider") != "adguard":
            r.error("modules.dns.provider must be adguard")
        port = dns_cfg.get("admin_port", 3000)
        if not isinstance(port, int) or not 1 <= port <= 65535:
            r.error("modules.dns.admin_port must be 1..65535")
        upstreams = dns_cfg.get("upstreams", [])
        if not isinstance(upstreams, list):
            r.error("modules.dns.upstreams must be a list")
        else:
            for index, upstream in enumerate(upstreams):
                if parse_ip(upstream) is None:
                    r.error(f"modules.dns.upstreams[{index}] must be an IP address")
        records = dns_cfg.get("records", [])
        if not isinstance(records, list):
            r.error("modules.dns.records must be a list")
        else:
            seen: set[tuple[str, str]] = set()
            for index, record in enumerate(records):
                prefix = f"modules.dns.records[{index}]"
                if not isinstance(record, dict):
                    r.error(f"{prefix} must be a mapping")
                    continue
                name = record.get("name")
                rtype = record.get("type")
                value = record.get("value")
                if not isinstance(name, str) or not is_dns_name(name):
                    r.error(f"{prefix}.name must be a DNS name")
                    continue
                if rtype not in {"A", "AAAA", "CNAME"}:
                    r.error(f"{prefix}.type must be A/AAAA/CNAME")
                    continue
                if not isinstance(value, str) or not value:
                    r.error(f"{prefix}.value must be a non-empty string")
                    continue
                key = (name, rtype)
                if key in seen:
                    r.error(f"duplicate DNS record: {name} {rtype}")
                seen.add(key)
                if not record.get("external") and internal and not inside(name, internal):
                    r.error(f"{prefix}.name must be inside {internal} (or set external: true)")
                if rtype in {"A", "AAAA"}:
                    ip = parse_ip(value)
                    if ip is None:
                        r.error(f"{prefix}.value must be an IP address for {rtype}")
                    elif rtype == "A" and ip.version != 4:
                        r.error(f"{prefix}.value must be IPv4 for A")
                    elif rtype == "AAAA" and ip.version != 6:
                        r.error(f"{prefix}.value must be IPv6 for AAAA")

    vpn_cfg = modules.get("vpn")
    vpn_network = networks.get("vpn")
    if isinstance(vpn_cfg, dict) and vpn_cfg.get("enabled", True):
        if vpn_cfg.get("provider") != "wireguard":
            r.error("modules.vpn.provider must be wireguard")
        endpoint = vpn_cfg.get("endpoint")
        if not isinstance(endpoint, str) or ":" not in endpoint:
            r.error("modules.vpn.endpoint must be host:port")
        else:
            host, _, port_text = endpoint.rpartition(":")
            if not host:
                r.error("modules.vpn.endpoint host is empty")
            try:
                port = int(port_text)
                if not 1 <= port <= 65535:
                    raise ValueError
            except ValueError:
                r.error("modules.vpn.endpoint port must be 1..65535")
        peers = vpn_cfg.get("peers", [])
        if not isinstance(peers, list):
            r.error("modules.vpn.peers must be a list")
        else:
            peer_names: set[str] = set()
            peer_ips: set[str] = set()
            for index, peer in enumerate(peers):
                prefix = f"modules.vpn.peers[{index}]"
                if not isinstance(peer, dict):
                    r.error(f"{prefix} must be a mapping")
                    continue
                name = peer.get("name")
                if not isinstance(name, str) or not name:
                    r.error(f"{prefix}.name must be a non-empty string")
                elif name in peer_names:
                    r.error(f"{prefix}.name duplicated: {name}")
                else:
                    peer_names.add(name)
                allowed = peer.get("allowed_ips")
                if not isinstance(allowed, list) or not allowed:
                    r.error(f"{prefix}.allowed_ips must be a non-empty list")
                    continue
                for j, cidr in enumerate(allowed):
                    net = parse_net(cidr)
                    if net is None:
                        r.error(f"{prefix}.allowed_ips[{j}] is invalid")
                        continue
                    if vpn_network is not None and not net.subnet_of(vpn_network):
                        r.error(f"{prefix}.allowed_ips[{j}] must be inside {vpn_network}")
                    first = str(net.network_address)
                    if first in peer_ips:
                        r.warn(f"{prefix}.allowed_ips[{j}] overlaps another peer")
                    peer_ips.add(first)

    compute_cfg = modules.get("compute")
    if isinstance(compute_cfg, dict) and compute_cfg.get("enabled", True):
        if compute_cfg.get("provider") != "proxmox":
            r.error("modules.compute.provider must be proxmox")
        api_url = compute_cfg.get("api_url")
        if not isinstance(api_url, str) or not api_url.startswith(("http://", "https://")):
            r.error("modules.compute.api_url must be http(s) URL")
        templates = compute_cfg.get("templates", [])
        if not isinstance(templates, list):
            r.error("modules.compute.templates must be a list")
        else:
            template_names: set[str] = set()
            vmids: set[int] = set()
            for index, template in enumerate(templates):
                prefix = f"modules.compute.templates[{index}]"
                if not isinstance(template, dict):
                    r.error(f"{prefix} must be a mapping")
                    continue
                name = template.get("name")
                if not isinstance(name, str) or not name:
                    r.error(f"{prefix}.name must be a non-empty string")
                elif name in template_names:
                    r.error(f"{prefix}.name duplicated: {name}")
                else:
                    template_names.add(name)
                vmid = template.get("vmid")
                if not isinstance(vmid, int) or vmid <= 0:
                    r.error(f"{prefix}.vmid must be a positive integer")
                elif vmid in vmids:
                    r.error(f"{prefix}.vmid duplicated: {vmid}")
                else:
                    vmids.add(vmid)
                os_name = template.get("os")
                if os_name is not None and os_name not in {"linux", "windows"}:
                    r.error(f"{prefix}.os must be linux/windows")
                cloud_init = template.get("cloud_init")
                if cloud_init is not None and not isinstance(cloud_init, bool):
                    r.error(f"{prefix}.cloud_init must be boolean")

    return r


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate a NetLattice topology.yaml")
    parser.add_argument("topology", type=Path)
    args = parser.parse_args()

    try:
        doc = yaml.safe_load(args.topology.read_text(encoding="utf-8"))
    except FileNotFoundError:
        print(f"ERROR: file not found: {args.topology}", file=sys.stderr)
        return 1
    except yaml.YAMLError as exc:
        print(f"ERROR: invalid YAML: {exc}", file=sys.stderr)
        return 1

    report = validate(doc)
    for warning in report.warnings:
        print(f"WARN: {warning}", file=sys.stderr)
    for error in report.errors:
        print(f"ERROR: {error}", file=sys.stderr)

    if report.errors:
        print(f"FAILED: {len(report.errors)} error(s), {len(report.warnings)} warning(s)", file=sys.stderr)
        return 1

    site = doc.get("metadata", {}).get("name", "?")
    print(f"OK: {args.topology} site={site} errors=0 warnings={len(report.warnings)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
