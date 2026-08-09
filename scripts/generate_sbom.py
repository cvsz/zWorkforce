from __future__ import annotations

import argparse
from datetime import datetime, timezone
from importlib import metadata
import json
from pathlib import Path
from urllib.parse import quote
import uuid


def normalize(name: str) -> str:
    return name.strip().lower().replace("_", "-")


def purl(name: str, version: str) -> str:
    return f"pkg:pypi/{quote(normalize(name))}@{quote(version)}"


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate a deterministic CycloneDX JSON SBOM from the installed Python environment")
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    components: dict[tuple[str, str], dict[str, str]] = {}
    for dist in metadata.distributions():
        name = dist.metadata.get("Name")
        version = dist.version
        if not name or not version:
            continue
        key = (normalize(name), version)
        components[key] = {
            "type": "library",
            "name": name,
            "version": version,
            "purl": purl(name, version),
        }

    root_version = metadata.version("zworkforce")
    timestamp = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    bom = {
        "bomFormat": "CycloneDX",
        "specVersion": "1.5",
        "serialNumber": f"urn:uuid:{uuid.uuid4()}",
        "version": 1,
        "metadata": {
            "timestamp": timestamp,
            "component": {
                "type": "application",
                "name": "zworkforce",
                "version": root_version,
                "purl": purl("zworkforce", root_version),
            },
            "tools": {
                "components": [
                    {
                        "type": "application",
                        "name": "zWorkforce built-in SBOM generator",
                        "version": root_version,
                    }
                ]
            },
        },
        "components": [components[key] for key in sorted(components)],
    }

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(bom, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
