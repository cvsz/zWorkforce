from __future__ import annotations

import argparse
from pathlib import Path
import re
import sys
import tomllib

ROOT = Path(__file__).resolve().parents[1]


def fail(message: str) -> None:
    raise SystemExit(f"release verification failed: {message}")


def package_version() -> str:
    data = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    return str(data["project"]["version"])


def init_version() -> str:
    text = (ROOT / "zworkforce" / "__init__.py").read_text(encoding="utf-8")
    match = re.search(r'^__version__\s*=\s*["\']([^"\']+)["\']\s*$', text, re.M)
    if not match:
        fail("zworkforce.__version__ is missing")
    return match.group(1)


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify zWorkforce release metadata is internally consistent")
    parser.add_argument("--expected", default="", help="expected semantic version without the v prefix")
    args = parser.parse_args()

    pyproject_version = package_version()
    module_version = init_version()
    expected = args.expected or pyproject_version

    if not re.fullmatch(r"\d+\.\d+\.\d+(?:[-+][0-9A-Za-z.-]+)?", expected):
        fail(f"invalid expected version {expected!r}")
    if pyproject_version != expected:
        fail(f"pyproject version {pyproject_version!r} != expected {expected!r}")
    if module_version != expected:
        fail(f"module version {module_version!r} != expected {expected!r}")

    changelog = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    if f"## {expected} " not in changelog and f"## {expected}\n" not in changelog:
        fail(f"CHANGELOG has no {expected} section")

    compose = (ROOT / "compose.yaml").read_text(encoding="utf-8")
    if f"zworkforce:{expected}" not in compose:
        fail(f"compose.yaml does not reference zworkforce:{expected}")

    canonical_k8s_tag = f"v{expected}"
    k8s = list((ROOT / "deploy" / "kubernetes").rglob("*.yaml"))
    image_refs = []
    for path in k8s:
        text = path.read_text(encoding="utf-8")
        image_refs.extend(re.findall(r"ghcr\.io/cvsz/zworkforce:([^\s\"']+)", text))
    stale = sorted({tag for tag in image_refs if tag != canonical_k8s_tag})
    if stale:
        fail(f"Kubernetes image tags are inconsistent; expected {canonical_k8s_tag}: {stale}")
    if not image_refs:
        fail("no Kubernetes zWorkforce image reference found")

    required = [
        ROOT / ".github" / "workflows" / "ci.yml",
        ROOT / ".github" / "workflows" / "codeql.yml",
        ROOT / ".github" / "workflows" / "release.yml",
        ROOT / "docs" / "PRODUCTION-READINESS.md",
        ROOT / "docs" / "DISASTER-RECOVERY.md",
        ROOT / "docs" / "RELEASE.md",
        ROOT / "docs" / "SECRET-MANAGEMENT.md",
        ROOT / "scripts" / "backup-postgres.sh",
        ROOT / "scripts" / "restore-postgres.sh",
        ROOT / "scripts" / "smoke-test.sh",
        ROOT / "scripts" / "generate_sbom.py",
    ]
    missing = [str(path.relative_to(ROOT)) for path in required if not path.exists()]
    if missing:
        fail(f"required release files missing: {', '.join(missing)}")

    print(f"release verification passed for zWorkforce {expected}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
