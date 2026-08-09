from __future__ import annotations

import argparse
import json
from pathlib import Path
import socket
import sys

from . import __version__
from .api import App, serve
from .config import Settings
from .db import Database
from .engine import Engine
from .providers import build_provider
from .security import AuthManager
from .skills import sign_manifest, validate_manifest


def build():
    settings = Settings.from_env()
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    db = Database(settings.database_path, settings.default_tenant)
    provider = build_provider(settings, db)
    engine = Engine(settings, db, provider)
    auth = AuthManager(db, settings.bootstrap_keys, settings.trust_proxy_identity, settings.proxy_identity_secret)
    return settings, db, engine, auth, provider


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="zworkforce", description="AI Workforce control plane and durable agent runtime")
    p.add_argument("--version", action="version", version=__version__)
    sub = p.add_subparsers(dest="command")
    sub.add_parser("serve", help="Run the API/control-plane server")
    worker = sub.add_parser("worker", help="Run a durable queue worker")
    worker.add_argument("--id", default="")
    worker.add_argument("--once", action="store_true")
    sub.add_parser("doctor", help="Validate configuration and runtime dependencies")
    sub.add_parser("init", help="Initialize/migrate the database")
    tenant = sub.add_parser("tenant-create", help="Create a tenant and seed default agents")
    tenant.add_argument("id")
    tenant.add_argument("--name", default="")
    key = sub.add_parser("key-create", help="Create an API key and print its secret once")
    key.add_argument("--tenant", default="")
    key.add_argument("--name", required=True)
    key.add_argument("--role", choices=["viewer", "operator", "admin", "superadmin"], default="viewer")
    key.add_argument("--scopes", default="*")
    verify = sub.add_parser("audit-verify", help="Verify the tenant audit hash chain")
    verify.add_argument("--tenant", default="")
    skill = sub.add_parser("skill-sign", help="Sign a skill manifest using ZWORKFORCE_SKILL_SIGNING_KEY")
    skill.add_argument("file")
    return p


def main(argv=None):
    args = parser().parse_args(argv)
    cmd = args.command or "serve"
    try:
        settings, db, engine, auth, provider = build()
    except Exception as exc:
        print(f"configuration error: {exc}", file=sys.stderr)
        return 2

    try:
        if cmd == "doctor":
            health = provider.models()
            report = {
                "version": __version__,
                "environment": settings.env,
                "database": str(settings.database_path),
                "database_ready": db.ready(),
                "schema_version": 2,
                "default_tenant": settings.default_tenant,
                "tenants": len(db.list_tenants()),
                "agents": len(db.list_agents(settings.default_tenant)),
                "workspace_root": str(settings.workspace_root),
                "workspace_exists": settings.workspace_root.exists(),
                "shell_enabled": settings.shell_enabled,
                "http_allowlist": list(settings.http_allowlist),
                "embedded_workers": settings.embedded_workers,
                "providers": [{"name": x["name"], "kind": x["kind"], "available": x["available"], "models": x["models"]} for x in health],
                "audit": db.verify_audit_chain(settings.default_tenant),
            }
            print(json.dumps(report, indent=2, ensure_ascii=False))
            return 0 if report["database_ready"] and report["workspace_exists"] else 1
        if cmd == "init":
            print(json.dumps({"ok": True, "database": str(settings.database_path), "schema_version": 2, "tenants": len(db.list_tenants())}, indent=2))
            return 0
        if cmd == "tenant-create":
            tenant = db.ensure_tenant(args.id.strip().lower(), args.name or args.id)
            print(json.dumps(tenant, indent=2, ensure_ascii=False))
            return 0
        if cmd == "key-create":
            tenant_id = (args.tenant or settings.default_tenant).strip().lower()
            db.ensure_tenant(tenant_id)
            key_id, secret = auth.create_key(tenant_id, args.name, args.role, [x.strip() for x in args.scopes.split(",") if x.strip()])
            print(json.dumps({"id": key_id, "tenant_id": tenant_id, "name": args.name, "role": args.role, "secret": secret, "warning": "Store this secret now; it is not retrievable later."}, indent=2))
            return 0
        if cmd == "audit-verify":
            tenant_id = (args.tenant or settings.default_tenant).strip().lower()
            result = db.verify_audit_chain(tenant_id)
            print(json.dumps(result, indent=2))
            return 0 if result["ok"] else 1
        if cmd == "skill-sign":
            manifest = json.loads(Path(args.file).read_text(encoding="utf-8"))
            validate_manifest(manifest)
            print(sign_manifest(manifest, settings.skill_signing_key))
            return 0
        if cmd == "worker":
            engine.recover()
            worker_id = args.id.strip() or f"worker-{socket.gethostname()}"
            processed = engine.worker_loop(worker_id, once=args.once)
            if args.once:
                print(json.dumps({"processed": processed, "worker_id": worker_id}))
            return 0
        serve(App(settings, db, engine, auth, provider))
        return 0
    finally:
        if cmd != "serve":
            engine.shutdown()


if __name__ == "__main__":
    raise SystemExit(main())
