import json
import threading
import unittest
import urllib.request
import urllib.error
from http.server import ThreadingHTTPServer

from common import stack
from zworkforce import __version__
from zworkforce.api import App, _sanitize_header_value


class ApiV2Tests(unittest.TestCase):
    def setUp(self):
        self.temp,self.settings,self.db,self.provider,self.engine,self.auth=stack()
        self.app=App(self.settings,self.db,self.engine,self.auth,self.provider)
        self.server=ThreadingHTTPServer(("127.0.0.1",0),self.app.handler())
        self.thread=threading.Thread(target=self.server.serve_forever,daemon=True); self.thread.start()
        self.base=f"http://127.0.0.1:{self.server.server_address[1]}"
    def tearDown(self):
        self.server.shutdown(); self.server.server_close(); self.engine.shutdown(); self.temp.cleanup()
    def req(self,path,method="GET",body=None,headers=None,timeout=15):
        h={"Authorization":"Bearer test-admin-secret",**(headers or {})}
        data=None
        if body is not None:
            data=json.dumps(body).encode(); h["Content-Type"]="application/json"
        r=urllib.request.Request(self.base+path,data=data,headers=h,method=method)
        with urllib.request.urlopen(r,timeout=timeout) as resp:
            return resp.status,dict(resp.headers),json.loads(resp.read())
    def test_health_is_public(self):
        with urllib.request.urlopen(self.base+"/health",timeout=5) as r:
            data=json.loads(r.read())
            self.assertEqual(data["version"],__version__)
            self.assertEqual(r.headers["X-Frame-Options"],"DENY")

    def test_header_values_strip_response_splitting_bytes(self):
        self.assertEqual(_sanitize_header_value("request\r\nInjected: yes"), "requestInjected: yes")
        self.assertEqual(_sanitize_header_value("origin\nInjected: yes"), "originInjected: yes")

    def test_static_asset_uses_explicit_content_type(self):
        req=urllib.request.Request(self.base+"/app.js")
        with urllib.request.urlopen(req,timeout=5) as r:
            self.assertEqual(r.headers["Content-Type"], "text/javascript; charset=utf-8")
    def test_overview_auth_and_task_dispatch(self):
        status,headers,data=self.req("/api/v1/overview")
        self.assertEqual(status,200); self.assertIn("credits_24h",data)
        status,_,task=self.req("/api/v1/tasks","POST",{"agent_id":"researcher","prompt":"summarize this"})
        self.assertEqual(status,201)
        self.engine.worker_loop("api-test",once=True)
        _,_,done=self.req("/api/v1/tasks/"+task["id"])
        self.assertEqual(done["status"],"succeeded")
    def test_scheduler_tick_endpoint_runs_once(self):
        status,_,data=self.req("/api/v1/scheduler-tick","POST",{})
        self.assertEqual(status,200)
        self.assertEqual(data["ticks"],1)
    def test_superadmin_tenant_switch(self):
        self.req("/api/v1/tenants","POST",{"id":"acme","name":"Acme"})
        _,_,data=self.req("/api/v1/agents",headers={"X-Tenant-ID":"acme"})
        self.assertEqual(len(data["items"]),6)
    def test_prometa_install_endpoint_installs_full_catalog(self):
        status,_,data=self.req("/api/v1/prometa/install","POST",{})
        self.assertEqual(status,201)
        self.assertEqual(data["agents"],28)
        self.assertEqual(data["skills"],22)
        self.assertEqual(data["agent_templates"],3)
        self.assertEqual(data["workflows"],4)
        _,_,agents=self.req("/api/v1/agents")
        self.assertTrue(any(item["id"]=="incident-commander" for item in agents["items"]))
        _,_,skills=self.req("/api/v1/skills")
        self.assertTrue(any(item["id"]=="release-verification" for item in skills["items"]))
    def test_tool_events_require_admin_role(self):
        _,secret=self.auth.create_key("default","viewer","viewer",["workforce:read","audit:read"])
        req=urllib.request.Request(self.base+"/api/v1/tool-events",headers={"Authorization":"Bearer "+secret})
        with self.assertRaises(urllib.error.HTTPError) as ctx:
            urllib.request.urlopen(req,timeout=5)
        self.assertEqual(ctx.exception.code,403)
    def test_missing_auth_is_401(self):
        req=urllib.request.Request(self.base+"/api/v1/overview")
        with self.assertRaises(urllib.error.HTTPError) as ctx: urllib.request.urlopen(req,timeout=5)
        self.assertEqual(ctx.exception.code,401)

if __name__=="__main__": unittest.main()
