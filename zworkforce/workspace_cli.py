from __future__ import annotations

from . import cli
from .workspace_context_api import WorkspaceContextApp


def main(argv=None):
    """Run the existing CLI while composing workspace/context routes into API serve mode."""
    previous = cli.App
    cli.App = WorkspaceContextApp
    try:
        return cli.main(argv)
    finally:
        cli.App = previous
