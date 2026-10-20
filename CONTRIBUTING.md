# Contributing

NetLattice is agent-first: a change is not complete until an agent can read the contract, apply it, and verify it.

## Ground rules

1. **No real infrastructure data.** No company domains, LAN IPs, usernames, hostnames, certificates, tokens, or topology exports. Use `home.arpa`, `example.com`, and RFC1918 addresses.
2. **Clean-room contributions.** If you port code from a private deployment, remove site-specific logic and secrets first. Do not copy private repository history.
3. **Contracts before code.** Update `AGENTS.md`, the module contract, and `topology.yaml` schema together with the implementation.
4. **Idempotent by default.** Re-running apply must not create duplicates or rotate keys.
5. **Destructive actions need confirmation.** Delete, revoke, restore, and template changes must be explicit.

## Development

```bash
python3 -m pip install pyyaml
python3 scripts/validate_topology.py examples/home-lab.yaml
python3 scripts/validate_topology.py examples/small-office.yaml
```

For compose changes:

```bash
cd modules/dns && docker compose config
cd modules/vpn && docker compose config
```

`docker compose config` requires the `.env` keys referenced by the file. Use the `.env.example` values for syntax checks.

## Pull requests

- Keep the diff focused.
- Explain the operator impact and the verification you ran.
- Include a test topology if you add a field.
- Do not include screenshots with real hostnames or IPs.
- Update `docs/topology-schema.md` for schema changes.

## Commit style

```text
<module>: <imperative summary>

Why:
- ...

Verified:
- ...
```

## License

By contributing, you agree that your contribution is licensed under Apache-2.0.
