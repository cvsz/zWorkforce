import os
import unittest
import uuid

from zworkforce.config import ProviderConfig, Settings
from zworkforce.db import Database, utcnow
from zworkforce.engine import Engine
from zworkforce.workflow import WorkflowOrchestrator
from zworkforce.providers import build_provider


@unittest.skipUnless(os.getenv("ZWORKFORCE_TEST_POSTGRES_URL"), "postgres integration URL not configured")
class PostgresIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.url=os.environ["ZWORKFORCE_TEST_POSTGRES_URL"]
        self.tenant_id=f"ci-{uuid.uuid4().hex}"
        self.db=Database(self.url,self.tenant_id)
        self.task_ids=[]
        self.settings=Settings(default_tenant=self.tenant_id,embedded_workers=0,providers=(
            ProviderConfig(name="mock",kind="mock",models={"luna":"mock-luna","terra":"mock-terra","sol":"mock-sol"}),))
        self.engine=Engine(self.settings,self.db,build_provider(self.settings,self.db))

    def test_fixture_uses_isolated_tenant(self):
        self.assertNotEqual(self.db.default_tenant, "ci")

    def tearDown(self):
        self.engine.shutdown()
        for task_id in self.task_ids:
            self.db.update_task(task_id,status="canceled",cancel_requested=1,finished_at=utcnow(),lease_owner=None,lease_expires_at=None,heartbeat_at=None)

    def _submit(self,*args,**kwargs):
        task,created=self.engine.submit(*args,**kwargs)
        self.task_ids.append(task["id"])
        return task,created

    def test_queue_and_runtime(self):
        task,_=self._submit(self.tenant_id,"researcher","postgres integration task",actor=self.tenant_id)
        self.assertEqual(self.engine.worker_loop("pg-worker",once=True),1)
        self.assertEqual(self.db.get_task(self.tenant_id,task["id"])["status"],"succeeded")
        self.assertEqual(self.db.backend_kind,"postgres")

    def test_skip_locked_claims_a_different_task(self):
        first,_=self._submit(self.tenant_id,"researcher","first queued task",actor=self.tenant_id,idempotency_key="pg-first")
        second,_=self._submit(self.tenant_id,"researcher","second queued task",actor=self.tenant_id,idempotency_key="pg-second")
        with self.db.connection() as locker:
            locker.execute("BEGIN")
            locked=locker.execute("SELECT id FROM tasks2 WHERE id=? FOR UPDATE",(first["id"],)).fetchone()
            self.assertEqual(locked[0],first["id"])
            claimed=self.db.claim_next_task("skip-locked-worker",30)
            self.assertIsNotNone(claimed)
            self.assertEqual(claimed["id"],second["id"])
            locker.execute("ROLLBACK")

    def test_v4_workflow_occurrence_and_outbox_claims(self):
        workflows = WorkflowOrchestrator(self.db, self.engine)
        workflows.upsert(self.tenant_id, {
            "id": "scheduled",
            "definition": {"steps": [{"id": "a", "agent_id": "researcher", "prompt": "run"}]},
        }, self.tenant_id)
        first = workflows.start(self.tenant_id, "scheduled", {}, self.tenant_id, idempotency_key="schedule:pg:1")
        second = workflows.start(self.tenant_id, "scheduled", {}, self.tenant_id, idempotency_key="schedule:pg:1")
        self.assertEqual(first["id"], second["id"])

        item_id = self.db.enqueue_outbox(self.tenant_id, "topic", "http://localhost/hook", {"ok": True})
        claimed = self.db.claim_outbox("pg-outbox-a", 30)
        self.assertEqual([item_id], [item["id"] for item in claimed])
        self.assertEqual([], self.db.claim_outbox("pg-outbox-b", 30))


if __name__ == "__main__": unittest.main()
