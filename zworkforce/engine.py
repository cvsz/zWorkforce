from __future__ import annotations
from concurrent.futures import ThreadPoolExecutor
import json, threading, uuid
from .db import utcnow
from .providers import ProviderError
from .router import ModelRouter
from .tools import TOOL_SCHEMAS, ToolExecutor, ToolError
class Engine:
    def __init__(self,settings,db,provider):
        self.settings,self.db,self.provider=settings,db,provider; self.router=ModelRouter(); self.tools=ToolExecutor(settings); self.pool=ThreadPoolExecutor(max_workers=settings.max_workers,thread_name_prefix="zworkforce"); self._scheduled=set(); self._lock=threading.Lock()
    def shutdown(self): self.pool.shutdown(wait=False,cancel_futures=True)
    def recover(self):
        for t in self.db.list_tasks(500):
            if t["status"] in {"queued","running"}: self.db.update_task(t["id"],status="queued",error=None); self._schedule(t["id"])
    def submit(self,agent_id,prompt,mutating=False,tier_override=None,parent_task_id=None,depth=0,idempotency_key=None,actor="system"):
        agent=self.db.get_agent(agent_id)
        if not agent or not agent["enabled"]: raise ValueError("agent not found or disabled")
        if not prompt.strip(): raise ValueError("prompt is required")
        if depth>8: raise ValueError("delegation depth exceeds platform limit")
        if v:=self.db.budget_violation(agent,self.settings.global_daily_budget_credits): raise ValueError(v)
        tier,rationale=self.router.choose(prompt,agent["default_tier"],mutating,tier_override); approval=bool(mutating and agent["requires_approval_for_mutations"])
        t={"id":str(uuid.uuid4()),"agent_id":agent_id,"prompt":prompt,"status":"waiting_approval" if approval else "queued","tier":tier,"model":self.settings.model_for_tier(tier),"mutating":mutating,"parent_task_id":parent_task_id,"depth":depth,"approval_required":approval}
        t,created=self.db.create_task(t,idempotency_key)
        if created:
            self.db.audit(actor,"task.create","task",t["id"],{"agent_id":agent_id,"tier":tier,"mutating":mutating,"router":rationale})
            if not approval: self._schedule(t["id"])
        return t,created
    def approve(self,task_id,actor):
        t=self.db.get_task(task_id)
        if not t: raise ValueError("task not found")
        if t["status"]!="waiting_approval": raise ValueError("task is not waiting for approval")
        self.db.update_task(task_id,status="queued",approved_by=actor,approved_at=utcnow()); self.db.audit(actor,"task.approve","task",task_id); self._schedule(task_id); return self.db.get_task(task_id)
    def cancel(self,task_id,actor):
        t=self.db.get_task(task_id)
        if not t: raise ValueError("task not found")
        if t["status"] in {"succeeded","failed","canceled"}: return t
        if t["status"] in {"queued","waiting_approval"}: self.db.update_task(task_id,status="canceled",cancel_requested=1,finished_at=utcnow())
        else: self.db.update_task(task_id,cancel_requested=1)
        self.db.audit(actor,"task.cancel","task",task_id); return self.db.get_task(task_id)
    def _schedule(self,task_id):
        with self._lock:
            if task_id in self._scheduled: return
            self._scheduled.add(task_id)
        self.pool.submit(self._guarded,task_id)
    def _guarded(self,task_id):
        try: self._run(task_id)
        finally:
            with self._lock: self._scheduled.discard(task_id)
    def _cost(self,tier,inp,cached,out):
        r=self.settings.rates[tier]; return ((max(0,inp-cached)*r.input)+(cached*r.cached)+(out*r.output))/1_000_000
    def _run(self,task_id):
        task=self.db.get_task(task_id)
        if not task or task["status"]!="queued": return
        agent=self.db.get_agent(task["agent_id"])
        if not agent: return
        if v:=self.db.budget_violation(agent,self.settings.global_daily_budget_credits): self.db.update_task(task_id,status="failed",error=v,finished_at=utcnow()); return
        self.db.update_task(task_id,status="running",started_at=utcnow(),error=None)
        system=(agent["system_prompt"] or f"You are {agent['name']} in department {agent['department']}.")+"\nUse tools only when needed. Keep work bounded. Never claim a tool action succeeded unless its result confirms success."
        messages=[{"role":"system","content":system},{"role":"user","content":task["prompt"]}]; total_in=total_cache=total_out=0; total_cost=0.0; tier=task["tier"]; model=task["model"]; delegated=0
        try:
            for iteration in range(1,int(agent["max_iterations"])+1):
                current=self.db.get_task(task_id) or task
                if current["cancel_requested"]: self.db.update_task(task_id,status="canceled",iterations=iteration-1,finished_at=utcnow()); return
                result=self.provider.chat(model,messages,TOOL_SCHEMAS); turn_cost=self._cost(tier,result.usage.input_tokens,result.usage.cached_tokens,result.usage.output_tokens); total_in+=result.usage.input_tokens; total_cache+=result.usage.cached_tokens; total_out+=result.usage.output_tokens; total_cost+=turn_cost
                self.db.record_usage(dict(task,tier=tier,model=model),result.usage.input_tokens,result.usage.cached_tokens,result.usage.output_tokens,turn_cost); self.db.update_task(task_id,tier=tier,model=model,input_tokens=total_in,cached_tokens=total_cache,output_tokens=total_out,cost_credits=total_cost,iterations=iteration)
                if total_cost>float(agent["max_cost_credits"]): raise RuntimeError(f"task budget exceeded agent max_cost_credits={agent['max_cost_credits']}")
                messages.append(result.raw_message or {"role":"assistant","content":result.content})
                if not result.tool_calls:
                    content=(result.content or "").strip()
                    if not content and (n:=self.router.escalate(tier)): tier=n; model=self.settings.model_for_tier(tier); continue
                    self.db.update_task(task_id,status="succeeded",result=content,input_tokens=total_in,cached_tokens=total_cache,output_tokens=total_out,cost_credits=total_cost,iterations=iteration,finished_at=utcnow()); self.db.audit("runtime","task.succeed","task",task_id,{"tier":tier,"cost_credits":total_cost,"iterations":iteration}); return
                for call in result.tool_calls:
                    if call.name=="agent_delegate":
                        if delegated>=int(agent["max_subagents"]): tr={"error":"max_subagents reached"}
                        else:
                            delegated+=1; child,_=self.submit(str(call.arguments.get("agent_id","")),str(call.arguments.get("prompt","")),bool(call.arguments.get("mutating",False)),parent_task_id=task_id,depth=int(task["depth"])+1,actor="runtime"); tr={"task_id":child["id"],"status":child["status"]}
                    else:
                        try: tr=self.tools.execute(call.name,call.arguments)
                        except (ToolError,OSError,ValueError) as exc: tr={"error":str(exc)}
                    messages.append({"role":"tool","tool_call_id":call.id,"content":json.dumps(tr,ensure_ascii=False,default=str)})
            raise RuntimeError("max_iterations reached before completion")
        except (ProviderError,RuntimeError,ValueError,OSError) as exc:
            current=self.db.get_task(task_id) or task; status="canceled" if current.get("cancel_requested") else "failed"; self.db.update_task(task_id,status=status,error=str(exc),input_tokens=total_in,cached_tokens=total_cache,output_tokens=total_out,cost_credits=total_cost,finished_at=utcnow()); self.db.audit("runtime",f"task.{status}","task",task_id,{"error":str(exc)[:500]})
