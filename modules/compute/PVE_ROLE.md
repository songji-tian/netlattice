# Proxmox VE role for NetLattice

Create a dedicated role and API token. Do not use `root@pam`.

## Role

```text
NetLattice:
  VM.Allocate
  VM.Audit
  VM.Backup
  VM.Clone
  VM.Config.CDROM
  VM.Config.CPU
  VM.Config.Cloudinit
  VM.Config.Disk
  VM.Config.HWType
  VM.Config.Memory
  VM.Config.Network
  VM.Config.Options
  VM.Console
  VM.GuestAgent.Audit
  VM.GuestAgent.FileRead
  VM.GuestAgent.Unrestricted
  VM.Migrate
  VM.PowerMgmt
  VM.Snapshot
  VM.Snapshot.Rollback
  Datastore.Audit
  Datastore.AllocateSpace
  Sys.Audit
  SDN.Use
  SDN.Audit
```

## ACL paths

Apply with propagation:

- `/` — read/audit and VM lifecycle
- `/storage` — allocate space for clones
- `/sdn/zones/localnetwork/vmbr0` — `SDN.Use` for the target bridge

Adjust the SDN path to your actual bridge/zone.

## Token

1. Create a user, e.g. `netlattice@pve`.
2. Assign the `NetLattice` role on the ACL paths.
3. Create an API token with privilege separation **off** (or grant the same role to the token).
4. Store the token secret in your secret manager.

Test:

```bash
curl -fsS https://pve-1.home.arpa:8006/api2/json/version \
  -H "Authorization: PVEAPIToken=netlattice@pve!console=<secret>"
```

## Notes

- `VM.GuestAgent.Unrestricted` is powerful; only grant it if the console must change passwords or SSH keys on running VMs.
- `Datastore.AllocateSpace` is needed for full clones.
- If you use SDN, grant `SDN.Use` on the specific zone, not global.
- Rotate the token on a schedule and on any suspected leak.
