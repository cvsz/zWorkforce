from __future__ import annotations

from . import cli
from .artifact_content_api import ArtifactContentApp


def main(argv=None):
    """Run the existing CLI while composing workspace, browser-effect and artifact-content routes."""
    previous = cli.App
    cli.App = ArtifactContentApp
    try:
        return cli.main(argv)
    finally:
        cli.App = previous
