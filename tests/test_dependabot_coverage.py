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

    def test_node_ci_rejects_peer_dependency_conflicts(self):
        workflow = ZARVIS_WORKFLOW.read_text(encoding="utf-8")

        self.assertIn("pnpm peers check", workflow)

    def test_zarvis_workflow_resolves_all_zc_dependency_sets(self):
        workflow = ZARVIS_WORKFLOW.read_text(encoding="utf-8")

        self.assertIn("zc-dependency-resolution:", workflow)
        self.assertIn("pip install --dry-run", workflow)
        self.assertIn("-r app/requirements.txt", workflow)
        self.assertIn("-r requirements-dev.txt", workflow)
        self.assertIn("-r requirements-enterprise.txt", workflow)
        self.assertIn("-r webapp/requirements-web.txt", workflow)

    def test_unsupported_node_majors_are_ignored(self):
        config = DEPENDABOT.read_text(encoding="utf-8")

        self.assertIn('dependency-name: "eslint"', config)
        self.assertIn('dependency-name: "typescript"', config)
        self.assertGreaterEqual(config.count("update-types: [version-update:semver-major]"), 2)


if __name__ == "__main__":
    unittest.main()
