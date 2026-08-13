from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
RELEASE_WORKFLOW = ROOT / ".github" / "workflows" / "release.yml"


class ReleaseWorkflowTests(unittest.TestCase):
    def test_publish_tolerates_missing_windows_artifact_directory(self):
        workflow = RELEASE_WORKFLOW.read_text(encoding="utf-8")

        self.assertIn("continue-on-error: true", workflow)
        self.assertGreaterEqual(workflow.count("mkdir -p windows-assets"), 2)
        self.assertIn("Windows release artifacts were skipped", workflow)
        self.assertIn("find dist windows-assets -type f -print", workflow)


if __name__ == "__main__":
    unittest.main()
