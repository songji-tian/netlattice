# Security model

NetLattice manages the control plane of a network. Treat it as production infrastructure even in a lab.

## Threat model

| Threat | Impact | Mitigation |
|---|---|---|
| Admin UI exposed to internet | Full DNS/VPN/VM control | Bind admin ports to LAN/VPN; reverse proxy with auth if public |
| Weak or reused admin password | Account takeover | Unique password; password hash; optional SSO/MFA at proxy |
| WireGuard private key leak | Network access | Per-peer keys; rotate; revoke; never commit |
| DNS poisoning / open resolver | Traffic redirection / abuse | Restrict recursion to LAN/VPN; DNSSEC upstreams; firewall |
| PVE token leak | VM lifecycle control | Dedicated role, token scope, rotate, LAN/VPN only |
| Agent prompt injection | Destructive actions | Plan + confirmation + ownership markers + untrusted-input rule |
| Supply-chain image compromise | Host compromise | Pin digests; read scripts; least privilege |
| Secret in logs/state | Credential leak | Redaction, file permissions, secret scan before publish |

## Trust boundaries

```text
Internet
  │  only WireGuard UDP (and optionally HTTPS via a hardened proxy)
  ▼
Edge host
  ├── AdGuard Home  :53 (LAN/VPN), :3000 (LAN/VPN only)
  ├── WireGuard     :51820/udp (public)
  └── wg-easy       :51821 (LAN/VPN only)
        │
        ▼
LAN / VPN overlay
  ├── Proxmox VE   :8006 (LAN/VPN only)
  └── NetLattice Console (LAN/VPN only)
```

Rules:

- Never bind `:3000`, `:51821`, or `:8006` to `0.0.0.0` on a public interface.
- If remote administration is required, put the admin UI behind a VPN or an authenticating reverse proxy.
- Keep the DNS resolver closed to the internet. An open resolver is a DDoS amplifier.

## Secrets inventory

| Secret | Where it lives | Rotation |
|---|---|---|
| AdGuard admin password | secret manager / `.env.local` | quarterly or on incident |
| WireGuard private keys | generated on host, delivered once | per peer; revoke on loss |
| wg-easy admin password hash | secret manager | quarterly |
| PVE API token | PVE user/token store + secret manager | quarterly |
| TLS private key | reverse proxy host | per certificate policy |
| SSH private keys | user's agent/keychain | per policy |

Never store any of the above in Git. `.env.example` contains names, not values.

## `.env.local` handling

- Mode `0600`.
- Owned by the deploying user.
- Excluded by `.gitignore`.
- Loaded by the deploy process, not committed.
- If the host supports systemd credentials or Docker secrets, prefer them.

Example `.env.example`:

```dotenv
ADGUARD_ADMIN_USER=admin
ADGUARD_ADMIN_PASSWORD=
WG_HOST=vpn.example.com
WG_ADMIN_PASSWORD_HASH=
PVE_API_URL=https://pve-1.home.arpa:8006
PVE_TOKEN_ID=
PVE_TOKEN_SECRET=
```

## Pre-publish secret scan

Before making a repository public:

```bash
# 1. Check for common secret patterns (adjust to your tooling)
gitleaks detect --source . --no-git

# 2. Check for private keys and certificates
find . -type f \( -name '*.key' -o -name '*.pem' -o -name '*.p12' -o -name '*.pfx' \) -print

# 3. Check for internal domains/IPs in tracked files
git grep -nE 'corp\.|\.internal|192\.168\.|10\.[0-9]+\.|172\.(1[6-9]|2[0-9]|3[01])\.' -- . ':!docs/*' || true

# 4. Check history, not just the working tree
git log -p --all | grep -nE 'BEGIN (RSA|OPENSSH|EC|PRIVATE) KEY|password|token|secret' | head
```

If a secret was ever committed, **rotate it**; deleting the file is not enough.

## Hardening checklist

- [ ] Admin ports bound to LAN/VPN
- [ ] Firewall default-deny inbound; only 51820/udp public
- [ ] SSH key-only; no root password login
- [ ] AdGuard recursion restricted to LAN/VPN
- [ ] WireGuard peers use `/32` allowed IPs
- [ ] PVE API token scoped to a dedicated role
- [ ] Containers pinned to versions/digests
- [ ] Backups encrypted and tested
- [ ] Logs redact secrets
- [ ] `.netlattice/` untracked
- [ ] Secret scan clean before publish

## Incident response

1. Revoke the affected credential (VPN peer, PVE token, admin password).
2. Rotate dependent secrets.
3. Check logs for unauthorized use.
4. Re-run verification gates.
5. Document the incident and the fix; add a regression check if possible.
