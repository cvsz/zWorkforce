import unittest
from common import stack


class AgentRegistryTests(unittest.TestCase):
    def setUp(self): self.temp,self.settings,self.db,self.provider,self.engine,self.auth=stack()
    def tearDown(self): self.engine.shutdown();self.temp.cleanup()
    def test_versions_and_templates(self):
        agent=dict(self.db.get_agent("default","researcher")); agent["description"]="updated description"
        self.db.upsert_agent("default",agent,"test")
        versions=self.db.list_agent_versions("default","researcher")
        self.assertEqual(versions[0]["version"],1);self.assertIn("updated description",versions[0]["snapshot"]["description"])
        template=self.db.upsert_agent_template("default",{"id":"research-template","name":"Research Template","agent":{"name":"Research Copy","department":"research","default_tier":"terra","allowed_tools":["calculator"]}},"test")
        self.assertEqual(template["id"],"research-template")

if __name__=="__main__": unittest.main()
