from __future__ import annotations

from . import cli
from .workspace_evidence_api import WorkspaceEvidenceApp


def main(argv=None):
    """Run the existing CLI while composing workspace/context/command/evidence routes into API serve mode."""
    previous = cli.App
    cli.App = WorkspaceEvidenceApp
    try:
        return cli.main(argv)
    finally:
        cli.App = previous
