import unittest
from common import stack
from zworkforce.policy import decide, validate_policy, PolicyError


class PolicyTests(unittest.TestCase):
    def setUp(self): self.temp,self.settings,self.db,self.provider,self.engine,self.auth=stack()
    def tearDown(self): self.engine.shutdown();self.temp.cleanup()
    def test_policy_deny_task(self):
        document=validate_policy({"rules":[{"id":"block-finance","effect":"deny","action":"task.submit","when":{"department":"finance"}}]})
        self.db.upsert_policy("default",{"id":"guard","name":"guard","document":document},"test")
        with self.assertRaises(PolicyError):
            self.engine.submit("default","finance-analyst","forecast",actor="test")
        task,_=self.engine.submit("default","researcher","research",actor="test")
        self.assertEqual(task["status"],"queued")
    def test_explicit_deny_wins(self):
        policies=[{"id":"p","document":{"default":"allow","rules":[
            {"id":"a","effect":"allow","action":"tool.*","when":{}},
            {"id":"d","effect":"deny","action":"tool.shell_exec","when":{}},
        ]}}]
        self.assertFalse(decide(policies,"tool.shell_exec",{})[0])
        self.assertTrue(decide(policies,"tool.calculator",{})[0])

if __name__=="__main__": unittest.main()
