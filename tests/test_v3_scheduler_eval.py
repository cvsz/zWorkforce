import unittest

from common import stack
from zworkforce.scheduler import Scheduler
from zworkforce.evaluation_suite import EvaluationRunner


class SchedulerEvalTests(unittest.TestCase):
    def setUp(self):
        self.temp,self.settings,self.db,self.provider,self.engine,self.auth = stack()

    def tearDown(self):
        self.engine.shutdown(); self.temp.cleanup()

    def test_event_rule_dispatches(self):
        self.db.upsert_event_rule("default", {
            "id":"incident","name":"Incident","event_type":"incident.opened","target_type":"agent",
            "target_id":"operations","filter":{"severity":"high"},
            "payload_template":{"prompt":"Investigate {{event.title}}"}
        }, "test")
        self.db.emit_event("default","incident.opened","test",{"severity":"high","title":"API down"},"e1")
        stats = Scheduler(self.db,self.engine).tick()
        self.assertEqual(stats["events"], 1)
        tasks = self.db.list_tasks("default")
        self.assertEqual(len(tasks), 1)
        self.assertIn("API down", tasks[0]["prompt"])

    def test_ab_evaluation(self):
        runner = EvaluationRunner(self.db,self.engine)
        runner.upsert("default", {
            "id":"tiers","name":"tiers","agent_id":"researcher",
            "cases":[{"id":"c1","prompt":"Summarize this test","success_criteria":[{"type":"non_empty"}]}],
            "variants":[{"name":"cheap","tier":"luna"},{"name":"balanced","tier":"terra"}]
        }, "test")
        run = runner.start("default","tiers","test")
        self.assertEqual(len(self.db.list_evaluation_results(run["id"])), 2)
        self.engine.worker_loop("e1", once=True)
        self.engine.worker_loop("e2", once=True)
        self.assertEqual(runner.tick()["completed"], 1)
        final = self.db.get_evaluation_run("default", run["id"])
        self.assertEqual(final["status"], "succeeded")
        self.assertTrue(final["summary"]["recommended_variant"])


if __name__ == "__main__":
    unittest.main()

class ServiceLeaseTests(unittest.TestCase):
    def setUp(self):
        self.temp,self.settings,self.db,self.provider,self.engine,self.auth = stack()
    def tearDown(self):
        self.engine.shutdown(); self.temp.cleanup()
    def test_service_lease_has_single_owner(self):
        self.assertTrue(self.db.acquire_service_lease("scheduler", "a", 30))
        self.assertFalse(self.db.acquire_service_lease("scheduler", "b", 30))
        self.assertTrue(self.db.acquire_service_lease("scheduler", "a", 30))
        self.assertTrue(self.db.release_service_lease("scheduler", "a"))
        self.assertTrue(self.db.acquire_service_lease("scheduler", "b", 30))
