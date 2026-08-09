## Summary
Describe the change and the production behavior it affects.

## Validation
- [ ] Unit/integration tests added or updated where behavior changed
- [ ] `python -m compileall -q zworkforce tests scripts`
- [ ] `python -m unittest discover -s tests -v`
- [ ] `python scripts/verify_release.py`
- [ ] `make check` (or equivalent individual gates)
- [ ] PostgreSQL integration run against a real service when applicable
- [ ] No `shell=True` in runtime and no provider secrets in static assets
- [ ] Docker/Compose or Kubernetes changes validated when applicable

## Security and operations
- [ ] No credentials, tokens, private keys or customer data are committed
- [ ] Authorization/policy boundaries remain fail-closed
- [ ] Mutating tools remain approval/policy gated
- [ ] Schema/data migrations are backward-compatible or documented
- [ ] Rollback and recovery impact is documented

## Release impact
- [ ] CHANGELOG/docs updated when user-visible behavior changes
- [ ] Version bump is included when release semantics require it
- [ ] New dependencies are necessary and reviewed
