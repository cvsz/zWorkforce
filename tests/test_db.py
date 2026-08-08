import tempfile,unittest
from pathlib import Path
from zworkforce.db import Database
class DbTests(unittest.TestCase):
    def test_seed_and_budget(self):
        with tempfile.TemporaryDirectory() as d:
            db=Database(Path(d)/"x.sqlite3"); self.assertGreaterEqual(len(db.list_agents()),6); db.set_budget("department","engineering","daily",10); self.assertEqual(db.list_budgets()[0]["limit_credits"],10)
