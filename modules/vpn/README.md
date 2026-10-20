# VPN module — WireGuard

Public ingress to the LAN, remote development, and optional site-to-site links.

## What it provides

- WireGuard interface and peer lifecycle
- One-time peer config delivery
- Split-horizon DNS pointing at the DNS module
- NAT/firewall rules for the overlay
- Optional wg-easy web UI

## What it does not do

- Public DNS
- TLS termination
- VM lifecycle

## Compose

```bash
cd modules/vpn
cp .env.example .env
# edit .env: WG_HOST, PASSWORD_HASH, WG_DEFAULT_DNS
docker compose up -d
```

Default ports:

| Port | Purpose | Exposure |
|---|---|---|
| `51820/udp` | WireGuard | public |
| `51821/tcp` | wg-easy admin | **localhost by default** |

If you need the admin UI from the LAN or VPN, set:

```dotenv
VPN_ADMIN_BIND=192.168.10.2
```

Never expose `51821` directly to the internet. Put it behind VPN or an authenticating proxy.

## `WG_HOST`

`WG_HOST` is the address peers use to reach the VPN. It must be:

- a public DNS name (`vpn.example.com`) that resolves to your edge, or
- a public IP.

It is **not** the LAN address of the edge host, unless the edge is directly reachable from the internet.

## Keys

- Each peer gets its own keypair.
- The private key is shown **once** when the peer is created.
- Never reuse a peer config across devices.
- Revoke a peer by name if a device is lost.

## Verification

On the edge:

```bash
wg show
wg show wg0 latest-handshakes
```

From a peer:

```bash
ping -c 3 192.168.10.10
dig @192.168.10.2 pve.home.arpa +short
```

Pass conditions:

- `wg show` lists the expected interface and peer count.
- At least one peer has a handshake within 5 minutes.
- The peer resolves internal names through the DNS module.
- The peer reaches a compute guest (if compute is enabled).

## Firewall

Minimum public inbound:

- `51820/udp`

Everything else should be denied by default. If you use a cloud firewall, allow UDP 51820 only.

## API

See [`docs/api/README.md`](../../docs/api/README.md#vpn). wg-easy also exposes its own API; the NetLattice contract is the stable surface for agents.

## Notes

- If the edge is behind CGNAT, use a public relay or a site-to-site tunnel; `WG_HOST` alone will not fix reachability.
- Keep `WG_ALLOWED_IPS` narrow. Do not route all traffic through the VPN unless the user explicitly wants a full tunnel.
- If DNS is not reachable from the peer, check `WG_DEFAULT_DNS` and the DNS firewall rules before changing WireGuard keys.
