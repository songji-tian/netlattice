<!-- purpose: 给 AI 执行者的 DNS 模块部署手册 -->

# DNS · Agent Runbook

You are the deployment agent. Read the root [`AGENTS.md`](../../AGENTS.md) first. This file is the DNS-specific part of the runbook: use it to deploy and verify AdGuard Home, not as a user-facing manual.

Your job: make `spec.networks.lan.dns` answer internal names from `topology.yaml`, forward upstream, and keep the admin UI off the public internet. Stop when the verification gate passes.

## Inputs

From `topology.yaml`:

- `spec.networks.lan.dns` — the address clients should use
- `spec.modules.dns.upstreams`
- `spec.modules.dns.records`
- `spec.modules.dns.filters`
- `spec.modules.dns.admin_port`

From the environment:

- `DNS_ADMIN_BIND` — address to bind the admin UI (default `127.0.0.1`)
- `ADGUARD_ADMIN_USER`, `ADGUARD_ADMIN_PASSWORD` — only for API automation

## Apply

1. Check port 53:
   ```bash
   ss -lntup | grep ':53 '
   ```
   If `systemd-resolved` owns it, stop its stub listener or bind AdGuard to a dedicated address. Do not kill an unrelated DNS server without asking.
2. Start the container:
   ```bash
   docker compose up -d
   ```
3. Wait for health:
   ```bash
   curl -fsS http://127.0.0.1:3000/ >/dev/null
   ```
4. Complete the first-run wizard if the config is empty. Ask the user for the admin password; do not generate and hide it.
5. Apply upstreams and rewrites via the AdGuard API or UI.
6. Verify each record with `dig`.

## Idempotency

- Read existing rewrites before adding.
- Match by `(name, type)`.
- If the value differs, update it; do not create a duplicate.
- Do not delete records that are not in `topology.yaml` unless they carry the `netlattice` marker.

## Verification gate

```bash
dig @<dns-ip> <internal-name> +short
dig @<dns-ip> example.com +short
curl -fsS http://<dns-admin-bind>:3000/ >/dev/null
```

All three must pass. If a record is intentionally external, skip it with a reason.

## Rollback

- Back up `modules/dns/conf/` and `modules/dns/work/` before changing rewrites.
- On failure, restore the previous `AdGuardHome.yaml` and restart the container.
- Never delete the query log or filter database as a “fix”.

## Secrets

- Admin password: secret manager or `.env.local`, mode `0600`.
- Do not log the `Authorization` header.
- Do not store the password in `topology.yaml`.
