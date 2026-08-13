---
name: zworkforce-artifact-provenance
description: Verify zWorkforce artifact provenance, hashes, content-addressed storage metadata, release evidence bundles, SBOMs, checksums, package assets, GHCR image digests, and rollback artifacts.
---

# zWorkforce Artifact Provenance

Treat artifacts as evidence objects. Verify exact hashes, owners, versions, and
storage locations before using them for release or compliance decisions.

## Workflow

1. Identify artifact type: task output, memory export, release asset, SBOM,
   checksum, container image, Windows package, backup, or evidence bundle.
2. Confirm content hash, size, owner, tenant or release scope, creation time,
   and producing task/workflow/commit.
3. Verify links from docs or release notes against actual local files, GitHub
   assets, or package metadata.
4. Check rollback and restore artifacts before declaring release readiness.
5. Record missing provenance as a release or compliance gap.

## References

- `zworkforce/artifacts.py`
- `scripts/generate_sbom.py`
- `scripts/verify_release.py`
- `docs/RELEASE.md`
- `docs/DISASTER-RECOVERY.md`
- `deploy/`

## Output

Report artifact IDs, hashes or digests, verification source, producer, consumer,
and gaps. Do not claim an artifact exists without direct evidence.
