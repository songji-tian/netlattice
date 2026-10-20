# Roadmap

## v0.1 — contract-first skeleton (current)

- [x] `AGENTS.md` deployment contract
- [x] `topology.yaml` schema and validator
- [x] DNS, VPN, compute module contracts
- [x] Secret-free home-lab and small-office examples
- [x] Apache-2.0 license and CI validation
- [ ] Public repository

## v0.2 — reference console

Extract a clean-room FastAPI + static frontend from the private PVE console:

- [ ] `GET /api/site` — topology summary, no secrets
- [ ] `GET /api/dns/records` — normalized AdGuard records
- [ ] `GET /api/vpn/peers` — peer names, handshakes, no private keys
- [ ] `GET /api/compute/vms` — VM list, metrics, template guard
- [ ] Login, CSRF, rate limiting
- [ ] One-time credential display
- [ ] Delete guard: templates never deletable; VMs require name confirmation

## v0.3 — agent runner

- [ ] `netlattice plan` / `apply` / `verify` CLI
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
