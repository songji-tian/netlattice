<!-- purpose: 给 AI 执行者的 VPN 模块部署手册 -->

# VPN · Agent Runbook

You are the deployment agent. Read the root [`AGENTS.md`](../../AGENTS.md) first. This file is the VPN-specific part of the runbook: use it to deploy and verify WireGuard, not as a user-facing manual.

Your job: give the user a working WireGuard endpoint, peers from `topology.yaml`, split DNS pointing at the DNS module, and a real handshake check when a peer is online. Stop when the verification gate passes.

## Inputs

From `topology.yaml`:

- `spec.modules.vpn.endpoint` — public `host:port`
- `spec.modules.vpn.interface` — default `wg0`
- `spec.modules.vpn.peers`
- `spec.networks.vpn.cidr`
- `spec.networks.lan.dns`

From the environment:

- `WG_HOST` — public hostname/IP for peer configs
- `WG_ADMIN_PASSWORD_HASH` — wg-easy admin password hash
- `VPN_ADMIN_BIND` — admin UI bind address (default `127.0.0.1`)
- `WG_DEFAULT_DNS` — usually the DNS module address

## Apply

1. Check that `51820/udp` is free and that the host has `NET_ADMIN`.
2. Start the container:
   ```bash
   docker compose up -d
   ```
3. Wait for the admin UI:
   ```bash
   curl -fsS http://127.0.0.1:51821/ >/dev/null
   ```
4. Create peers from `topology.yaml`. If a peer has no `public_key`, generate a keypair and deliver the config once.
5. Set peer DNS to the DNS module address.
6. Apply NAT/firewall rules only for the VPN CIDR and LAN CIDR.
7. Verify.

## Idempotency

- Match peers by `name`.
- Do not recreate an existing peer with the same name; update allowed IPs instead.
- If a peer's public key changed, treat it as a key rotation and confirm with the user.
- Do not delete peers that are not in `topology.yaml` unless they carry the `netlattice` marker.

## Verification gate

```bash
# wg-easy uses a bridged network; the host cannot see the interface.
docker exec netlattice-wg-easy wg show
docker exec netlattice-wg-easy wg show <iface> latest-handshakes
```

Pass conditions:

- Interface exists.
- Peer count matches the topology (or extra peers are documented).
- At least one handshake within 5 minutes, if a peer is expected online.
- From a peer: internal DNS resolves and a LAN host is reachable.

If no peer is online, mark the handshake check `SKIPPED`, not `PASS`.

## Rollback

- Back up `/etc/wireguard/` (or the container's `./data`) before changes.
- To roll back a peer, restore the previous config and restart the interface.
- To revoke a peer, remove it from the config and `wg syncconf`; do not just delete the UI entry if the config still contains the key.

## Secrets

- Private keys are generated on the host and delivered once.
- Never print a private key in a report.
- Never commit `./data`, `*.conf`, or `*.key`.
- `WG_ADMIN_PASSWORD_HASH` is a hash, but still treat it as a secret.
