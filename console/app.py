"""NetLattice reference console API.

Read-only by design: it renders safe previews from topology.yaml and never
connects to AdGuard Home, WireGuard, or Proxmox.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles

from . import __version__, render, topology

app = FastAPI(
    title="NetLattice Reference Console",
    version=__version__,
    description=(
        "Read-only console for a NetLattice topology. "
        "Renders DNS, WireGuard, and compute previews without touching infrastructure."
    ),
)
STATIC_DIR = Path(__file__).resolve().parent / "static"
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


def _document() -> dict[str, Any]:
    try:
        return topology.load()
    except topology.TopologyError as exc:
        raise HTTPException(
            status_code=422,
            detail={"errors": exc.errors, "warnings": exc.warnings},
        ) from exc


def _module_or_404(document: dict[str, Any], name: str) -> dict[str, Any]:
    config = topology.module_config(document, name)
    if not config:
        raise HTTPException(status_code=404, detail=f"module not found: {name}")
    return config


@app.get("/", include_in_schema=False)
def index() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/api/health", tags=["system"])
def health() -> dict[str, Any]:
    document = _document()
    summary = topology.site_summary(document)
    return {
        "ok": True,
        "service": "netlattice-console",
        "version": __version__,
        "mode": "render-only",
        "site": summary["site"],
        "topology": topology.display_path(),
        "modules": summary["modules"],
    }


@app.get("/api/site", tags=["site"])
def site() -> dict[str, Any]:
    return topology.site_summary(_document())


@app.get("/api/modules", tags=["site"])
def modules() -> dict[str, Any]:
    document = _document()
    return {"modules": [topology.module_view(document, name) for name in ("dns", "vpn", "compute")]}


@app.get("/api/topology", tags=["site"])
def raw_topology() -> dict[str, Any]:
    return _document()


@app.get("/api/dns", tags=["dns"])
def dns() -> dict[str, Any]:
    document = _document()
    config = _module_or_404(document, "dns")
    return {
        "module": topology.module_view(document, "dns"),
        "admin_port": config.get("admin_port", 3000),
        "upstreams": config.get("upstreams", []),
        "records": config.get("records", []),
        "filters": config.get("filters", []),
        "preview": render.render_dns(document),
    }


@app.get("/api/vpn", tags=["vpn"])
def vpn() -> dict[str, Any]:
    document = _document()
    _module_or_404(document, "vpn")
    return {
        "module": topology.module_view(document, "vpn"),
        "endpoint": topology.module_config(document, "vpn").get("endpoint"),
        "interface": topology.module_config(document, "vpn").get("interface", "wg0"),
        "peers": topology.peers(document),
        "server_preview": render.render_wireguard_server(document),
    }


@app.get("/api/vpn/peers/{peer_name}/config", tags=["vpn"], response_class=PlainTextResponse)
def vpn_peer_config(peer_name: str) -> str:
    document = _document()
    try:
        return render.render_wireguard_peer(document, peer_name)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=f"peer not found: {peer_name}") from exc


@app.get("/api/compute", tags=["compute"])
def compute() -> dict[str, Any]:
    document = _document()
    _module_or_404(document, "compute")
    return {
        "module": topology.module_view(document, "compute"),
        "plan": render.render_compute_plan(document),
    }


@app.get("/api/plan", tags=["render"])
def plan() -> dict[str, Any]:
    return render.render_plan(_document())


@app.get("/api/render", tags=["render"])
def render_bundle() -> dict[str, str]:
    return render.render_bundle(_document())


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("console.app:app", host="0.0.0.0", port=8787, reload=False)
