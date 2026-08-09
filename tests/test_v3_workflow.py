import unittest

from common import stack
from zworkforce.workflow import WorkflowOrchestrator, WorkflowError
from zworkforce.scheduler import Scheduler, parse_cron, next_cron_at
from datetime import datetime, timezone


class WorkflowTests(unittest.TestCase):
    def setUp(self):
        self.temp,self.settings,self.db,self.provider,self.engine,self.auth = stack()

    def tearDown(self):
        self.engine.shutdown(); self.temp.cleanup()

    def test_dag_executes_dependencies(self):
        wf = WorkflowOrchestrator(self.db, self.engine)
        wf.upsert("default", {"id":"demo","name":"Demo","definition":{"steps":[
            {"id":"a","agent_id":"researcher","prompt":"Research {{input.topic}}"},
            {"id":"b","agent_id":"management","depends_on":["a"],"prompt":"Summarize {{steps.a.result}}"},
        ]}}, "test")
        run = wf.start("default","demo",{"topic":"AI workforce"},"test")
        self.assertEqual(wf.tick()["tasks_submitted"], 1)
        self.assertEqual(self.engine.worker_loop("w1", once=True), 1)
        self.assertEqual(wf.tick()["tasks_submitted"], 1)
        self.assertEqual(self.engine.worker_loop("w2", once=True), 1)
        result = wf.tick()
        self.assertEqual(result["completed"], 1)
        self.assertEqual(self.db.get_workflow_run("default", run["id"])["status"], "succeeded")

    def test_cycle_rejected(self):
        wf=WorkflowOrchestrator(self.db,self.engine)
        with self.assertRaises(WorkflowError):
            wf.upsert("default", {"id":"bad","definition":{"steps":[
                {"id":"a","agent_id":"researcher","prompt":"a","depends_on":["b"]},
                {"id":"b","agent_id":"researcher","prompt":"b","depends_on":["a"]},
            ]}}, "test")

    def test_cron_parser(self):
        self.assertIn(0, parse_cron("*/15 * * * *")[0])
        nxt = next_cron_at("0 9 * * 1-5", datetime(2026,8,9,tzinfo=timezone.utc), "UTC")
        self.assertTrue(nxt.endswith("+00:00"))


if __name__ == "__main__":
    unittest.main()
