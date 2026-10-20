# Security policy

## Reporting a vulnerability

Please use GitHub's **Private vulnerability reporting** for this repository. Do not open a public issue with exploit details, credentials, or a live hostname.

Include:

- affected module (`dns`, `vpn`, `compute`, or `core`)
- version/commit
- reproduction steps
- impact
- suggested fix, if known

We aim to acknowledge within 7 days and to ship a fix or mitigation within 30 days for valid reports.

## In scope

- Authentication/authorization bypass in the console
- Secret leakage in logs, API responses, or generated configs
- Command injection in deployment scripts
- Unsafe defaults that expose an admin interface to the internet
- Supply-chain issues in pinned images

## Out of scope

- Misconfiguration by the operator (public admin port, weak password)
- Vulnerabilities in Proxmox VE, AdGuard Home, WireGuard, or wg-easy itself (report upstream)
- Social engineering
- Denial of service from an already-authenticated admin

## Safe harbor

We will not pursue legal action for good-faith research that:

- avoids privacy violations and data destruction
- uses test accounts and test infrastructure
- gives us reasonable time to fix before disclosure

## Operator checklist

- [ ] Admin UIs bound to LAN/VPN, not `0.0.0.0` on a public interface
- [ ] Public inbound limited to WireGuard UDP (and an authenticating HTTPS proxy if needed)
- [ ] Unique admin passwords; no defaults
- [ ] Secrets in a secret manager, not `topology.yaml`
- [ ] Backups encrypted and tested
- [ ] Images pinned and updated on a schedule
- [ ] `git secrets`/gitleaks scan clean before publishing a fork
