import argparse,json,sys
from .api import App,serve
from .config import Settings
from .db import Database
from .engine import Engine
from .providers import build_provider
from .security import AuthManager
def build():
    s=Settings.from_env(); s.data_dir.mkdir(parents=True,exist_ok=True); db=Database(s.database_path); e=Engine(s,db,build_provider(s)); return s,db,e,AuthManager(s.api_keys)
def main(argv=None):
    p=argparse.ArgumentParser(prog="zworkforce",description="AI Workforce control plane"); sub=p.add_subparsers(dest="command"); sub.add_parser("serve"); sub.add_parser("doctor"); sub.add_parser("init"); args=p.parse_args(argv); cmd=args.command or "serve"
    try:s,db,e,auth=build()
    except Exception as exc: print(f"configuration error: {exc}",file=sys.stderr); return 2
    if cmd=="doctor": print(json.dumps({"version":"1.0.0","environment":s.env,"database":str(s.database_path),"database_writable":s.database_path.parent.exists(),"provider":s.provider,"agents":len(db.list_agents()),"workspace_root":str(s.workspace_root),"shell_enabled":s.shell_enabled,"http_allowlist":list(s.http_allowlist)},indent=2)); e.shutdown(); return 0
    if cmd=="init": print(json.dumps({"ok":True,"database":str(s.database_path),"agents":len(db.list_agents())})); e.shutdown(); return 0
    e.recover(); serve(App(s,db,e,auth)); return 0
