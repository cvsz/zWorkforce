# Contributing

1. Create a feature branch from `main`.
2. Run `make check` and `python -m zworkforce doctor`.
3. Add tests for behavior changes, including failure/recovery paths.
4. Keep mutations behind policy and approval controls.
5. Document new environment variables and migration behavior.
6. Open a focused PR and call out security/operational impact.

The project favors small auditable primitives over implicit autonomous behavior.
