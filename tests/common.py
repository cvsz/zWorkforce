from __future__ import annotations

from pathlib import Path
import tempfile

from zworkforce.config import BootstrapKey, ProviderConfig, Settings
from zworkforce.db import Database
from zworkforce.engine import Engine
from zworkforce.providers import build_provider
from zworkforce.security import AuthManager


def stack(*, embedded_workers=0, required_key=True):
    temp = tempfile.TemporaryDirectory()
    root = Path(temp.name)
    settings = Settings(
        data_dir=root / "data",
        workspace_root=root / "workspace",
        embedded_workers=embedded_workers,
        worker_poll_ms=25,
        lease_seconds=10,
        lease_heartbeat_seconds=2,
        max_attempts=3,
        retry_base_seconds=1,
        providers=(ProviderConfig(name="mock", kind="mock", models={"luna": "mock-luna", "terra": "mock-terra", "sol": "mock-sol"}),),
        bootstrap_keys=(BootstrapKey("test-admin-secret", "superadmin", "default", "test-admin"),) if required_key else (),
    )
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    settings.workspace_root.mkdir(parents=True, exist_ok=True)
    db = Database(settings.database_path, settings.default_tenant)
    provider = build_provider(settings, db)
    engine = Engine(settings, db, provider)
    auth = AuthManager(db, settings.bootstrap_keys)
    return temp, settings, db, provider, engine, auth
