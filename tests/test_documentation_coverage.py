from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class DocumentationCoverageTests(unittest.TestCase):
    def test_github_operations_document_is_linked_from_primary_docs(self):
        required = [
            ROOT / "README.md",
            ROOT / "docs" / "OPERATIONS.md",
            ROOT / "docs" / "RELEASE.md",
            ROOT / ".github" / "pull_request_template.md",
        ]

        for path in required:
            with self.subTest(path=path.relative_to(ROOT)):
                self.assertIn(
                    "GITHUB-OPERATIONS.md",
                    path.read_text(encoding="utf-8"),
                )

    def test_readme_deployment_boundary_matches_package_version(self):
        readme = (ROOT / "README.md").read_text(encoding="utf-8")

        self.assertIn("## v3.0.2 highlights", readme)
        self.assertIn("v3.0.2 provides real distributed execution", readme)
        self.assertNotIn("v3.0.0 provides real distributed execution", readme)

    def test_github_operations_lists_current_workflows(self):
        doc = (ROOT / "docs" / "GITHUB-OPERATIONS.md").read_text(encoding="utf-8")
        workflows = {
            path.stem
            for path in (ROOT / ".github" / "workflows").glob("*.yml")
        }

        for expected in {
            "ci",
            "zarvis",
            "windows-client",
            "codeql",
            "dependency-review",
            "release",
        }:
            with self.subTest(workflow=expected):
                self.assertIn(expected, workflows)

        for phrase in [
            "CI",
            "ZARVIS",
            "Windows client",
            "CodeQL Advanced",
            "Dependency Review",
            "release.yml",
        ]:
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, doc)


if __name__ == "__main__":
    unittest.main()
