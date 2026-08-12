from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
ZARVIS = ROOT / "packages" / "zarvis"


class ZarvisApiRenameTests(unittest.TestCase):
    def test_old_service_directory_and_runtime_identifiers_are_removed(self):
        self.assertFalse((ZARVIS / "services" / "phase6-api").exists())
        self.assertTrue((ZARVIS / "services" / "zarvis-api").is_dir())

        stale = []
        for path in ZARVIS.rglob("*"):
            if not path.is_file() or ".git" in path.parts:
                continue
            try:
                content = path.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                continue
            if any(
                old in content
                for old in ("phase6-api", "PHASE6_API_URL", "PHASE6_API_TOKEN")
            ):
                stale.append(str(path.relative_to(ROOT)))

        self.assertEqual(stale, [])


if __name__ == "__main__":
    unittest.main()
