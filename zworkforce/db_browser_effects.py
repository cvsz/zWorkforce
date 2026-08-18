from __future__ import annotations

import re
import uuid
from typing import Any

from .db_base import utcnow

_KEY_RE = re.compile(r"^[A-Za-z0-9._:-]{1,128}$")
_SHA_RE = re.compile(r"^[0-9a-f]{64}$")
_EFFECT_STATES = frozenset({"not_started", "executing", "succeeded", "failed", "unknown", "canceled"})


class BrowserEffectMixin:
    def begin_browser_effect(
        self,
        tenant_id: str,
        *,
        idempotency_key: str,
        action_sha256: str,
        approval_task_id: str,
    ) -> dict[str, Any]:
        key = str(idempotency_key or "").strip()
        digest = str(action_sha256 or "").strip().lower()
        approval_id = str(approval_task_id or "").strip()
        if not _KEY_RE.fullmatch(key):
            raise ValueError("browser effect requires a bounded idempotency key")
        if not _SHA_RE.fullmatch(digest):
            raise ValueError("browser effect action digest is invalid")
        if not approval_id:
            raise ValueError("browser effect approval task id is required")
        now = utcnow()
        effect_id = str(uuid.uuid4())
        with self.connection() as c:
            approval = c.execute(
                "SELECT id FROM tasks2 WHERE tenant_id=? AND id=? AND mutating=1 AND approved_at IS NOT NULL",
                (tenant_id, approval_id),
            ).fetchone()
            if not approval:
                raise ValueError("browser effect approval task is not an approved tenant mutation")
            c.execute(
                """INSERT INTO browser_effects3(
                    id,tenant_id,idempotency_key,action_sha256,approval_task_id,status,created_at,updated_at
                ) VALUES(?,?,?,?,?,'not_started',?,?)
                ON CONFLICT(tenant_id,idempotency_key) DO NOTHING""",
                (effect_id, tenant_id, key, digest, approval_id, now, now),
            )
            row = c.execute(
                "SELECT * FROM browser_effects3 WHERE tenant_id=? AND idempotency_key=?",
                (tenant_id, key),
            ).fetchone()
        if not row:
            raise RuntimeError("browser effect ledger insert failed")
        effect = self._decode(dict(row))
        if effect["action_sha256"] != digest or effect["approval_task_id"] != approval_id:
            raise ValueError("browser effect idempotency key was already used for a different approved action")
        return effect

    def get_browser_effect(self, tenant_id: str, effect_id: str) -> dict[str, Any] | None:
        with self.connection() as c:
            row = c.execute(
                "SELECT * FROM browser_effects3 WHERE tenant_id=? AND id=?",
                (tenant_id, effect_id),
            ).fetchone()
        return self._decode(dict(row)) if row else None

    def claim_browser_effect(self, tenant_id: str, effect_id: str) -> tuple[dict[str, Any], bool]:
        now = utcnow()
        with self.connection() as c:
            changed = c.execute(
                """UPDATE browser_effects3 SET status='executing',started_at=COALESCE(started_at,?),updated_at=?
                WHERE tenant_id=? AND id=? AND status='not_started'""",
                (now, now, tenant_id, effect_id),
            ).rowcount
            row = c.execute(
                "SELECT * FROM browser_effects3 WHERE tenant_id=? AND id=?",
                (tenant_id, effect_id),
            ).fetchone()
        if not row:
            raise ValueError("browser effect not found")
        return self._decode(dict(row)), bool(changed)

    def finish_browser_effect(
        self,
        tenant_id: str,
        effect_id: str,
        *,
        status: str,
        result_sha256: str = "",
        error_code: str = "",
    ) -> dict[str, Any]:
        target = str(status or "").strip().lower()
        if target not in {"succeeded", "failed", "unknown", "canceled"}:
            raise ValueError("invalid browser effect terminal status")
        result = str(result_sha256 or "").strip().lower()
        if result and not _SHA_RE.fullmatch(result):
            raise ValueError("browser effect result digest is invalid")
        now = utcnow()
        with self.connection() as c:
            changed = c.execute(
                """UPDATE browser_effects3 SET status=?,result_sha256=?,error_code=?,finished_at=?,updated_at=?
                WHERE tenant_id=? AND id=? AND status='executing'""",
                (target, result, str(error_code or "")[:128], now, now, tenant_id, effect_id),
            ).rowcount
            row = c.execute(
                "SELECT * FROM browser_effects3 WHERE tenant_id=? AND id=?",
                (tenant_id, effect_id),
            ).fetchone()
        if not row:
            raise ValueError("browser effect not found")
        if not changed:
            raise ValueError("browser effect is not executing")
        return self._decode(dict(row))

    def reconcile_browser_effect(
        self,
        tenant_id: str,
        effect_id: str,
        *,
        status: str,
        result_sha256: str = "",
        error_code: str = "",
    ) -> dict[str, Any]:
        target = str(status or "").strip().lower()
        if target not in {"succeeded", "failed"}:
            raise ValueError("browser effect reconciliation must resolve to succeeded or failed")
        result = str(result_sha256 or "").strip().lower()
        if result and not _SHA_RE.fullmatch(result):
            raise ValueError("browser effect result digest is invalid")
        now = utcnow()
        with self.connection() as c:
            changed = c.execute(
                """UPDATE browser_effects3 SET status=?,result_sha256=?,error_code=?,finished_at=?,updated_at=?
                WHERE tenant_id=? AND id=? AND status='unknown'""",
                (target, result, str(error_code or "")[:128], now, now, tenant_id, effect_id),
            ).rowcount
            row = c.execute(
                "SELECT * FROM browser_effects3 WHERE tenant_id=? AND id=?",
                (tenant_id, effect_id),
            ).fetchone()
        if not row:
            raise ValueError("browser effect not found")
        if not changed:
            raise ValueError("only unknown browser effects can be reconciled")
        return self._decode(dict(row))
