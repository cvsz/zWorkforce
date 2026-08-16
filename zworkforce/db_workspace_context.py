from __future__ import annotations

import hashlib
import uuid
from typing import Any

from .db_base import utcnow


def _uuid(value: str | None, label: str) -> str:
    if value is None:
        return str(uuid.uuid4())
    try:
        return str(uuid.UUID(str(value).strip()))
    except (ValueError, AttributeError, TypeError) as exc:
        raise ValueError(f"{label} must be a UUID") from exc


def _positive_int(value: Any, label: str, *, maximum: int = 10_000_000) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{label} must be an integer") from exc
    if parsed <= 0 or parsed > maximum:
        raise ValueError(f"{label} must be between 1 and {maximum}")
    return parsed


def _estimate_tokens(text: str) -> int:
    # Deterministic conservative approximation used only for preflight/context accounting.
    # Provider-reported usage remains authoritative when available.
    return max(1, (len(text.encode("utf-8")) + 3) // 4)


class WorkspaceContextMixin:
    """Durable, tenant-scoped workspace context accounting and compaction snapshots."""

    def create_workspace_context_snapshot(
        self,
        tenant_id: str,
        conversation_id: str,
        actor: str,
        *,
        model_id: str,
        context_ceiling_tokens: int,
        compaction_threshold_tokens: int,
        message_ids: list[str] | None = None,
        reason: str = "context-checkpoint",
        summary: str = "",
        snapshot_id: str | None = None,
    ) -> dict[str, Any]:
        conversation_id = _uuid(conversation_id, "conversation id")
        snapshot_id = _uuid(snapshot_id, "snapshot id")
        conversation = self.get_workspace_conversation(tenant_id, conversation_id)
        if not conversation:
            raise ValueError("conversation not found")
        model_id = str(model_id or "").strip()
        if not model_id or len(model_id) > 200:
            raise ValueError("model_id is required and must be at most 200 characters")
        ceiling = _positive_int(context_ceiling_tokens, "context_ceiling_tokens")
        threshold = _positive_int(compaction_threshold_tokens, "compaction_threshold_tokens")
        if threshold > ceiling:
            raise ValueError("compaction_threshold_tokens cannot exceed context_ceiling_tokens")
        reason = str(reason or "").strip()
        if not reason or len(reason) > 200:
            raise ValueError("reason is required and must be at most 200 characters")
        summary = str(summary or "")
        if len(summary) > 200_000:
            raise ValueError("summary must be at most 200000 characters")

        messages = self.list_workspace_messages(tenant_id, conversation_id)
        by_id = {item["id"]: item for item in messages}
        if message_ids is None:
            selected = messages
        else:
            if not isinstance(message_ids, list) or len(message_ids) > 1000:
                raise ValueError("message_ids must be an array with at most 1000 items")
            selected = []
            seen: set[str] = set()
            for raw in message_ids:
                message_id = _uuid(raw, "message id")
                if message_id in seen:
                    continue
                seen.add(message_id)
                message = by_id.get(message_id)
                if not message:
                    raise ValueError("message not found in conversation")
                selected.append(message)
            selected.sort(key=lambda item: int(item["ordinal"]))

        estimates = [(item, _estimate_tokens(str(item.get("content", "")))) for item in selected]
        estimated_total = sum(tokens for _, tokens in estimates)
        summary_sha256 = hashlib.sha256(summary.encode("utf-8")).hexdigest() if summary else ""
        now = utcnow()

        with self.connection() as c:
            c.execute("BEGIN IMMEDIATE")
            try:
                c.execute(
                    """INSERT INTO workspace_context_snapshots5(
                        tenant_id,id,conversation_id,model_id,context_ceiling_tokens,estimated_tokens,
                        compaction_threshold_tokens,reason,summary,summary_sha256,created_by,created_at
                    ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)""",
                    (
                        tenant_id,
                        snapshot_id,
                        conversation_id,
                        model_id,
                        ceiling,
                        estimated_total,
                        threshold,
                        reason,
                        summary,
                        summary_sha256,
                        actor,
                        now,
                    ),
                )
                for item, tokens in estimates:
                    c.execute(
                        """INSERT INTO workspace_context_members5(
                            tenant_id,snapshot_id,message_id,ordinal,estimated_tokens
                        ) VALUES(?,?,?,?,?)""",
                        (tenant_id, snapshot_id, item["id"], int(item["ordinal"]), tokens),
                    )
                c.execute("COMMIT")
            except Exception:
                c.execute("ROLLBACK")
                raise
        return self.get_workspace_context_snapshot(tenant_id, snapshot_id) or {}

    def get_workspace_context_snapshot(self, tenant_id: str, snapshot_id: str) -> dict[str, Any] | None:
        snapshot_id = _uuid(snapshot_id, "snapshot id")
        with self.connection() as c:
            row = c.execute(
                "SELECT * FROM workspace_context_snapshots5 WHERE tenant_id=? AND id=?",
                (tenant_id, snapshot_id),
            ).fetchone()
            if not row:
                return None
            result = dict(row)
            members = c.execute(
                """SELECT message_id,ordinal,estimated_tokens FROM workspace_context_members5
                WHERE tenant_id=? AND snapshot_id=? ORDER BY ordinal ASC,message_id ASC""",
                (tenant_id, snapshot_id),
            ).fetchall()
        result["members"] = [dict(item) for item in members]
        return result

    def list_workspace_context_snapshots(
        self, tenant_id: str, conversation_id: str, *, limit: int = 100
    ) -> list[dict[str, Any]]:
        conversation_id = _uuid(conversation_id, "conversation id")
        if not self.get_workspace_conversation(tenant_id, conversation_id):
            raise ValueError("conversation not found")
        bounded_limit = max(1, min(int(limit), 200))
        with self.connection() as c:
            rows = c.execute(
                """SELECT * FROM workspace_context_snapshots5
                WHERE tenant_id=? AND conversation_id=? ORDER BY created_at DESC,id DESC LIMIT ?""",
                (tenant_id, conversation_id, bounded_limit),
            ).fetchall()
        return [dict(row) for row in rows]

    def compact_workspace_conversation(
        self,
        tenant_id: str,
        conversation_id: str,
        actor: str,
        *,
        model_id: str,
        context_ceiling_tokens: int,
        compaction_threshold_tokens: int,
        summary: str,
        message_ids: list[str] | None = None,
        reason: str = "manual-compact",
    ) -> dict[str, Any]:
        summary = str(summary or "").strip()
        if not summary:
            raise ValueError("summary is required for compaction")
        return self.create_workspace_context_snapshot(
            tenant_id,
            conversation_id,
            actor,
            model_id=model_id,
            context_ceiling_tokens=context_ceiling_tokens,
            compaction_threshold_tokens=compaction_threshold_tokens,
            message_ids=message_ids,
            reason=reason,
            summary=summary,
        )
