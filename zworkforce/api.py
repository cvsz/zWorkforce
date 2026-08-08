from http import HTTPStatus
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
import json,mimetypes,re
from pathlib import Path
from .metrics import prometheus
class App:
    def __init__(self,settings,db,engine,auth): self.settings,self.db,self.engine,self.auth=settings,db,engine,auth; self.static=Path(__file__).parent/"static"
    def handler(self):
        app=self
        class Handler(BaseHTTPRequestHandler):
            server_version="zWorkforce/1.0"
            def log_message(self,fmt,*args): print(json.dumps({"event":"http","client":self.client_address[0],"message":fmt%args},separators=(",",":")),flush=True)
            def _json(self,status,data):
                payload=json.dumps(data,ensure_ascii=False,separators=(",",":"),default=str).encode(); self.send_response(status); self.send_header("Content-Type","application/json; charset=utf-8"); self.send_header("Content-Length",str(len(payload))); self.send_header("Cache-Control","no-store"); self.send_header("X-Content-Type-Options","nosniff"); self.end_headers(); self.wfile.write(payload)
            def _body(self):
                try: n=int(self.headers.get("Content-Length","0"))
                except ValueError: raise ValueError("invalid Content-Length")
                if n<=0:return {}
                if n>app.settings.max_request_bytes: raise ValueError("request body too large")
                try:return json.loads(self.rfile.read(n))
                except json.JSONDecodeError as exc: raise ValueError("invalid JSON") from exc
            def _principal(self,role):
                p=app.auth.authenticate(self.headers.get("Authorization"),self.headers.get("X-API-Key"))
                if not app.auth.require(p,role): self._json(HTTPStatus.UNAUTHORIZED if p is None else HTTPStatus.FORBIDDEN,{"error":"authentication or role requirement failed"}); return None
                return p
            def _static(self,name):
                p=app.static/name
                if not p.is_file(): self.send_error(404); return
                data=p.read_bytes(); self.send_response(200); self.send_header("Content-Type",mimetypes.guess_type(name)[0] or "application/octet-stream"); self.send_header("Content-Length",str(len(data))); self.send_header("Cache-Control","public,max-age=300"); self.send_header("X-Content-Type-Options","nosniff"); self.end_headers(); self.wfile.write(data)
            def do_GET(self):
                path=self.path.split("?",1)[0]
                if path=="/": return self._static("index.html")
                if path in {"/app.js","/styles.css"}: return self._static(path[1:])
                if path=="/health": return self._json(200,{"status":"ok","version":"1.0.0"})
                if path=="/ready": return self._json(200,{"status":"ready","provider":app.settings.provider})
                if path=="/metrics":
                    if not self._principal("viewer"): return
                    data=prometheus(app.db).encode(); self.send_response(200); self.send_header("Content-Type","text/plain; version=0.0.4"); self.send_header("Content-Length",str(len(data))); self.end_headers(); self.wfile.write(data); return
                if not self._principal("viewer"): return
                if path=="/api/v1/overview": return self._json(200,app.db.overview())
                if path=="/api/v1/agents": return self._json(200,{"items":app.db.list_agents()})
                if path=="/api/v1/tasks": return self._json(200,{"items":app.db.list_tasks()})
                if path=="/api/v1/audit": return self._json(200,{"items":app.db.list_audit()})
                if path=="/api/v1/budgets": return self._json(200,{"items":app.db.list_budgets()})
                if path=="/api/v1/models": return self._json(200,{"tiers":[{"tier":t,"model":app.settings.model_for_tier(t),"rate":app.settings.rates[t].__dict__} for t in ("luna","terra","sol")]})
                m=re.fullmatch(r"/api/v1/tasks/([0-9a-f-]+)",path)
                if m:
                    t=app.db.get_task(m.group(1)); return self._json(200,t) if t else self._json(404,{"error":"task not found"})
                return self._json(404,{"error":"not found"})
            def do_POST(self):
                path=self.path.split("?",1)[0]
                try:
                    if path=="/api/v1/tasks":
                        p=self._principal("operator");
                        if not p:return
                        b=self._body(); t,created=app.engine.submit(str(b.get("agent_id","")),str(b.get("prompt","")),bool(b.get("mutating",False)),b.get("tier_override"),idempotency_key=self.headers.get("Idempotency-Key"),actor=p.name); return self._json(201 if created else 200,t)
                    if path=="/api/v1/agents":
                        p=self._principal("admin");
                        if not p:return
                        b=self._body(); aid=str(b.get("id",""))
                        if not re.fullmatch(r"[a-z0-9][a-z0-9-]{1,62}",aid): raise ValueError("agent id must be a DNS-like slug")
                        if b.get("default_tier","terra") not in {"luna","terra","sol"}: raise ValueError("invalid default_tier")
                        a=app.db.upsert_agent(b); app.db.audit(p.name,"agent.upsert","agent",a["id"]); return self._json(200,a)
                    if path=="/api/v1/budgets":
                        p=self._principal("admin");
                        if not p:return
                        b=self._body(); st=str(b.get("scope_type","")); period=str(b.get("period","")); sid=str(b.get("scope_id","")); limit=float(b.get("limit_credits",0))
                        if st not in {"global","department","agent"} or period not in {"daily","monthly"} or not sid: raise ValueError("invalid budget")
                        app.db.set_budget(st,sid,period,limit); app.db.audit(p.name,"budget.set","budget",f"{st}:{sid}:{period}",{"limit_credits":limit}); return self._json(200,{"ok":True})
                    m=re.fullmatch(r"/api/v1/tasks/([0-9a-f-]+)/(approve|cancel)",path)
                    if m:
                        p=self._principal("operator");
                        if not p:return
                        return self._json(200,app.engine.approve(m.group(1),p.name) if m.group(2)=="approve" else app.engine.cancel(m.group(1),p.name))
                    return self._json(404,{"error":"not found"})
                except (ValueError,TypeError) as exc: return self._json(400,{"error":str(exc)})
                except Exception as exc: return self._json(500,{"error":"internal server error","detail":str(exc) if app.settings.env!="production" else None})
        return Handler
def serve(app):
    server=ThreadingHTTPServer((app.settings.host,app.settings.port),app.handler()); print(f"zWorkforce 1.0.0 listening on http://{app.settings.host}:{app.settings.port}",flush=True)
    try: server.serve_forever(poll_interval=.25)
    except KeyboardInterrupt: pass
    finally: server.server_close(); app.engine.shutdown()
