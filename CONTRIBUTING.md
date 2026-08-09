# Contributing

1. Create a feature branch from `main`.
2. Run `make check`. For PostgreSQL changes, also set
   `ZWORKFORCE_TEST_POSTGRES_URL` to a real PostgreSQL service and run
   `make postgres-test`.
3. Add tests for behavior changes, including failure/recovery paths.
4. Keep mutations behind policy and approval controls.
5. Document new environment variables and migration behavior.
6. Open a focused PR and call out security/operational impact.

The project favors small auditable primitives over implicit autonomous behavior.

## Protected main

`main` requires a pull request, up-to-date CI/CodeQL/dependency checks,
conversation resolution, and has force-push/deletion protection with admin
enforcement. The repository currently has one collaborator, so the approval
count is `0` to avoid making self-authored pull requests unmergeable. Add an
independent maintainer/team before raising the approval count or requiring
code-owner review.
