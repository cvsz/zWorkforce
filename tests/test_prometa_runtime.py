import unittest

from common import stack
from zworkforce.prometa import install_prometa_catalog, load_prometa_catalog
from zworkforce.skills import verify_manifest


class ProMetaRuntimeTests(unittest.TestCase):
    def setUp(self):
        self.temp, self.settings, self.db, self.provider, self.engine, self.auth = stack()

    def tearDown(self):
        self.engine.shutdown()
        self.temp.cleanup()

    def test_catalog_loads_and_installs_idempotently(self):
        catalog = load_prometa_catalog()
        self.assertEqual(18, len(catalog["agents"]))
        self.assertEqual(12, len(catalog["skills"]))
        self.assertEqual(3, len(catalog["templates"]))
        self.assertEqual(4, len(catalog["workflows"]))

        first = install_prometa_catalog(self.db, "default", "test")
        second = install_prometa_catalog(self.db, "default", "test")
        self.assertEqual(first, second)
        self.assertEqual(18, len([a for a in self.db.list_agents("default") if a["id"] in {x["id"] for x in catalog["agents"]}]))
        self.assertEqual(12, len(self.db.list_skills("default")))
        self.assertEqual(3, len(self.db.list_agent_templates("default")))
        self.assertEqual(4, len(self.db.list_workflows("default")))

        workflow = self.db.get_workflow("default", "prometa-repo-change")
        self.assertEqual("implementation-engineer", workflow["definition"]["steps"][2]["agent_id"])

    def test_install_can_sign_skill_manifests(self):
        key = "test-signing-key-with-enough-entropy"
        install_prometa_catalog(self.db, "default", "test", signing_key=key, sign_skills=True)
        skill = self.db.get_skill("default", "repo-review")
        self.assertTrue(verify_manifest(skill["manifest"], skill["signature"], key, require_signature=True))


if __name__ == "__main__":
    unittest.main()
