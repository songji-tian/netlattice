# Topology schema (`netlattice/v1`)

`topology.yaml` is the single source of truth. All addresses, domains, and credentials below are **examples**; replace them with your own.

## Minimal shape

```yaml
apiVersion: netlattice/v1
kind: Site
metadata:
  name: home-lab
spec:
  domains:
    internal: home.arpa
    public: example.com
  networks:
    lan:
      cidr: 192.168.10.0/24
      gateway: 192.168.10.1
      dns: 192.168.10.2
    vpn:
      cidr: 10.44.0.0/24
  nodes:
    - name: edge-1
      role: edge
      address: 192.168.10.2
    - name: pve-1
      role: compute
      address: 192.168.10.10
  modules:
    dns:
      enabled: true
      provider: adguard
      admin_port: 3000
      upstreams:
        - 1.1.1.1
        - 9.9.9.9
      records:
        - name: pve.home.arpa
          type: A
          value: 192.168.10.10
    vpn:
      enabled: true
      provider: wireguard
      endpoint: vpn.example.com:51820
      peers:
        - name: laptop
          allowed_ips:
            - 10.44.0.2/32
    compute:
      enabled: true
      provider: proxmox
      api_url: https://pve-1.home.arpa:8006
      templates:
        - name: debian-12
          vmid: 9001
```

## Top-level

| Field | Required | Notes |
|---|---|---|
| `apiVersion` | yes | Must be `netlattice/v1` |
| `kind` | yes | Must be `Site` |
| `metadata.name` | yes | DNS-label-safe; used as resource prefix |
| `spec` | yes | Site specification |

## `spec.domains`

| Field | Required | Notes |
|---|---|---|
| `internal` | yes | Reserved/internal zone, e.g. `home.arpa` or `lan.example.com` |
| `public` | no | Public zone, e.g. `example.com`; used only for VPN endpoint names |

Rules:

- Internal DNS records must end with `.internal`.
- Do not put real public domains in examples.
- `home.arpa` is reserved for home networks (RFC 8375) and is a good default.

## `spec.networks`

A map of network name → network.

| Field | Required | Notes |
|---|---|---|
| `cidr` | yes | IPv4 or IPv6 CIDR |
| `gateway` | no | Must be inside `cidr` |
| `dns` | no | DNS server address reachable from this network |
| `vlan` | no | Documentation only; the agent does not configure switches |

## `spec.nodes`

| Field | Required | Notes |
|---|---|---|
| `name` | yes | Unique; DNS-label-safe |
| `role` | yes | `edge`, `compute`, `control`, or `client` |
| `address` | yes | Management address |
| `ssh` | no | `{user, port, host}`; `host` overrides `address` |
| `tags` | no | Free-form labels |

## `spec.modules.dns`

| Field | Required | Notes |
|---|---|---|
| `enabled` | yes | Boolean |
| `provider` | yes | `adguard` |
| `admin_port` | no | Default `3000`; bind to LAN/VPN only |
| `upstreams` | no | Default `1.1.1.1`, `9.9.9.9` |
| `records` | no | List of A/AAAA/CNAME records |
| `filters` | no | AdGuard filter list URLs |

Record fields:

| Field | Required | Notes |
|---|---|---|
| `name` | yes | Must be inside `domains.internal` unless `external: true` |
| `type` | yes | `A`, `AAAA`, `CNAME` |
| `value` | yes | IP or target name |
| `ttl` | no | Seconds; default `60` |

## `spec.modules.vpn`

| Field | Required | Notes |
|---|---|---|
| `enabled` | yes | Boolean |
| `provider` | yes | `wireguard` |
| `endpoint` | yes | `host:port`; public DNS name or IP |
| `interface` | no | Default `wg0` |
| `peers` | no | List of peers |

Peer fields:

| Field | Required | Notes |
|---|---|---|
| `name` | yes | Unique; used as peer name |
| `allowed_ips` | yes | Inside `networks.vpn.cidr` |
| `public_key` | no | If absent, generate a keypair and deliver the private key once |
| `dns` | no | Defaults to `networks.lan.dns` |
| `persistent_keepalive` | no | Default `25` |

## `spec.modules.compute`

| Field | Required | Notes |
|---|---|---|
| `enabled` | yes | Boolean |
| `provider` | yes | `proxmox` |
| `api_url` | yes | PVE API base URL |
| `token_id` | no | Prefer API token over password |
| `templates` | no | Template inventory |
| `defaults` | no | Default cores/memory/storage |

Template fields:

| Field | Required | Notes |
|---|---|---|
| `name` | yes | Unique |
| `vmid` | yes | Existing PVE template VMID |
| `os` | no | `linux` or `windows` |
| `cloud_init` | no | Boolean; default `true` for Linux |

## Validation

```bash
python3 scripts/validate_topology.py topology.yaml
```

The validator checks structure, uniqueness, CIDR membership, DNS zone membership, and VPN peer addresses. It does **not** contact your infrastructure. Preflight does that.
