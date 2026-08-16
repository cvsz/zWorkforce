from __future__ import annotations

WORKSPACE_SCHEMA_SQL = '''
                CREATE TABLE IF NOT EXISTS workspace_projects5(
                    tenant_id TEXT NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
                    id TEXT NOT NULL,
                    name TEXT NOT NULL,
                    description TEXT NOT NULL DEFAULT '',
                    status TEXT NOT NULL DEFAULT 'active' CHECK(status IN ('active','archived')),
                    pinned INTEGER NOT NULL DEFAULT 0,
                    sort_order INTEGER NOT NULL DEFAULT 0,
                    created_by TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    PRIMARY KEY(tenant_id,id)
                );
                CREATE INDEX IF NOT EXISTS idx_workspace_projects5_tenant_updated
                    ON workspace_projects5(tenant_id,status,pinned DESC,updated_at DESC);

                CREATE TABLE IF NOT EXISTS workspace_conversations5(
                    tenant_id TEXT NOT NULL,
                    id TEXT NOT NULL,
                    project_id TEXT NULL,
                    title TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'active' CHECK(status IN ('active','archived')),
                    pinned INTEGER NOT NULL DEFAULT 0,
                    auto_named INTEGER NOT NULL DEFAULT 0,
                    source_task_id TEXT NULL,
                    source_workflow_run_id TEXT NULL,
                    retention_policy TEXT NOT NULL DEFAULT 'standard'
                        CHECK(retention_policy IN ('standard','ephemeral','compliance_hold')),
                    created_by TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    PRIMARY KEY(tenant_id,id),
                    FOREIGN KEY(tenant_id,project_id)
                        REFERENCES workspace_projects5(tenant_id,id) ON DELETE RESTRICT
                );
                CREATE INDEX IF NOT EXISTS idx_workspace_conversations5_tenant_updated
                    ON workspace_conversations5(tenant_id,status,pinned DESC,updated_at DESC);
                CREATE INDEX IF NOT EXISTS idx_workspace_conversations5_project
                    ON workspace_conversations5(tenant_id,project_id,updated_at DESC);

                CREATE TABLE IF NOT EXISTS workspace_messages5(
                    tenant_id TEXT NOT NULL,
                    id TEXT NOT NULL,
                    conversation_id TEXT NOT NULL,
                    role TEXT NOT NULL CHECK(role IN ('user','assistant','system','tool')),
                    content TEXT NOT NULL,
                    artifact_ids_json TEXT NOT NULL DEFAULT '[]',
                    parent_message_id TEXT NULL,
                    created_by TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    PRIMARY KEY(tenant_id,id),
                    FOREIGN KEY(tenant_id,conversation_id)
                        REFERENCES workspace_conversations5(tenant_id,id) ON DELETE CASCADE
                );
                CREATE INDEX IF NOT EXISTS idx_workspace_messages5_conversation
                    ON workspace_messages5(tenant_id,conversation_id,created_at,id);
'''
