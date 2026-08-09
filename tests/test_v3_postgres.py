import os
import unittest

from zworkforce.config import ProviderConfig, Settings
from zworkforce.db import Database
from zworkforce.engine import Engine
from zworkforce.providers import build_provider


@unittest.skipUnless(os.getenv("ZWORKFORCE_TEST_POSTGRES_URL"), "postgres integration URL not configured")
class PostgresIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.url=os.environ["ZWORKFORCE_TEST_POSTGRES_URL"]
        self.db=Database(self.url,"ci")
        self.settings=Settings(default_tenant="ci",embedded_workers=0,providers=(
            ProviderConfig(name="mock",kind="mock",models={"luna":"mock-luna","terra":"mock-terra","sol":"mock-sol"}),))
        self.engine=Engine(self.settings,self.db,build_provider(self.settings,self.db))
    def tearDown(self):
        self.engine.shutdown()

    def test_queue_and_runtime(self):
        task,_=self.engine.submit("ci","researcher","postgres integration task",actor="ci")
        self.assertEqual(self.engine.worker_loop("pg-worker",once=True),1)
        self.assertEqual(self.db.get_task("ci",task["id"])["status"],"succeeded")
        self.assertEqual(self.db.backend_kind,"postgres")

    def test_skip_locked_claims_a_different_task(self):
        first,_=self.engine.submit("ci","researcher","first queued task",actor="ci",idempotency_key="pg-first")
        second,_=self.engine.submit("ci","researcher","second queued task",actor="ci",idempotency_key="pg-second")
        with self.db.connection() as locker:
            locker.execute("BEGIN")
            locked=locker.execute("SELECT id FROM tasks2 WHERE id=? FOR UPDATE",(first["id"],)).fetchone()
            self.assertEqual(locked[0],first["id"])
            claimed=self.db.claim_next_task("skip-locked-worker",30)
            self.assertIsNotNone(claimed)
            self.assertEqual(claimed["id"],second["id"])
            locker.execute("ROLLBACK")


if __name__ == "__main__": unittest.main()
