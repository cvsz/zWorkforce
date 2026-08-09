# Release Process

zWorkforce releases are tag-driven and must originate from a commit reachable from `main`.

## Preconditions

Before creating a release tag:

1. Merge the intended release commit to `main`.
2. Confirm CI and CodeQL are green.
3. Confirm `pyproject.toml`, `zworkforce.__version__`, Compose/Kubernetes image references and `CHANGELOG.md` carry the same version.
4. Run `python scripts/verify_release.py` locally or rely on the mandatory CI release-integrity job.
5. Confirm production migration/rollback notes are current.

## Tag format

Use an immutable semantic version tag:

```bash
git checkout main
git pull --ff-only
git tag -a v3.0.2 -m 'zWorkforce v3.0.2'
git push origin v3.0.2
```

Do not move or reuse an existing release tag. Publish a new patch/minor/major version instead.

## Automated release outputs

`.github/workflows/release.yml` validates the tag against package metadata and verifies that the tagged commit is reachable from `main`. If validation succeeds it produces:

- source distribution (`sdist`);
- Python wheel;
- CycloneDX JSON SBOM;
- SHA-256 checksums;
- GitHub artifact bundle;
- GitHub build-provenance attestation for distribution artifacts;
- GHCR image tagged with the release tag and `latest`;
- OCI provenance and SBOM from BuildKit;
- GitHub Release with generated release notes and attached artifacts.

Production deployments should pin the semantic tag or image digest, never `latest`.

## Trusted Windows signing

The pull-request Windows workflow deliberately uses a short-lived self-signed
certificate for package installation smoke tests. A release tag is
fail-closed unless the repository or protected release environment provides:

- `WINDOWS_MSIX_PFX_BASE64`: base64-encoded organization-issued MSIX signing
  PFX containing its private key;
- `WINDOWS_MSIX_PFX_PASSWORD`: the PFX password; and optionally
- `WINDOWS_MSIX_PUBLISHER`: the exact certificate subject to use as the MSIX
  publisher (otherwise the package script derives it from the certificate).

The release workflow imports the PFX only on the ephemeral Windows runner,
patches the package publisher to match the signing identity, and publishes
only the public `.cer` beside the MSIX. Never commit the PFX, password, or a
base64 value to the repository. A missing or invalid signing secret blocks the
release instead of producing a package that users cannot trust.

## Release verification

After the workflow finishes:

1. Inspect the GitHub Release and workflow conclusion.
2. Verify downloaded files against `SHA256SUMS`.
3. Inspect provenance/attestation in GitHub Actions.
4. Pull the exact image tag/digest and run `zworkforce --version`.
5. Deploy first to a staging environment backed by PostgreSQL.
6. Run `zworkforce doctor` and `scripts/smoke-test.sh`.
7. Exercise one durable task, one workflow, one approval path, scheduler
   occurrence deduplication, and outbox claim/retry behavior before promotion.

## Hotfixes

Hotfixes use the same flow. Create a branch from the affected release/main state, fix and validate it, merge to `main`, bump the patch version, update `CHANGELOG.md`, then publish a new immutable tag.

## Rollback

Application rollback is performed by redeploying the previous immutable image tag/digest. Database rollback is a separate destructive operation and must follow `docs/DISASTER-RECOVERY.md`; do not restore a database merely to roll back application code unless data/schema compatibility requires it.

## External publication

The repository release workflow publishes to GitHub Releases/GHCR. Publishing to PyPI or another registry is intentionally not automatic until trusted-publishing ownership and release policy for that external registry are configured.
