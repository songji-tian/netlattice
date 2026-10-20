# Roadmap

## v0.1 — contract-first skeleton

- [x] `AGENTS.md` deployment contract
- [x] `topology.yaml` schema and validator
- [x] DNS, VPN, compute module contracts
- [x] Secret-free home-lab and small-office examples
- [x] Apache-2.0 license and CI validation
- [x] Public repository and `v0.1.0` release

## v0.2 — read-only reference console (current)

Clean-room FastAPI + static frontend, driven only by `topology.yaml`:

- [x] `GET /api/site` — topology summary, no secrets
- [x] `GET /api/dns` — normalized DNS records and AdGuard preview
- [x] `GET /api/vpn` — peer names, addresses, server preview
- [x] `GET /api/vpn/peers/{name}/config` — client config with key placeholders
- [x] `GET /api/compute` — template inventory and clone plan, no VM mutation
- [x] `GET /api/render` — safe preview bundle
- [x] `GET /openapi.json` — generated API contract
- [x] Unit/API tests and container build
- [ ] Live VM inventory/metrics (requires a real PVE connection; v0.3)
- [ ] Login, CSRF, rate limiting (only needed once writes exist; v0.3)
- [ ] Delete guard: templates never deletable; VMs require name confirmation (v0.3)

## v0.3 — agent runner and write path

- [ ] `netlattice plan` / `apply` / `verify` CLI
- [ ] Write-enabled console: login, CSRF, rate limiting, audit log
- [ ] Live PVE VM list/metrics and delete guard
- [ ] One-time credential display for created VMs
- [ ] DNS record and WireGuard peer apply with dry-run and rollback
- [ ] Machine-readable plan (`plan.json`) and verification (`verify.json`)
- [ ] Secret backends: env, file, 1Password, SOPS/age
- [ ] Idempotency tests against a disposable PVE cluster
- [ ] `topology diff` and drift detection

## v1.0 — stable

- [ ] Versioned module images
- [ ] Upgrade and rollback guides
- [ ] Backup/restore tested
- [ ] Security review
- [ ] Optional split into three standalone module repos, with this repo as the umbrella

## Split criteria

Keep one repo while:

- the schema and Agent contract change together
- modules share the same release cadence
- the reference console integrates all three

Split when a module has independent maintainers, release cadence, or a large codebase. The umbrella repo keeps the `topology.yaml` contract and links to module repos.
