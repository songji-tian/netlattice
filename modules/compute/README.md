# Compute module — Proxmox VE

Fast, clean test/dev environments from templates.

## What it provides

- Template inventory
- Full clone → CPU/memory → cloud-init → optional start
- Linux password/key/both login modes
- Windows template clone with built-in administrator flow
- VM lifecycle: start, shutdown, stop, reboot, delete
- Per-VM metrics and host overview
- HTTP API and browser console

## What it does not do

- Install Proxmox VE
- Configure cluster/storage/network fabric
- Manage public DNS or VPN

## Prerequisites

- Proxmox VE 8.x/9.x
- A template VMID for each OS family
- An API token scoped to the `NetLattice` role (see [`PVE_ROLE.md`](PVE_ROLE.md))
- Network reachability from the console to `https://<pve>:8006`
- Cloud-init drive on Linux templates
- Guest agent on templates (recommended)

## Minimal flow

```text
list templates → clone full → set cores/memory → inject cloud-init
→ start → wait for guest agent → return connection details
```

## Login modes (Linux)

| `auth` | Behavior |
|---|---|
| `password` | Set `ciuser` password; enable sshd password login; clear inherited keys |
| `key` | Inject SSH public keys only; password login remains disabled |
| `both` | Password + keys (default) |

Windows templates ignore `auth`; use the built-in administrator account and the template's provisioning method.

## SSH public keys

The `ssh_public_keys` field takes the **text content** of one or more `.pub` files, one key per line:

```text
ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAA... user@example
```

Do not paste a private key. Do not pass a file path unless the API explicitly supports it.

## Verification

```bash
# API health
curl -fsS https://pve-1.home.arpa:8006/api2/json/version \
  -H "Authorization: PVEAPIToken=<token-id>=<secret>"

# Clone a test VM, then delete it
curl -fsS -X POST https://console.home.arpa/api/compute/vms \
  -H 'Content-Type: application/json' \
  -d '{"template":"debian-12","name":"netlattice-test","cores":2,"memory_mb":2048}'
```

Pass conditions:

- API returns authenticated 200.
- Clone completes and the VM appears in the list.
- Guest agent responds (Linux) or the VM is reachable (Windows).
- Delete with the correct name confirmation succeeds.
- Template is still present after the test.

## Console

The reference console is a FastAPI service with a static frontend. It exposes the contract in [`docs/api/README.md`](../../docs/api/README.md#compute). The open-source extraction is tracked in the roadmap; until then, the API contract is the stable integration surface.

The sanitized reference HTTP API is in [`API.md`](API.md): 13 operations covering health, login, VM list/detail, power actions, clone, delete, credentials, templates, overview, and audit logs. It is a contract reference, not yet the v0.1 server implementation.

## Security

- Bind the console and PVE API to LAN/VPN only.
- Use a dedicated API token, not `root@pam` password.
- Do not expose `:8006` to the internet.
- Never return passwords or private keys in `GET` responses.
- Treat templates as read-only; do not delete them from the console.
