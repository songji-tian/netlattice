from __future__ import annotations

import os
import sys
import tempfile
import unittest
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
os.environ.setdefault("NETLATTICE_TOPOLOGY", str(ROOT / "examples" / "home-lab.yaml"))

from fastapi.testclient import TestClient  # noqa: E402

from console import render, topology  # noqa: E402
from console.app import app  # noqa: E402

EXAMPLE = ROOT / "examples" / "home-lab.yaml"


class TopologyTests(unittest.TestCase):
    def setUp(self) -> None:
        self.doc = topology.load(EXAMPLE)

    def test_summary_counts(self) -> None:
        summary = topology.site_summary(self.doc)
        self.assertEqual(summary["site"], "home-lab")
        self.assertEqual(summary["counts"]["vpnPeers"], 2)
        self.assertEqual(summary["counts"]["dnsRecords"], 2)
        self.assertEqual(summary["counts"]["computeTemplates"], 2)

    def test_invalid_document_fails(self) -> None:
        with tempfile.NamedTemporaryFile("w", suffix=".yaml", delete=False) as handle:
            handle.write("apiVersion: nope\nkind: Site\n")
            path = handle.name
        try:
            with self.assertRaises(topology.TopologyError):
                topology.load(path)
        finally:
            os.unlink(path)


class RenderTests(unittest.TestCase):
    def setUp(self) -> None:
        self.doc = topology.load(EXAMPLE)

    def test_dns_preview_is_yaml(self) -> None:
        preview = render.render_dns(self.doc)
        parsed = yaml.safe_load(preview)
        self.assertEqual(parsed["dns"]["port"], 53)
        self.assertEqual(parsed["dns"]["upstream_dns"], ["1.1.1.1", "9.9.9.9"])
        self.assertEqual(parsed["dns"]["rewrites"][0]["domain"], "pve.home.arpa")

    def test_wireguard_server_preview(self) -> None:
        preview = render.render_wireguard_server(self.doc)
        self.assertIn("Address = 10.44.0.1/24", preview)
        self.assertIn("ListenPort = 51820", preview)
        self.assertIn("AllowedIPs = 10.44.0.2/32", preview)
        self.assertIn("__REPLACE_LAPTOP_PUBLIC_KEY__", preview)

    def test_wireguard_peer_preview(self) -> None:
        preview = render.render_wireguard_peer(self.doc, "laptop")
        self.assertIn("Address = 10.44.0.2/32", preview)
        self.assertIn("DNS = 192.168.10.2", preview)
        self.assertIn("Endpoint = vpn.example.com:51820", preview)
        self.assertIn("AllowedIPs = 192.168.10.0/24, 10.44.0.0/24", preview)

    def test_unknown_peer_raises(self) -> None:
        with self.assertRaises(KeyError):
            render.render_wireguard_peer(self.doc, "missing")

    def test_bundle_contains_all_previews(self) -> None:
        bundle = render.render_bundle(self.doc)
        self.assertIn("dns/AdGuardHome.yaml", bundle)
        self.assertIn("vpn/wg0.conf", bundle)
        self.assertIn("vpn/peers/laptop.conf", bundle)
        self.assertIn("vpn/peers/phone.conf", bundle)
        self.assertIn("compute/plan.json", bundle)
        self.assertIn("plan.json", bundle)


class ApiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.client = TestClient(app)

    def test_health(self) -> None:
        response = self.client.get("/api/health")
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertTrue(body["ok"])
        self.assertEqual(body["site"], "home-lab")
        self.assertEqual(body["mode"], "render-only")

    def test_index(self) -> None:
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertIn("NetLattice", response.text)

    def test_openapi(self) -> None:
        response = self.client.get("/openapi.json")
        self.assertEqual(response.status_code, 200)
        paths = response.json()["paths"]
        self.assertIn("/api/vpn/peers/{peer_name}/config", paths)
        self.assertIn("/api/render", paths)

    def test_dns_endpoint(self) -> None:
        body = self.client.get("/api/dns").json()
        self.assertEqual(body["records"][0]["name"], "pve.home.arpa")
        self.assertIn("AdGuard", body["preview"])

    def test_peer_config_and_404(self) -> None:
        response = self.client.get("/api/vpn/peers/laptop/config")
        self.assertEqual(response.status_code, 200)
        self.assertIn("Endpoint = vpn.example.com:51820", response.text)
        missing = self.client.get("/api/vpn/peers/missing/config")
        self.assertEqual(missing.status_code, 404)

    def test_compute_and_render(self) -> None:
        compute = self.client.get("/api/compute").json()
        self.assertFalse(compute["plan"]["live"])
        self.assertEqual(compute["plan"]["templates"][0]["vmid"], 9001)
        bundle = self.client.get("/api/render").json()
        self.assertIn("vpn/peers/phone.conf", bundle)

    def test_invalid_topology_returns_422(self) -> None:
        with tempfile.NamedTemporaryFile("w", suffix=".yaml", delete=False) as handle:
            handle.write("apiVersion: nope\n")
            path = handle.name
        previous = os.environ.get("NETLATTICE_TOPOLOGY")
        os.environ["NETLATTICE_TOPOLOGY"] = path
        try:
            response = self.client.get("/api/health")
            self.assertEqual(response.status_code, 422)
        finally:
            if previous is None:
                os.environ.pop("NETLATTICE_TOPOLOGY", None)
            else:
                os.environ["NETLATTICE_TOPOLOGY"] = previous
            os.unlink(path)


if __name__ == "__main__":
    unittest.main()
