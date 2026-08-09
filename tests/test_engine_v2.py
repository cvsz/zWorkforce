import tempfile
import time
import unittest

from common import stack
from zworkforce.providers import ProviderResult, ToolCall, Usage, ProviderError

class ScriptedProvider:
    def __init__(self, results): self.results=list(results); self.calls=0
    def preview(self, tier): return "scripted", f"model-{tier}"
    def chat(self, tier, messages, tools):
        self.calls += 1; item=self.results.pop(0)
        if isinstance(item, Exception): raise item
        return item
    def models(self): return [{"name":"scripted","kind":"test","available":True,"models":{}}]

class EngineV2Tests(unittest.TestCase):
    def setUp(self): self.temp, self.settings, self.db, self.provider, self.engine, self.auth = stack()
    def tearDown(self): self.engine.shutdown(); self.temp.cleanup()
    def test_mock_provider_completes_and_evaluates(self):
        task,_=self.engine.submit("default","researcher","summarize one two",actor="alice"); self.assertEqual(self.engine.worker_loop("w", once=True),1)
        done=self.db.get_task("default",task["id"]); self.assertEqual(done["status"],"succeeded"); self.assertEqual(done["outcome_status"],"passed"); self.assertGreater(done["input_tokens"],0)
    def test_four_eyes_approval(self):
        task,_=self.engine.submit("default","software-engineer","write file",actor="alice",mutating=True); self.assertEqual(task["status"],"waiting_approval")
        with self.assertRaises(ValueError): self.engine.approve("default",task["id"],"alice")
        approved=self.engine.approve("default",task["id"],"bob"); self.assertEqual(approved["status"],"queued")
    def test_two_distinct_approvals(self):
        agent=self.db.get_agent("default","software-engineer"); agent["required_approvals"]=2; self.db.upsert_agent("default",agent)
        task,_=self.engine.submit("default","software-engineer","deploy",actor="requester",mutating=True)
        one=self.engine.approve("default",task["id"],"reviewer-1"); self.assertEqual(one["status"],"waiting_approval")
        with self.assertRaises(Exception): self.engine.approve("default",task["id"],"reviewer-1")
        two=self.engine.approve("default",task["id"],"reviewer-2"); self.assertEqual(two["status"],"queued")
    def test_mutating_tool_denied_on_non_mutating_task(self):
        fake=ScriptedProvider([ProviderResult("", "scripted", "model-terra", Usage(10,0,5), [ToolCall("1","workspace_write",{"path":"x.txt","content":"owned"})], {"role":"assistant","content":"","tool_calls":[]}),ProviderResult("done", "scripted", "model-terra", Usage(5,0,2), [], {"role":"assistant","content":"done"})])
        self.engine.shutdown(); from zworkforce.engine import Engine; self.engine=Engine(self.settings,self.db,fake)
        task,_=self.engine.submit("default","software-engineer","please inspect",actor="alice",mutating=False,tier_override="terra"); self.engine.worker_loop("w",once=True)
        self.assertFalse((self.settings.workspace_root/"x.txt").exists()); events=self.db.list_tool_events("default",task["id"]); self.assertFalse(any(e["tool_name"]=="workspace_write" and e["success"] for e in events))
    def test_approved_workspace_write_executes(self):
        fake=ScriptedProvider([ProviderResult("", "scripted", "model-terra", Usage(10,0,5), [ToolCall("1","workspace_write",{"path":"x.txt","content":"hello"})], {"role":"assistant","content":""}),ProviderResult("done", "scripted", "model-terra", Usage(5,0,2), [], {"role":"assistant","content":"done"})])
        self.engine.shutdown(); from zworkforce.engine import Engine; self.engine=Engine(self.settings,self.db,fake)
        task,_=self.engine.submit("default","software-engineer","write x",actor="alice",mutating=True,tier_override="terra"); self.engine.approve("default",task["id"],"bob"); self.engine.worker_loop("w",once=True)
        self.assertEqual((self.settings.workspace_root/"x.txt").read_text(),"hello"); self.assertEqual(self.db.get_task("default",task["id"])["status"],"succeeded")
    def test_retryable_provider_failure_requeues(self):
        fake=ScriptedProvider([ProviderError("temporary", retryable=True), ProviderResult("ok","scripted","model-terra",Usage(1,0,1),[],{"role":"assistant","content":"ok"})])
        self.engine.shutdown(); from zworkforce.engine import Engine; self.engine=Engine(self.settings,self.db,fake)
        task,_=self.engine.submit("default","researcher","work",actor="alice",tier_override="terra"); self.engine.worker_loop("w1",once=True)
        mid=self.db.get_task("default",task["id"]); self.assertEqual(mid["status"],"queued"); self.db.update_task(task["id"],run_after="2000-01-01T00:00:00+00:00"); self.engine.worker_loop("w2",once=True)
        self.assertEqual(self.db.get_task("default",task["id"])["status"],"succeeded")

if __name__ == "__main__": unittest.main()
