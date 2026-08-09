import unittest
from pathlib import Path

from common import stack
from zworkforce.rag import LocalSemanticMemory, feature_hash_embedding, cosine
from zworkforce.artifacts import LocalArtifactStore, ArtifactError
from zworkforce.economics import chargeback_report, capacity_forecast, slo_status


class RagArtifactTests(unittest.TestCase):
    def setUp(self):
        self.temp,self.settings,self.db,self.provider,self.engine,self.auth = stack()

    def tearDown(self):
        self.engine.shutdown(); self.temp.cleanup()

    def test_semantic_memory(self):
        memory = self.db.put_memory("default", None, "PostgreSQL", "Use SKIP LOCKED for worker lease queues", ["database"], "test")
        rag = LocalSemanticMemory(self.db)
        rag.reindex("default")
        results = rag.search("default", "postgres worker queue")
        self.assertEqual(results[0]["memory_id"], memory["id"])
        self.assertGreater(results[0]["score"], 0)

    def test_artifact_integrity(self):
        store = LocalArtifactStore(Path(self.temp.name)/"artifacts", self.db)
        item = store.put_bytes("default","report.txt",b"hello",actor="test")
        self.assertEqual(store.read_bytes(item["storage_uri"], item["sha256"]), b"hello")
        self.assertEqual(len(self.db.list_artifacts("default")), 1)

    def test_economics_and_slo(self):
        task,_ = self.engine.submit("default","researcher","hello",actor="test")
        self.engine.worker_loop("w",once=True)
        report=chargeback_report(self.db,"default",24)
        self.assertGreaterEqual(report["chargeback_amount"],0)
        self.assertGreaterEqual(capacity_forecast(self.db,"default",24)["recommended_workers"],1)
        self.db.set_slo_policy("default",{"id":"success","metric":"success_rate","comparator":"gte","target":0.5})
        self.assertTrue(slo_status(self.db,"default")["ok"])


if __name__ == "__main__":
    unittest.main()
