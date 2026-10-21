# Unified API contract

This is the contract the NetLattice Console and external agents should target. It is intentionally small; module-specific APIs remain the source of truth for advanced operations.

Base path:

```text
/api
```

Authentication:

- Browser: `sid` HttpOnly cookie, `SameSite=Lax`, 12h TTL.
- Agent/CLI: `Authorization: Bearer <token>`.
- Never put credentials in query strings.

Common errors:

```json
{"detail": "human-readable message"}
```

| HTTP | Meaning |
|---|---|
| 200 | success |
| 201 | created |
| 400 | invalid request |
| 401 | unauthenticated |
| 403 | insufficient role |
| 404 | not found |
| 409 | state conflict |
| 422 | schema validation |
| 502 | upstream module failure |

## Read-only reference console

The repository ships `console/`, a **read-only** implementation of the topology/render subset. It does not implement the write endpoints below.

| Method | Path | Purpose |
|---|---|---|
| GET | `/api/health` | service and topology status |
| GET | `/api/site` | site, nodes, networks, modules |
| GET | `/api/topology` | validated topology document |
| GET | `/api/modules` | module summaries |
| GET | `/api/dns` | DNS records and AdGuard preview |
| GET | `/api/vpn` | peers and WireGuard server preview |
| GET | `/api/vpn/peers/{name}/config` | one peer config, private-key placeholder |
| GET | `/api/compute` | templates and clone plan, read-only |
| GET | `/api/plan` | compact resource plan |
| GET | `/api/render` | all safe preview files |
| GET | `/openapi.json` | generated OpenAPI 3 document |

Start it with:

```bash
python3 -m venv .venv
.venv/bin/pip install -r console/requirements.txt
NETLATTICE_TOPOLOGY=examples/home-lab.yaml \
  .venv/bin/uvicorn console.app:app --host 127.0.0.1 --port 8787
```

The write endpoints below are the contract. The reference console does not implement them; verify the endpoint against the implementation you are running.

## Topology

### `GET /api/topology`

Returns the normalized, secret-free topology.

```json
{
  "site": "home-lab",
  "domains": {"internal": "home.arpa", "public": "example.com"},
  "networks": {"lan": {"cidr": "192.168.10.0/24"}},
  "modules": {
    "dns": {"enabled": true, "health": "ok"},
    "vpn": {"enabled": true, "health": "ok"},
    "compute": {"enabled": true, "health": "degraded"}
  }
}
```

### `GET /api/health`

Aggregated health. Each module returns `ok`, `degraded`, or `down`.

```json
{
  "ok": false,
  "modules": {
    "dns": {"status": "ok"},
    "vpn": {"status": "ok"},
    "compute": {"status": "degraded", "error": "PVE API timeout"}
  }
}
```

## DNS

### `GET /api/dns/records`

```json
{
  "records": [
    {"name": "pve.home.arpa", "type": "A", "value": "192.168.10.10", "ttl": 60}
  ]
}
```

### `POST /api/dns/records`

```json
{"name": "nas.home.arpa", "type": "A", "value": "192.168.10.20", "ttl": 60}
```

### `DELETE /api/dns/records`

```json
{"name": "nas.home.arpa", "type": "A"}
```

### `GET /api/dns/status`

Returns upstream health, query count, and filter status.

## VPN

### `GET /api/vpn/peers`

```json
{
  "peers": [
    {"name": "laptop", "allowed_ips": ["10.44.0.2/32"], "latest_handshake": 1760000000, "online": true}
  ]
}
```

### `POST /api/vpn/peers`

```json
{"name": "phone", "allowed_ips": ["10.44.0.3/32"], "dns": "192.168.10.2"}
```

The response contains `config` **once**. It is never retrievable again.

### `DELETE /api/vpn/peers`

```json
{"name": "phone"}
```

### `GET /api/vpn/status`

Returns interface status, listen port, and handshake summary.

## Compute

### `GET /api/compute/vms`

```json
{
  "vms": [
    {"vmid": 100, "name": "dev-01", "status": "running", "node": "pve-1", "ip": "192.168.10.100"}
  ]
}
```

### `POST /api/compute/vms`

```json
{
  "template": "debian-12",
  "name": "dev-01",
  "cores": 2,
  "memory_mb": 2048,
  "auth": "key",
  "ssh_public_keys": ["ssh-ed25519 AAAA... user@example"]
}
```

The response includes `vmid`, `status`, and connection details. Passwords/private keys are returned once if generated.

### `POST /api/compute/vms/{vmid}/action`

```json
{"action": "start"}
```

Allowed: `start`, `shutdown`, `stop`, `reboot`.

### `DELETE /api/compute/vms/{vmid}`

Requires `{"confirm": "<vm-name>"}`.

### `GET /api/compute/templates`

Lists templates and their OS family. Templates are read-only; deletion is not exposed.

### `GET /api/compute/overview`

Node, storage, and capacity summary.

## Design rules

- All IDs are stable; names are not unique globally, so use IDs for writes.
- All timestamps are Unix seconds.
- All byte values are bytes, not GiB.
- List endpoints may return full lists; if an implementation paginates, it must be documented in its OpenAPI schema.
- Secrets are write-only. A `GET` never returns a password, private key, or token.
- Destructive calls require an explicit confirmation field.
