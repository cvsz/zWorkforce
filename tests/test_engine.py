import tempfile,time,unittest
from pathlib import Path
from zworkforce.config import Settings
from zworkforce.db import Database
from zworkforce.engine import Engine
from zworkforce.providers import MockProvider
class EngineTests(unittest.TestCase):
    def setUp(self): self.tmp=tempfile.TemporaryDirectory(); p=Path(self.tmp.name); self.s=Settings(data_dir=p,workspace_root=p,max_workers=2); self.db=Database(p/"test.sqlite3"); self.e=Engine(self.s,self.db,MockProvider())
    def tearDown(self): self.e.shutdown(); self.tmp.cleanup()
    def wait(self,tid):
        for _ in range(100):
            t=self.db.get_task(tid)
            if t["status"] in {"succeeded","failed","canceled"}: return t
            time.sleep(.02)
        self.fail("task did not finish")
    def test_task(self):
        t,c=self.e.submit("researcher","Summarize the operating model",actor="test"); self.assertTrue(c); done=self.wait(t["id"]); self.assertEqual(done["status"],"succeeded"); self.assertGreater(done["output_tokens"],0)
    def test_approval(self):
        t,_=self.e.submit("software-engineer","Change a file",mutating=True,actor="test"); self.assertEqual(t["status"],"waiting_approval"); self.e.approve(t["id"],"approver"); self.assertEqual(self.wait(t["id"])["status"],"succeeded")
    def test_idempotency(self):
        a,c1=self.e.submit("researcher","A",idempotency_key="same",actor="test"); b,c2=self.e.submit("researcher","A",idempotency_key="same",actor="test"); self.assertTrue(c1); self.assertFalse(c2); self.assertEqual(a["id"],b["id"])
