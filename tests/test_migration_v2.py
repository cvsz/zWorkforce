import json
import sqlite3
import tempfile
import unittest
from pathlib import Path

from zworkforce.db import Database


class MigrationV2Tests(unittest.TestCase):
    def test_v1_state_is_preserved_and_agent_config_wins_over_seed(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "zworkforce.sqlite3"
            c = sqlite3.connect(path)
            c.executescript("""
            CREATE TABLE agents(id TEXT PRIMARY KEY,name TEXT NOT NULL,description TEXT NOT NULL DEFAULT '',department TEXT NOT NULL DEFAULT 'general',default_tier TEXT NOT NULL,max_cost_credits REAL NOT NULL,max_iterations INTEGER NOT NULL,max_subagents INTEGER NOT NULL,requires_approval_for_mutations INTEGER NOT NULL,system_prompt TEXT NOT NULL,enabled INTEGER NOT NULL,created_at TEXT NOT NULL,updated_at TEXT NOT NULL);
            CREATE TABLE tasks(id TEXT PRIMARY KEY,agent_id TEXT NOT NULL,prompt TEXT NOT NULL,status TEXT NOT NULL,tier TEXT NOT NULL,model TEXT NOT NULL,mutating INTEGER NOT NULL,parent_task_id TEXT,depth INTEGER NOT NULL,approval_required INTEGER NOT NULL,approved_by TEXT,approved_at TEXT,result TEXT,error TEXT,input_tokens INTEGER NOT NULL,cached_tokens INTEGER NOT NULL,output_tokens INTEGER NOT NULL,cost_credits REAL NOT NULL,iterations INTEGER NOT NULL,cancel_requested INTEGER NOT NULL,created_at TEXT NOT NULL,updated_at TEXT NOT NULL,started_at TEXT,finished_at TEXT);
            CREATE TABLE usage_events(id INTEGER PRIMARY KEY AUTOINCREMENT,task_id TEXT NOT NULL,agent_id TEXT NOT NULL,department TEXT NOT NULL,tier TEXT NOT NULL,model TEXT NOT NULL,input_tokens INTEGER NOT NULL,cached_tokens INTEGER NOT NULL,output_tokens INTEGER NOT NULL,cost_credits REAL NOT NULL,created_at TEXT NOT NULL);
            CREATE TABLE budgets(scope_type TEXT NOT NULL,scope_id TEXT NOT NULL,period TEXT NOT NULL,limit_credits REAL NOT NULL,updated_at TEXT NOT NULL,PRIMARY KEY(scope_type,scope_id,period));
            CREATE TABLE audit_events(id INTEGER PRIMARY KEY AUTOINCREMENT,actor TEXT NOT NULL,action TEXT NOT NULL,target_type TEXT NOT NULL,target_id TEXT NOT NULL,details_json TEXT NOT NULL,created_at TEXT NOT NULL);
            """)
            ts = "2026-08-08T00:00:00+00:00"
            c.execute("INSERT INTO agents VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)", ("software-engineer","Legacy Engineer","legacy config","engineering","sol",123.0,17,4,1,"legacy-system",1,ts,ts))
            c.execute("INSERT INTO tasks VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", ("11111111-1111-1111-1111-111111111111","software-engineer","legacy task","succeeded","sol","legacy-sol",1,None,0,1,"legacy-approver",ts,"done",None,10,2,3,0.5,1,0,ts,ts,ts,ts))
            c.execute("INSERT INTO usage_events(task_id,agent_id,department,tier,model,input_tokens,cached_tokens,output_tokens,cost_credits,created_at) VALUES(?,?,?,?,?,?,?,?,?,?)", ("11111111-1111-1111-1111-111111111111","software-engineer","engineering","sol","legacy-sol",10,2,3,0.5,ts))
            c.execute("INSERT INTO budgets VALUES(?,?,?,?,?)", ("agent","software-engineer","daily",99.0,ts))
            c.execute("INSERT INTO audit_events(actor,action,target_type,target_id,details_json,created_at) VALUES(?,?,?,?,?,?)", ("legacy-admin","task.create","task","11111111-1111-1111-1111-111111111111",json.dumps({"from":"v1"}),ts))
            c.commit(); c.close()
            db = Database(path, "default")
            agent = db.get_agent("default", "software-engineer")
            self.assertEqual(agent["name"], "Legacy Engineer"); self.assertEqual(agent["default_tier"], "sol"); self.assertEqual(agent["max_cost_credits"], 123.0)
            task = db.get_task("default", "11111111-1111-1111-1111-111111111111"); self.assertEqual(task["result"], "done")
            self.assertEqual(db.list_budgets("default")[0]["limit_credits"], 99.0)
            approvals = db.list_approvals("default", task["id"]); self.assertEqual(approvals[0]["actor"], "legacy-approver")
            self.assertTrue(db.verify_audit_chain("default")["ok"]); self.assertTrue(any(x["actor"] == "legacy-admin" for x in db.list_audit("default")))
            before = len(db.list_audit("default", 500)); db2 = Database(path, "default"); self.assertEqual(len(db2.list_audit("default", 500)), before)

if __name__ == "__main__": unittest.main()
