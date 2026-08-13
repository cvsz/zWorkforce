import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ZARVIS = ROOT / "packages" / "zarvis"


class ZarvisPackageMigrationTests(unittest.TestCase):
    def test_complete_zarvis_workspace_is_vendored(self):
        required = [
            "package.json",
            "pnpm-workspace.yaml",
            "pnpm-lock.yaml",
            "apps/zarvis-console",
            "apps/zarvis-windows",
            "apps/zvoice",
            "services/zarvis-orchestrator",
            "services/zarvis-api",
            "services/zarvis-action-gateway",
            "services/zarvis-task-gateway",
            "services/zarvis-memory",
            "services/zarvis-perception",
            "services/zarvis-proactive",
            "services/zarvis-owner-voice-edge",
            "services/voice-agent",
            "services/voice-gateway",
            "packages/contracts",
            "compose.zarvis-local.yml",
            "compose.zarvis-owner-domain.yml",
            "compose.zarvis-owner-voice.yml",
            "compose.voice.yml",
            "scripts/zarvis-complete-all.sh",
            "docs/architecture/zarvis.md",
            "MIGRATION.json",
        ]
        missing = [path for path in required if not (ZARVIS / path).exists()]
        self.assertEqual([], missing, f"missing migrated Z.A.R.V.I.S. paths: {missing}")

    def test_migration_manifest_declares_zworkforce_authoritative(self):
        manifest = json.loads((ZARVIS / "MIGRATION.json").read_text(encoding="utf-8"))
        self.assertEqual("cvsz/zWorkforce", manifest["source_of_truth"])
        self.assertEqual("cvsz/z-platform", manifest["migrated_from"])
        self.assertRegex(manifest["source_commit"], r"^[0-9a-f]{40}$")
        self.assertFalse(manifest["upstream_sync"])

    def test_nested_workspace_contains_no_git_repository(self):
        self.assertFalse((ZARVIS / ".git").exists())


if __name__ == "__main__":
    unittest.main()
