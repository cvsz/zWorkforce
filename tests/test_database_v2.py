import sqlite3
import unittest

from common import stack
from zworkforce.db import utcnow


class DatabaseV2Tests(unittest.TestCase):
    def setUp(self):
        self.temp, self.settings, self.db, self.provider, self.engine, self.auth = stack()
    def tearDown(self):
        self.engine.shutdown(); self.temp.cleanup()
    def test_tenant_isolation_and_seed_agents(self):
        self.db.ensure_tenant("acme", "Acme")
        self.assertEqual(len(self.db.list_agents("default")), 6)
        self.assertEqual(len(self.db.list_agents("acme")), 6)
        self.db.upsert_agent("acme", {"id":"custom-agent","name":"Custom","default_tier":"luna","allowed_tools":[],"approval_tools":[]})
        self.assertIsNone(self.db.get_agent("default", "custom-agent")); self.assertIsNotNone(self.db.get_agent("acme", "custom-agent"))
    def test_durable_claim_is_exclusive(self):
        task, _ = self.engine.submit("default", "researcher", "analyze this", actor="alice")
        a = self.db.claim_next_task("w1", 10); b = self.db.claim_next_task("w2", 10)
        self.assertEqual(a["id"], task["id"]); self.assertIsNone(b)
    def test_expired_lease_requeues(self):
        task, _ = self.engine.submit("default", "researcher", "analyze this", actor="alice")
        claimed = self.db.claim_next_task("w1", 10)
        self.db.update_task(claimed["id"], lease_expires_at="2000-01-01T00:00:00+00:00")
        result = self.db.requeue_expired_leases(); self.assertEqual(result["requeued"], 1); self.assertEqual(self.db.get_task("default", task["id"])["status"], "queued")
    def test_idempotency_scoped_to_actor_and_payload(self):
        t1, created1 = self.engine.submit("default", "researcher", "same", actor="alice", idempotency_key="abc")
        t2, created2 = self.engine.submit("default", "researcher", "same", actor="alice", idempotency_key="abc")
        self.assertTrue(created1); self.assertFalse(created2); self.assertEqual(t1["id"], t2["id"])
        t3, created3 = self.engine.submit("default", "researcher", "same", actor="bob", idempotency_key="abc")
        self.assertTrue(created3); self.assertNotEqual(t1["id"], t3["id"])
        with self.assertRaises(ValueError): self.engine.submit("default", "researcher", "different", actor="alice", idempotency_key="abc")
    def test_audit_hash_chain_detects_tamper(self):
        self.db.audit("default", "alice", "x", "task", "1", {"a":1}); self.db.audit("default", "bob", "y", "task", "2", {"b":2})
        self.assertTrue(self.db.verify_audit_chain("default")["ok"])
        with self.db.connection() as c: c.execute("UPDATE audit_events2 SET actor='mallory' WHERE id=(SELECT MIN(id) FROM audit_events2)")
        self.assertFalse(self.db.verify_audit_chain("default")["ok"])
    def test_memory_is_tenant_scoped(self):
        self.db.ensure_tenant("acme"); self.db.put_memory("default", None, "Project Alpha", "secret launch notes", ["launch"], "alice")
        self.assertEqual(len(self.db.search_memories("default", "launch")), 1); self.assertEqual(self.db.search_memories("acme", "launch"), [])

if __name__ == "__main__": unittest.main()
