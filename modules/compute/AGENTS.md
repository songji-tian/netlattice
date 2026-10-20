# Compute module contract

Read the root [`AGENTS.md`](../../AGENTS.md) first. This file adds Proxmox-specific rules.

## Inputs

From `topology.yaml`:

- `spec.modules.compute.api_url`
- `spec.modules.compute.token_id`
- `spec.modules.compute.templates`
- `spec.modules.compute.defaults`

From the environment:

- `PVE_TOKEN_ID`
- `PVE_TOKEN_SECRET`
- `PVE_VERIFY_TLS` (default `true`)

## Preflight

1. Check API reachability:
   ```bash
   curl -fsS "$PVE_API_URL/api2/json/version" \
     -H "Authorization: PVEAPIToken=$PVE_TOKEN_ID=$PVE_TOKEN_SECRET"
   ```
2. Check the token's role and privileges. It needs the privileges in [`PVE_ROLE.md`](PVE_ROLE.md).
3. List templates and confirm every `vmid` in `topology.yaml` exists and is a template.
4. Check storage free space for a full clone.
5. Check that the target bridge/SDN is available.

If the token is `root@pam` or has `VM.Allocate` on `/`, warn the user and propose a scoped role.

## Apply

1. Clone the template (full clone, not linked) to a new VMID.
2. Set cores, memory, and disk as requested.
3. Inject cloud-init:
   - hostname
   - user
   - password and/or SSH public keys
   - IP configuration (DHCP or static)
4. Start the VM.
5. Wait for the guest agent (Linux) or a reachable RDP/SMB port (Windows).
6. Return connection details and a one-time credential if generated.

## Idempotency

- Match VMs by name **and** NetLattice tag.
- Never clone a second VM with the same name; return the existing one and report `no-op`.
- Do not delete a VM that lacks the `netlattice:<site>` tag.
- Templates are read-only. Never delete or modify a template.

## Verification gate

```bash
# 1. Health
curl -fsS "$PVE_API_URL/api2/json/version" -H "Authorization: PVEAPIToken=$PVE_TOKEN_ID=$PVE_TOKEN_SECRET"

# 2. Clone
# create a test VM via the console API or PVE API

# 3. Guest
# Linux: qemu-guest-agent responds
# Windows: RDP/SMB port reachable

# 4. Delete
# delete the test VM with name confirmation
```

Pass conditions:

- API 200.
- Test clone succeeds.
- Guest responds or is reachable.
- Test VM deletes successfully.
- Template still exists.

If no test template is available, mark clone verification `SKIPPED` with a reason.

## Rollback

- If clone fails, delete the partial VM by VMID.
- If cloud-init fails, do not delete the template; fix the cloud-init drive or image.
- If the guest agent is missing, document it and fall back to network reachability.
- Keep a log of VMID, name, node, and storage for every clone.

## Secrets

- PVE API token: secret manager or `.env.local`; never in `topology.yaml`.
- VM passwords: generated or user-supplied; return once, never store in state.
- SSH private keys: never accept, never store. Only public keys.
- Do not log the `Authorization` header.
