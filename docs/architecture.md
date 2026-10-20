# Architecture

## Design goals

1. **One source of truth.** A site is described by `topology.yaml`, not by a pile of shell history.
2. **Agent-executable, human-auditable.** `AGENTS.md` is a contract, not a suggestion. Humans can read the same plan and verification output.
3. **Composable modules.** DNS, VPN, and compute can be deployed alone or together.
4. **Boring defaults.** AdGuard Home, WireGuard, and Proxmox VE are mature, well-understood building blocks.
5. **No secret sprawl.** Secrets are injected at deploy time and never persisted in Git or state files.
6. **Safe by default.** Management planes bind to LAN/VPN; only the VPN UDP port (and optionally an HTTPS entry) faces the public internet.

## Control plane vs data plane

```text
Control plane                     Data plane
─────────────                     ──────────
topology.yaml                     AdGuard Home   :53, :3000
AGENTS.md                         WireGuard      :51820/udp
scripts/validate_topology.py      wg-easy        :51821
console/ (read-only projection)    Proxmox VE     :8006
.netlattice/plan.json
.netlattice/state.json
```

The control plane is deliberately small: a YAML file, a validation script, an agent contract, and a read-only console projection. The heavy lifting is done by the data-plane components.

The v0.2 console reads the same `topology.yaml` and renders safe previews. It does not hold credentials, mutate state, or call infrastructure APIs; apply remains the deployment agent's job.

## Why one repository with three modules?

Three separate repositories would be cleaner for release engineering, but worse for the primary use case: an agent deploying a whole site.

Problems with three repos:

- The agent must discover and reconcile three version sets.
- Cross-module invariants (VPN DNS pointing at AdGuard, compute guests using the VPN DNS) have no single owner.
- A “one-line deploy” becomes three prompts and three plans.
- Examples and topology schema drift.

The single-repo approach keeps one version, one schema, and one deployment contract. Each module is still isolated in `modules/<name>/` with its own `AGENTS.md`, so it can be extracted into a standalone repository later without changing the contract.

If a module grows its own release cadence, use Git subtree or a release mirror; do not fork the contract.

## Module boundaries

### DNS

Owns:

- AdGuard Home container and config
- upstream selection
- internal DNS rewrites
- filter lists
- optional DHCP (disabled by default)

Does not own:

- public DNS records (use your registrar/Cloudflare)
- TLS certificates
- VPN peer routing

### VPN

Owns:

- WireGuard interface and keys
- peer lifecycle
- NAT/firewall rules needed for the overlay
- wg-easy admin surface (optional)

Does not own:

- DNS records (it configures peers to *use* the DNS module)
- VM lifecycle
- public reverse proxy

### Compute

Owns:

- Proxmox VE API client
- template inventory
- clone/start/stop/delete lifecycle
- cloud-init injection
- console UI/API

Does not own:

- PVE cluster installation
- storage/network fabric configuration
- DNS/VPN routing

## Deployment order

```text
validate → preflight → plan
            │
            ▼
          DNS  ──► verify DNS
            │
            ▼
          VPN  ──► verify handshake + VPN DNS
            │
            ▼
        Compute ──► verify API + clone + guest DNS
```

DNS first because VPN peers and compute guests both need name resolution. VPN second because remote verification of compute may depend on it. Compute last because it is the most destructive and slowest module.

## State model

`.netlattice/` is local and untracked:

```text
.netlattice/
├── preflight.json
├── plan.json
├── state.json
├── backups/
└── logs/
```

`state.json` records resource IDs and ownership markers, not secrets. It is used for idempotency and cleanup. If it is lost, the agent must re-discover resources by name/tag before creating anything.

## Ownership markers

Every managed resource should carry a marker:

- Docker: label `netlattice.site=<site>`, `netlattice.module=<module>`
- DNS rewrite: comment/metadata where supported
- WireGuard peer: name prefix `<site>-`
- PVE VM: tag `netlattice:<site>`, description marker

The marker prevents an agent from deleting a user's unrelated VM or DNS record.

## Failure domains

| Failure | Blast radius | Mitigation |
|---|---|---|
| DNS misconfigured | Whole site name resolution | Keep previous config backup; verify with `dig` before switching |
| VPN key leak | Network access | Rotate peer keys; revoke by peer name; audit handshakes |
| PVE token leak | VM lifecycle | Scope token to a dedicated role; rotate; bind to LAN/VPN |
| Agent misbehaves | Could delete resources | Plan + destructive confirmation + ownership markers |
| Container compromise | Host network | Pin images; drop capabilities; bind admin ports to LAN/VPN |

## Non-goals

- Replacing Terraform/Ansible for large-scale infrastructure.
- Managing public DNS or public certificates.
- Multi-tenant RBAC.
- Kubernetes.
- Being a general-purpose CMDB.

NetLattice is opinionated: a small site, a small set of primitives, and an agent that can reason about the whole thing.
