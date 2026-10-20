# Open-source release checklist

Run before every public push.

## Secrets

- [ ] No `.env`, `.env.local`, `*.key`, `*.pem`, `*.conf`, `data/`, `work/`, `conf/`
- [ ] No tokens, passwords, API keys, cookie values, private keys
- [ ] No real public IPs, LAN IPs, hostnames, domains, SSIDs, usernames, emails
- [ ] No screenshots with terminal history or browser autofill
- [ ] `git log -p` reviewed, not just the working tree
- [ ] Secret scanner clean (gitleaks/trufflehog)
- [ ] Git history rewritten if a secret was ever committed

## Identity

- [ ] Generic `home.arpa`, `example.com`, RFC1918 addresses
- [ ] No company name, customer name, internal project name
- [ ] No private repository URLs or issue links
- [ ] License and copyright holder confirmed

## Code

- [ ] Clean-room extraction: no site-specific branches, comments, or config
- [ ] No hardcoded credentials or fallback passwords
- [ ] Admin ports bind to localhost/LAN/VPN by default
- [ ] Destructive operations require confirmation
- [ ] Templates are read-only
- [ ] Logs redact secrets

## Verification

- [ ] `python3 scripts/validate_topology.py examples/*.yaml`
- [ ] `docker compose config` for each module
- [ ] CI green
- [ ] README one-line prompt works with a fresh agent
- [ ] Test deployment on a clean VM, not the author's machine

## Legal

- [ ] Apache-2.0 `LICENSE`
- [ ] `SECURITY.md` with private reporting
- [ ] `CONTRIBUTING.md` with clean-room rule
- [ ] Third-party licenses reviewed
- [ ] No copied code with incompatible license
