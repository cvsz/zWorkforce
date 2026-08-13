from pathlib import Path
import unittest

from zworkforce import __version__


ROOT = Path(__file__).resolve().parents[1]


class StaticAssetTests(unittest.TestCase):
    def test_dashboard_version_matches_package_version(self):
        html = (ROOT / "zworkforce" / "static" / "index.html").read_text(encoding="utf-8")
        self.assertIn(f"zWorkforce v{__version__}", html)
        self.assertIn(f'class="version">v{__version__}</span>', html)
        self.assertNotIn("v2.0.0", html)

    def test_dashboard_exposes_prometa_install_action(self):
        html = (ROOT / "zworkforce" / "static" / "index.html").read_text(encoding="utf-8")
        app = (ROOT / "zworkforce" / "static" / "app.js").read_text(encoding="utf-8")
        self.assertIn("prometaInstallBtn", html)
        self.assertIn("/api/v1/prometa/install", app)


if __name__ == "__main__":
    unittest.main()
