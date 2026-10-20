# DNS module — AdGuard Home

LAN DNS with internal names, upstream split, filtering, and query visibility.

## What it provides

- Recursive DNS for LAN and VPN clients
- Internal A/AAAA/CNAME records from `topology.yaml`
- Upstream selection (plain DNS, DoH, DoT)
- Filter lists and query log
- Optional DHCP (off by default)

## What it does not do

- Public DNS hosting
- TLS certificates
- VPN routing

## Compose

```bash
cd modules/dns
cp .env.example .env
# edit .env: set DNS_ADMIN_BIND to the LAN/VPN address if remote admin is needed
docker compose up -d
```

Default ports:

| Port | Purpose | Exposure |
|---|---|---|
| `53/tcp`, `53/udp` | DNS | LAN/VPN |
| `3000/tcp` | AdGuard setup/admin | **localhost by default** |

If you need the admin UI from another machine, set:

```dotenv
DNS_ADMIN_BIND=192.168.10.2
```

Do not bind it to a public interface.

## First-run

1. Open `http://<dns-admin-bind>:3000/`.
2. Complete AdGuard Home's setup wizard.
3. Set the admin username/password. Store it in your secret manager.
4. Set upstreams from `topology.yaml`.
5. Add the internal rewrites from `topology.yaml`.
6. Point LAN DHCP's DNS setting at this host (or configure it manually).

## Verification

```bash
# Internal record
dig @192.168.10.2 pve.home.arpa +short

# External resolution through the resolver
dig @192.168.10.2 example.com +short

# Admin UI
curl -fsS http://192.168.10.2:3000/ >/dev/null && echo admin-ok
```

Expected:

- `pve.home.arpa` returns the address from `topology.yaml`.
- `example.com` resolves (or is filtered as configured).
- Admin UI returns HTTP 200.

## API

AdGuard Home exposes its own API. For NetLattice's normalized contract, see [`docs/api/README.md`](../../docs/api/README.md#dns).

Common operations:

- `GET /control/status`
- `GET /control/rewrite/list`
- `POST /control/rewrite/add`
- `POST /control/rewrite/delete`
- `GET /control/stats`

Use HTTP Basic auth with the AdGuard admin credentials. Never put credentials in a URL.

## Notes

- Port 53 is often occupied by `systemd-resolved`. On Ubuntu/Debian, disable its DNS stub listener or bind AdGuard to a dedicated IP.
- If AdGuard is also the DHCP server, disable the router's DHCP to avoid two servers.
- Keep the query log retention short on small disks.
