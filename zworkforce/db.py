from __future__ import annotations
import json, sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone, timedelta
from pathlib import Path

def utcnow(): return datetime.now(timezone.utc).isoformat(timespec="seconds")
class Database:
    def __init__(self,path): self.path=Path(path); self.path.parent.mkdir(parents=True,exist_ok=True); self.initialize()
    @contextmanager
    def connection(self):
        c=sqlite3.connect(self.path,timeout=15,isolation_level=None); c.row_factory=sqlite3.Row; c.execute("PRAGMA foreign_keys=ON"); c.execute("PRAGMA busy_timeout=15000")
        try: yield c
        finally: c.close()
    def initialize(self):
        with self.connection() as c:
            c.execute("PRAGMA journal_mode=WAL")
            c.executescript("""
            CREATE TABLE IF NOT EXISTS agents(id TEXT PRIMARY KEY,name TEXT NOT NULL,description TEXT NOT NULL DEFAULT '',department TEXT NOT NULL DEFAULT 'general',default_tier TEXT NOT NULL CHECK(default_tier IN ('sol','terra','luna')),max_cost_credits REAL NOT NULL DEFAULT 50,max_iterations INTEGER NOT NULL DEFAULT 8,max_subagents INTEGER NOT NULL DEFAULT 2,requires_approval_for_mutations INTEGER NOT NULL DEFAULT 1,system_prompt TEXT NOT NULL DEFAULT '',enabled INTEGER NOT NULL DEFAULT 1,created_at TEXT NOT NULL,updated_at TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS tasks(id TEXT PRIMARY KEY,agent_id TEXT NOT NULL REFERENCES agents(id),prompt TEXT NOT NULL,status TEXT NOT NULL,tier TEXT NOT NULL,model TEXT NOT NULL,mutating INTEGER NOT NULL DEFAULT 0,parent_task_id TEXT NULL REFERENCES tasks(id),depth INTEGER NOT NULL DEFAULT 0,approval_required INTEGER NOT NULL DEFAULT 0,approved_by TEXT NULL,approved_at TEXT NULL,result TEXT NULL,error TEXT NULL,input_tokens INTEGER NOT NULL DEFAULT 0,cached_tokens INTEGER NOT NULL DEFAULT 0,output_tokens INTEGER NOT NULL DEFAULT 0,cost_credits REAL NOT NULL DEFAULT 0,iterations INTEGER NOT NULL DEFAULT 0,cancel_requested INTEGER NOT NULL DEFAULT 0,created_at TEXT NOT NULL,updated_at TEXT NOT NULL,started_at TEXT NULL,finished_at TEXT NULL);
            CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status);
            CREATE INDEX IF NOT EXISTS idx_tasks_created ON tasks(created_at DESC);
            CREATE TABLE IF NOT EXISTS usage_events(id INTEGER PRIMARY KEY AUTOINCREMENT,task_id TEXT NOT NULL REFERENCES tasks(id),agent_id TEXT NOT NULL,department TEXT NOT NULL,tier TEXT NOT NULL,model TEXT NOT NULL,input_tokens INTEGER NOT NULL,cached_tokens INTEGER NOT NULL,output_tokens INTEGER NOT NULL,cost_credits REAL NOT NULL,created_at TEXT NOT NULL);
            CREATE INDEX IF NOT EXISTS idx_usage_created ON usage_events(created_at DESC);
            CREATE TABLE IF NOT EXISTS audit_events(id INTEGER PRIMARY KEY AUTOINCREMENT,actor TEXT NOT NULL,action TEXT NOT NULL,target_type TEXT NOT NULL,target_id TEXT NOT NULL,details_json TEXT NOT NULL DEFAULT '{}',created_at TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS budgets(scope_type TEXT NOT NULL CHECK(scope_type IN ('global','department','agent')),scope_id TEXT NOT NULL,period TEXT NOT NULL CHECK(period IN ('daily','monthly')),limit_credits REAL NOT NULL,updated_at TEXT NOT NULL,PRIMARY KEY(scope_type,scope_id,period));
            CREATE TABLE IF NOT EXISTS idempotency_keys(key TEXT PRIMARY KEY,task_id TEXT NOT NULL REFERENCES tasks(id),created_at TEXT NOT NULL);
            """)
            if c.execute("SELECT COUNT(*) FROM agents").fetchone()[0]==0:
                now=utcnow(); seeds=[
                    ("software-engineer","Software Engineer","Repository analysis, implementation, testing and review","engineering","terra",80,12,3,1,"You are a careful senior software engineer. Prefer tests, small diffs, and secure defaults."),
                    ("researcher","Research Analyst","Research, synthesis, evidence and decision support","research","terra",50,8,2,0,"You are an evidence-first research analyst. Separate facts, assumptions, and recommendations."),
                    ("finance-analyst","Finance Analyst","Forecasting, spreadsheet reasoning and financial analysis","finance","terra",40,8,1,1,"You are a finance analyst. Show assumptions and never fabricate financial records."),
                    ("sales","Sales Agent","Lead preparation, proposals and sales workflow support","sales","luna",25,6,1,1,"You are a concise sales operations agent. Never make unauthorized commitments."),
                    ("operations","Operations Agent","Operational checks, runbooks and workflow automation","operations","terra",50,10,2,1,"You are an operations engineer. Prefer reversible actions and explicit verification."),
                    ("management","Management Analyst","Executive synthesis, planning and board-ready outputs","management","sol",80,8,2,0,"You are an executive analyst. Optimize for decision quality, risks, and measurable outcomes.")]
                c.executemany("INSERT INTO agents(id,name,description,department,default_tier,max_cost_credits,max_iterations,max_subagents,requires_approval_for_mutations,system_prompt,enabled,created_at,updated_at) VALUES (?,?,?,?,?,?,?,?,?,?,1,?,?)",[(*s,now,now) for s in seeds])
    def _rows(self,rows): return [dict(r) for r in rows]
    def list_agents(self):
        with self.connection() as c: return self._rows(c.execute("SELECT * FROM agents ORDER BY department,name").fetchall())
    def get_agent(self,agent_id):
        with self.connection() as c:
            r=c.execute("SELECT * FROM agents WHERE id=?",(agent_id,)).fetchone(); return dict(r) if r else None
    def upsert_agent(self,a):
        now=utcnow()
        vals=(a["id"],a["name"],a.get("description",""),a.get("department","general"),a.get("default_tier","terra"),float(a.get("max_cost_credits",50)),int(a.get("max_iterations",8)),int(a.get("max_subagents",2)),int(bool(a.get("requires_approval_for_mutations",True))),a.get("system_prompt",""),int(bool(a.get("enabled",True))),now,now)
        with self.connection() as c:
            c.execute("BEGIN IMMEDIATE")
            if c.execute("SELECT 1 FROM agents WHERE id=?",(a["id"],)).fetchone(): c.execute("UPDATE agents SET name=?,description=?,department=?,default_tier=?,max_cost_credits=?,max_iterations=?,max_subagents=?,requires_approval_for_mutations=?,system_prompt=?,enabled=?,updated_at=? WHERE id=?",vals[1:11]+(now,a["id"]))
            else: c.execute("INSERT INTO agents(id,name,description,department,default_tier,max_cost_credits,max_iterations,max_subagents,requires_approval_for_mutations,system_prompt,enabled,created_at,updated_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",vals)
            c.execute("COMMIT")
        return self.get_agent(a["id"])
    def create_task(self,t,idempotency_key=None):
        now=utcnow()
        with self.connection() as c:
            c.execute("BEGIN IMMEDIATE")
            if idempotency_key:
                hit=c.execute("SELECT task_id FROM idempotency_keys WHERE key=?",(idempotency_key,)).fetchone()
                if hit:
                    row=c.execute("SELECT * FROM tasks WHERE id=?",(hit[0],)).fetchone(); c.execute("COMMIT"); return dict(row),False
            c.execute("INSERT INTO tasks(id,agent_id,prompt,status,tier,model,mutating,parent_task_id,depth,approval_required,created_at,updated_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",(t["id"],t["agent_id"],t["prompt"],t["status"],t["tier"],t["model"],int(t.get("mutating",False)),t.get("parent_task_id"),int(t.get("depth",0)),int(t.get("approval_required",False)),now,now))
            if idempotency_key: c.execute("INSERT INTO idempotency_keys(key,task_id,created_at) VALUES (?,?,?)",(idempotency_key,t["id"],now))
            c.execute("COMMIT")
        return self.get_task(t["id"]),True
    def get_task(self,task_id):
        with self.connection() as c:
            r=c.execute("SELECT * FROM tasks WHERE id=?",(task_id,)).fetchone(); return dict(r) if r else None
    def list_tasks(self,limit=100):
        with self.connection() as c: return self._rows(c.execute("SELECT * FROM tasks ORDER BY created_at DESC LIMIT ?",(max(1,min(limit,500)),)).fetchall())
    def update_task(self,task_id,**fields):
        allowed={"status","tier","model","approved_by","approved_at","result","error","input_tokens","cached_tokens","output_tokens","cost_credits","iterations","cancel_requested","started_at","finished_at"}; items=[(k,v) for k,v in fields.items() if k in allowed]
        if not items: return
        items.append(("updated_at",utcnow())); sql="UPDATE tasks SET "+",".join(f"{k}=?" for k,_ in items)+" WHERE id=?"
        with self.connection() as c: c.execute(sql,tuple(v for _,v in items)+(task_id,))
    def record_usage(self,task,inp,cached,out,cost):
        agent=self.get_agent(task["agent_id"]) or {"department":"unknown"}
        with self.connection() as c: c.execute("INSERT INTO usage_events(task_id,agent_id,department,tier,model,input_tokens,cached_tokens,output_tokens,cost_credits,created_at) VALUES (?,?,?,?,?,?,?,?,?,?)",(task["id"],task["agent_id"],agent["department"],task["tier"],task["model"],inp,cached,out,cost,utcnow()))
    def audit(self,actor,action,target_type,target_id,details=None):
        with self.connection() as c: c.execute("INSERT INTO audit_events(actor,action,target_type,target_id,details_json,created_at) VALUES (?,?,?,?,?,?)",(actor,action,target_type,target_id,json.dumps(details or {},separators=(",",":")),utcnow()))
    def list_audit(self,limit=100):
        with self.connection() as c: return self._rows(c.execute("SELECT * FROM audit_events ORDER BY id DESC LIMIT ?",(max(1,min(limit,500)),)).fetchall())
    def set_budget(self,scope_type,scope_id,period,limit):
        with self.connection() as c: c.execute("INSERT INTO budgets(scope_type,scope_id,period,limit_credits,updated_at) VALUES (?,?,?,?,?) ON CONFLICT(scope_type,scope_id,period) DO UPDATE SET limit_credits=excluded.limit_credits,updated_at=excluded.updated_at",(scope_type,scope_id,period,max(0,float(limit)),utcnow()))
    def list_budgets(self):
        with self.connection() as c: return self._rows(c.execute("SELECT * FROM budgets ORDER BY scope_type,scope_id,period").fetchall())
    def spent(self,scope_type,scope_id,period):
        now=datetime.now(timezone.utc); start=now.replace(hour=0,minute=0,second=0,microsecond=0) if period=="daily" else now.replace(day=1,hour=0,minute=0,second=0,microsecond=0); clause="1=1"; args=[]
        if scope_type=="department": clause="department=?"; args=[scope_id]
        elif scope_type=="agent": clause="agent_id=?"; args=[scope_id]
        with self.connection() as c: return float(c.execute(f"SELECT COALESCE(SUM(cost_credits),0) FROM usage_events WHERE {clause} AND created_at>=?",(*args,start.isoformat(timespec="seconds"))).fetchone()[0] or 0)
    def budget_violation(self,agent,global_daily_limit=0):
        checks=[]
        if global_daily_limit>0: checks.append(("global","global","daily",global_daily_limit))
        with self.connection() as c: rows=c.execute("SELECT * FROM budgets").fetchall()
        for row in rows:
            r=dict(row)
            if r["scope_type"]=="global" or (r["scope_type"]=="agent" and r["scope_id"]==agent["id"]) or (r["scope_type"]=="department" and r["scope_id"]==agent["department"]): checks.append((r["scope_type"],r["scope_id"],r["period"],float(r["limit_credits"])))
        for st,sid,period,limit in checks:
            if self.spent(st,sid,period)>=limit: return f"{st}:{sid} {period} budget exhausted ({limit:g} credits)"
        return None
    def overview(self):
        since=(datetime.now(timezone.utc)-timedelta(hours=24)).isoformat(timespec="seconds")
        with self.connection() as c:
            active=c.execute("SELECT COUNT(*) FROM tasks WHERE status IN ('queued','running','waiting_approval')").fetchone()[0]; total=c.execute("SELECT COUNT(*) FROM tasks WHERE created_at>=?",(since,)).fetchone()[0]; success=c.execute("SELECT COUNT(*) FROM tasks WHERE created_at>=? AND status='succeeded'",(since,)).fetchone()[0]; cost=c.execute("SELECT COALESCE(SUM(cost_credits),0) FROM usage_events WHERE created_at>=?",(since,)).fetchone()[0]; mix=self._rows(c.execute("SELECT tier,COALESCE(SUM(cost_credits),0) cost,COUNT(*) turns FROM usage_events WHERE created_at>=? GROUP BY tier ORDER BY tier",(since,)).fetchall()); top=self._rows(c.execute("SELECT agent_id,COALESCE(SUM(cost_credits),0) cost,COUNT(*) turns FROM usage_events WHERE created_at>=? GROUP BY agent_id ORDER BY cost DESC LIMIT 8",(since,)).fetchall())
        return {"active_tasks":active,"tasks_24h":total,"success_rate":round(success/total*100 if total else 100,2),"credits_24h":round(float(cost or 0),6),"model_mix":mix,"top_cost_agents":top}
