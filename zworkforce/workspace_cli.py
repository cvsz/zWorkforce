from __future__ import annotations

from . import cli
from .workspace_grant_api import WorkspaceGrantApp


def main(argv=None):
    """Run the existing CLI while composing workspace/context/command/evidence/grant routes into API serve mode."""
    previous = cli.App
    cli.App = WorkspaceGrantApp
    try:
        return cli.main(argv)
    finally:
        cli.App = previous
