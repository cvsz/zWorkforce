from __future__ import annotations

import re
import uuid
from typing import Any

from .db_base import json_dumps, utcnow

_PROJECT_STATUSES = {"active", "archived"}
_CONVERSATION_STATUSES = {"active", "archived"}
_RETENTION_POLICIES = {"standard", "ephemeral", "compliance_hold"}
_MESSAGE_ROLES = {"user", "assistant", "system", "tool"}
_ARTIFACT_ID_RE = re.compile(r"^[A-Za-z0-9._:-]{1,128}$")


def _uuid(value: str | None, label: str) -> str:
    if value is None:
        return str(uuid.uuid4())
    try:
        return str(uuid.UUID(str(value).strip()))
    except (ValueError, AttributeError, TypeError) as exc:
        raise ValueError(f"{label} must be a UUID") from exc


def _required_text(value: Any, label: str, maximum: int) -> str:
    text = str(value or "").strip()
    if not text:
        raise ValueError(f"{label} is required")
    if len(text) > maximum:
        raise ValueError(f"{label} must be at most {maximum} characters")
    return text


def _optional_text(value: Any, label: str, maximum: int) -> str:
    text = str(value or "").strip()
    if len(text) > maximum:
        raise ValueError(f"{label} must be at most {maximum} characters")
    return text


def _literal_like(value: str) -> str:
    return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def _artifact_ids(values: Any) -> list[str]:
    if values is None:
        return []
    if not isinstance(values, list):
        raise ValueError("artifact_ids must be an array")
    if len(values) > 50:
        raise ValueError("artifact_ids may contain at most 50 items")
    out: list[str] = []
    seen: set[str] = set()
    for raw in values:
        value = str(raw).strip()
        if not _ARTIFACT_ID_RE.fullmatch(value):
            raise ValueError("artifact_ids contains an invalid id")
        if value not in seen:
            seen.add(value)
            out.append(value)
    return out


class WorkspaceMixin:
    """Durable tenant-scoped projects, conversations and ordered messages."""

    def create_workspace_project(
        self,
        tenant_id: str,
        name: str,
        actor: str,
        *,
        description: str = "",
        project_id: str | None = None,
    ) -> dict[str, Any]:
        self.ensure_tenant(tenant_id)
        project_id = _uuid(project_id, "project id")
        name = _required_text(name, "project name", 200)
        description = _optional_text(description, "project description", 4000)
        if self.get_workspace_project(tenant_id, project_id):
            raise ValueError("project id already exists")
        now = utcnow()
        with self.connection() as c:
            c.execute(
                """INSERT INTO workspace_projects5(
                    tenant_id,id,name,description,status,pinned,sort_order,created_by,created_at,updated_at
                ) VALUES(?,?,?,?, 'active',0,0,?,?,?)""",
                (tenant_id, project_id, name, description, actor, now, now),
            )
        return self.get_workspace_project(tenant_id, project_id) or {}

    def get_workspace_project(self, tenant_id: str, project_id: str) -> dict[str, Any] | None:
        project_id = _uuid(project_id, "project id")
        with self.connection() as c:
            row = c.execute(
                "SELECT * FROM workspace_projects5 WHERE tenant_id=? AND id=?",
                (tenant_id, project_id),
            ).fetchone()
        return dict(row) if row else None

    def list_workspace_projects(
        self,
        tenant_id: str,
        *,
        status: str | None = None,
        query: str = "",
        limit: int = 100,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        clauses = ["tenant_id=?"]
        args: list[Any] = [tenant_id]
        if status:
            if status not in _PROJECT_STATUSES:
                raise ValueError("invalid project status")
            clauses.append("status=?")
            args.append(status)
        query = str(query or "").strip()
        if query:
            if len(query) > 200:
                raise ValueError("project query must be at most 200 characters")
            pattern = f"%{_literal_like(query.lower())}%"
            clauses.append("(lower(name) LIKE ? ESCAPE '\\' OR lower(description) LIKE ? ESCAPE '\\')")
            args.extend((pattern, pattern))
        args.extend((max(1, min(int(limit), 200)), max(0, int(offset))))
        sql = (
            "SELECT * FROM workspace_projects5 WHERE "
            + " AND ".join(clauses)
            + " ORDER BY pinned DESC,sort_order ASC,updated_at DESC,id ASC LIMIT ? OFFSET ?"
        )
        with self.connection() as c:
            return self._rows(c.execute(sql, tuple(args)).fetchall())

    def update_workspace_project(
        self,
        tenant_id: str,
        project_id: str,
        *,
        name: str | None = None,
        description: str | None = None,
        pinned: bool | None = None,
        status: str | None = None,
        sort_order: int | None = None,
    ) -> dict[str, Any]:
        current = self.get_workspace_project(tenant_id, project_id)
        if not current:
            raise ValueError("project not found")
        next_name = current["name"] if name is None else _required_text(name, "project name", 200)
        next_description = current["description"] if description is None else _optional_text(description, "project description", 4000)
        next_status = current["status"] if status is None else str(status)
        if next_status not in _PROJECT_STATUSES:
            raise ValueError("invalid project status")
        next_pinned = int(bool(current["pinned"])) if pinned is None else int(bool(pinned))
        next_sort = int(current["sort_order"]) if sort_order is None else int(sort_order)
        if next_sort < -1_000_000 or next_sort > 1_000_000:
            raise ValueError("sort_order is outside the supported range")
        with self.connection() as c:
            c.execute(
                """UPDATE workspace_projects5
                SET name=?,description=?,status=?,pinned=?,sort_order=?,updated_at=?
                WHERE tenant_id=? AND id=?""",
                (next_name, next_description, next_status, next_pinned, next_sort, utcnow(), tenant_id, current["id"]),
            )
        return self.get_workspace_project(tenant_id, current["id"]) or {}

    def create_workspace_conversation(
        self,
        tenant_id: str,
        actor: str,
        *,
        project_id: str | None = None,
        title: str = "",
        conversation_id: str | None = None,
        source_task_id: str | None = None,
        source_workflow_run_id: str | None = None,
        retention_policy: str = "standard",
    ) -> dict[str, Any]:
        self.ensure_tenant(tenant_id)
        conversation_id = _uuid(conversation_id, "conversation id")
        if self.get_workspace_conversation(tenant_id, conversation_id):
            raise ValueError("conversation id already exists")
        normalized_project_id = None
        if project_id:
            normalized_project_id = _uuid(project_id, "project id")
            project = self.get_workspace_project(tenant_id, normalized_project_id)
            if not project:
                raise ValueError("project not found")
            if project["status"] != "active":
                raise ValueError("cannot create a conversation in an archived project")
        if retention_policy not in _RETENTION_POLICIES:
            raise ValueError("invalid retention policy")
        source_task_id = _optional_text(source_task_id, "source task id", 128) or None
        source_workflow_run_id = _optional_text(source_workflow_run_id, "source workflow run id", 128) or None
        if source_task_id and hasattr(self, "get_task") and not self.get_task(tenant_id, source_task_id):
            raise ValueError("source task not found")
        if source_workflow_run_id and hasattr(self, "get_workflow_run") and not self.get_workflow_run(tenant_id, source_workflow_run_id):
            raise ValueError("source workflow run not found")
        title = str(title or "").strip()
        auto_named = not bool(title)
        title = "New conversation" if auto_named else _required_text(title, "conversation title", 300)
        now = utcnow()
        with self.connection() as c:
            c.execute(
                """INSERT INTO workspace_conversations5(
                    tenant_id,id,project_id,title,status,pinned,auto_named,source_task_id,source_workflow_run_id,
                    retention_policy,created_by,created_at,updated_at
                ) VALUES(?,?,?,?, 'active',0,?,?,?,?,?,?,?)""",
                (
                    tenant_id,
                    conversation_id,
                    normalized_project_id,
                    title,
                    int(auto_named),
                    source_task_id,
                    source_workflow_run_id,
                    retention_policy,
                    actor,
                    now,
                    now,
                ),
            )
        return self.get_workspace_conversation(tenant_id, conversation_id) or {}

    def get_workspace_conversation(self, tenant_id: str, conversation_id: str) -> dict[str, Any] | None:
        conversation_id = _uuid(conversation_id, "conversation id")
        with self.connection() as c:
            row = c.execute(
                "SELECT * FROM workspace_conversations5 WHERE tenant_id=? AND id=?",
                (tenant_id, conversation_id),
            ).fetchone()
        return dict(row) if row else None

    def list_workspace_conversations(
        self,
        tenant_id: str,
        *,
        query: str = "",
        project_id: str | None = None,
        status: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        clauses = ["c.tenant_id=?"]
        args: list[Any] = [tenant_id]
        if project_id:
            clauses.append("c.project_id=?")
            args.append(_uuid(project_id, "project id"))
        if status:
            if status not in _CONVERSATION_STATUSES:
                raise ValueError("invalid conversation status")
            clauses.append("c.status=?")
            args.append(status)
        query = str(query or "").strip()
        if query:
            if len(query) > 500:
                raise ValueError("conversation query must be at most 500 characters")
            pattern = f"%{_literal_like(query.lower())}%"
            clauses.append(
                "(lower(c.title) LIKE ? ESCAPE '\\' OR EXISTS ("
                "SELECT 1 FROM workspace_messages5 m WHERE m.tenant_id=c.tenant_id "
                "AND m.conversation_id=c.id AND lower(m.content) LIKE ? ESCAPE '\\'))"
            )
            args.extend((pattern, pattern))
        args.extend((max(1, min(int(limit), 200)), max(0, int(offset))))
        sql = (
            "SELECT c.* FROM workspace_conversations5 c WHERE "
            + " AND ".join(clauses)
            + " ORDER BY c.pinned DESC,c.updated_at DESC,c.id ASC LIMIT ? OFFSET ?"
        )
        with self.connection() as c:
            return self._rows(c.execute(sql, tuple(args)).fetchall())

    def update_workspace_conversation(
        self,
        tenant_id: str,
        conversation_id: str,
        *,
        title: str | None = None,
        pinned: bool | None = None,
        status: str | None = None,
        project_id: str | None | object = ...,
        retention_policy: str | None = None,
    ) -> dict[str, Any]:
        current = self.get_workspace_conversation(tenant_id, conversation_id)
        if not current:
            raise ValueError("conversation not found")
        next_title = current["title"] if title is None else _required_text(title, "conversation title", 300)
        next_status = current["status"] if status is None else str(status)
        if next_status not in _CONVERSATION_STATUSES:
            raise ValueError("invalid conversation status")
        next_pinned = int(bool(current["pinned"])) if pinned is None else int(bool(pinned))
        next_retention = current["retention_policy"] if retention_policy is None else str(retention_policy)
        if next_retention not in _RETENTION_POLICIES:
            raise ValueError("invalid retention policy")
        next_project_id = current["project_id"]
        if project_id is not ...:
            if project_id in (None, ""):
                next_project_id = None
            else:
                next_project_id = _uuid(str(project_id), "project id")
                project = self.get_workspace_project(tenant_id, next_project_id)
                if not project:
                    raise ValueError("project not found")
                if project["status"] != "active":
                    raise ValueError("cannot move a conversation into an archived project")
        with self.connection() as c:
            c.execute(
                """UPDATE workspace_conversations5
                SET project_id=?,title=?,status=?,pinned=?,auto_named=0,retention_policy=?,updated_at=?
                WHERE tenant_id=? AND id=?""",
                (
                    next_project_id,
                    next_title,
                    next_status,
                    next_pinned,
                    next_retention,
                    utcnow(),
                    tenant_id,
                    current["id"],
                ),
            )
        return self.get_workspace_conversation(tenant_id, current["id"]) or {}

    def delete_workspace_conversation(self, tenant_id: str, conversation_id: str) -> bool:
        current = self.get_workspace_conversation(tenant_id, conversation_id)
        if not current:
            return False
        if current["retention_policy"] == "compliance_hold":
            raise ValueError("conversation is under compliance hold")
        with self.connection() as c:
            result = c.execute(
                "DELETE FROM workspace_conversations5 WHERE tenant_id=? AND id=?",
                (tenant_id, current["id"]),
            )
        return bool(result.rowcount)

    def append_workspace_message(
        self,
        tenant_id: str,
        conversation_id: str,
        role: str,
        actor: str,
        *,
        content: str = "",
        artifact_ids: list[str] | None = None,
        parent_message_id: str | None = None,
        message_id: str | None = None,
    ) -> dict[str, Any]:
        conversation_id = _uuid(conversation_id, "conversation id")
        message_id = _uuid(message_id, "message id")
        if role not in _MESSAGE_ROLES:
            raise ValueError("invalid message role")
        content = str(content or "")
        if len(content) > 200_000:
            raise ValueError("message content must be at most 200000 characters")
        artifacts = _artifact_ids(artifact_ids)
        if not content.strip() and not artifacts:
            raise ValueError("message content or artifact_ids is required")
        normalized_parent = None
        if parent_message_id:
            normalized_parent = _uuid(parent_message_id, "parent message id")
            parent = self.get_workspace_message(tenant_id, normalized_parent)
            if not parent or parent["conversation_id"] != conversation_id:
                raise ValueError("parent message not found in conversation")
        now = utcnow()
        with self.connection() as c:
            c.execute("BEGIN IMMEDIATE")
            try:
                conversation = c.execute(
                    "SELECT status FROM workspace_conversations5 WHERE tenant_id=? AND id=?",
                    (tenant_id, conversation_id),
                ).fetchone()
                if not conversation:
                    raise ValueError("conversation not found")
                if conversation["status"] != "active":
                    raise ValueError("cannot append to an archived conversation")
                # Updating the parent row serializes ordinal allocation on PostgreSQL;
                # BEGIN IMMEDIATE already serializes writers on SQLite.
                c.execute(
                    "UPDATE workspace_conversations5 SET updated_at=? WHERE tenant_id=? AND id=?",
                    (now, tenant_id, conversation_id),
                )
                row = c.execute(
                    "SELECT COALESCE(MAX(ordinal),0) FROM workspace_messages5 WHERE tenant_id=? AND conversation_id=?",
                    (tenant_id, conversation_id),
                ).fetchone()
                ordinal = int(row[0]) + 1
                c.execute(
                    """INSERT INTO workspace_messages5(
                        tenant_id,id,conversation_id,ordinal,role,content,artifact_ids_json,parent_message_id,created_by,created_at
                    ) VALUES(?,?,?,?,?,?,?,?,?,?)""",
                    (
                        tenant_id,
                        message_id,
                        conversation_id,
                        ordinal,
                        role,
                        content,
                        json_dumps(artifacts),
                        normalized_parent,
                        actor,
                        now,
                    ),
                )
                c.execute("COMMIT")
            except Exception:
                c.execute("ROLLBACK")
                raise
        return self.get_workspace_message(tenant_id, message_id) or {}

    def get_workspace_message(self, tenant_id: str, message_id: str) -> dict[str, Any] | None:
        message_id = _uuid(message_id, "message id")
        with self.connection() as c:
            row = c.execute(
                "SELECT * FROM workspace_messages5 WHERE tenant_id=? AND id=?",
                (tenant_id, message_id),
            ).fetchone()
        return self._decode(dict(row)) if row else None

    def list_workspace_messages(
        self,
        tenant_id: str,
        conversation_id: str,
        *,
        limit: int = 200,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        conversation_id = _uuid(conversation_id, "conversation id")
        if not self.get_workspace_conversation(tenant_id, conversation_id):
            raise ValueError("conversation not found")
        with self.connection() as c:
            rows = c.execute(
                """SELECT * FROM workspace_messages5
                WHERE tenant_id=? AND conversation_id=?
                ORDER BY ordinal ASC LIMIT ? OFFSET ?""",
                (tenant_id, conversation_id, max(1, min(int(limit), 1000)), max(0, int(offset))),
            ).fetchall()
        return self._rows(rows)
