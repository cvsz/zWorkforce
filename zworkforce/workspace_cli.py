from __future__ import annotations

from . import cli
from .browser_effect_api import BrowserEffectApp


def main(argv=None):
    """Run the existing CLI while composing workspace and browser-effect routes into API serve mode."""
    previous = cli.App
    cli.App = BrowserEffectApp
    try:
        return cli.main(argv)
    finally:
        cli.App = previous
