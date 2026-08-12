from pathlib import Path
import unittest


DEPENDABOT = Path(__file__).resolve().parents[1] / ".github" / "dependabot.yml"
ZARVIS_WORKFLOW = Path(__file__).resolve().parents[1] / ".github" / "workflows" / "zarvis.yml"


def dependency_directories(config: str) -> set[tuple[str, str]]:
    pairs = set()
    ecosystem = None
    for raw_line in config.splitlines():
        line = raw_line.strip()
        if line.startswith("- package-ecosystem:"):
            ecosystem = line.split(":", 1)[1].strip()
        elif ecosystem and line.startswith("directory:"):
            pairs.add((ecosystem, line.split(":", 1)[1].strip()))
            ecosystem = None
    return pairs


class DependabotCoverageTests(unittest.TestCase):
    def test_migrated_zarvis_ecosystems_are_monitored(self):
        configured = dependency_directories(DEPENDABOT.read_text(encoding="utf-8"))
        expected = {
            ("npm", "/packages/zarvis"),
            ("pip", "/packages/zarvis/apps/zaicoder/backend"),
            ("pip", "/packages/zarvis/services/zarvis-api"),
            ("pip", "/packages/zarvis/services/zc"),
            ("gomod", "/packages/zarvis/tools/zctl"),
            ("nuget", "/packages/zarvis/apps/zarvis-windows"),
        }

        self.assertLessEqual(expected, configured)

    def test_child_directory_does_not_cover_parent_or_wrong_ecosystem(self):
        config = """updates:
  - package-ecosystem: pip
    directory: /packages/zarvis
  - package-ecosystem: npm
    directory: /packages/zarvis/services/ai-gateway
"""

        configured = dependency_directories(config)
        self.assertNotIn(("npm", "/packages/zarvis"), configured)

    def test_zarvis_api_dependency_tests_run_in_zarvis_ci(self):
        workflow = ZARVIS_WORKFLOW.read_text(encoding="utf-8")

        self.assertIn("zarvis-api:", workflow)
        self.assertIn("pip install --no-cache-dir -r requirements.txt pytest", workflow)
        self.assertIn("python -m pytest tests -q", workflow)


if __name__ == "__main__":
    unittest.main()
