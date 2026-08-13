from pathlib import Path
import re
import subprocess
import unittest


ROOT = Path(__file__).resolve().parents[1]
MARKDOWN_LINK = re.compile(r"\[[^\]]+\]\(([^)]+)\)")
FENCED_BLOCK = re.compile(r"```.*?```", re.S)


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

    def test_prometa_master_document_is_linked_from_primary_docs(self):
        required = [
            ROOT / "README.md",
            ROOT / "docs" / "API.md",
            ROOT / "ROADMAP.md",
        ]

        for path in required:
            with self.subTest(path=path.relative_to(ROOT)):
                self.assertIn(
                    "PROMETA-MASTER.md",
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

    def test_markdown_internal_links_resolve(self):
        missing = []
        tracked = subprocess.check_output(
            ["git", "ls-files", "*.md"],
            cwd=ROOT,
            text=True,
            encoding="utf-8",
        ).splitlines()
        for relative in tracked:
            if "/.agents/" in relative or "/.claude/" in relative:
                continue
            path = ROOT / relative
            text = path.read_text(encoding="utf-8", errors="ignore")
            text = FENCED_BLOCK.sub("", text)
            for match in MARKDOWN_LINK.finditer(text):
                target = match.group(1).split("#", 1)[0]
                if not target or re.match(r"^[A-Za-z][A-Za-z0-9+.-]*:", target):
                    continue
                resolved = (path.parent / target.replace("%20", " ")).resolve()
                if not resolved.exists():
                    missing.append(f"{path.relative_to(ROOT)} -> {match.group(1)}")

        self.assertEqual([], missing)


if __name__ == "__main__":
    unittest.main()
