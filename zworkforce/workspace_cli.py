from __future__ import annotations

from . import cli
from .workspace_command_api import WorkspaceCommandApp


def main(argv=None):
    """Run the existing CLI while composing workspace/context/command routes into API serve mode."""
    previous = cli.App
    cli.App = WorkspaceCommandApp
    try:
        return cli.main(argv)
    finally:
        cli.App = previous
