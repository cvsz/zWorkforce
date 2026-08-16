from __future__ import annotations

from . import cli
from .workspace_api import WorkspaceApp


def main(argv=None):
    """Run the existing CLI while composing workspace routes into API serve mode."""
    previous = cli.App
    cli.App = WorkspaceApp
    try:
        return cli.main(argv)
    finally:
        cli.App = previous
