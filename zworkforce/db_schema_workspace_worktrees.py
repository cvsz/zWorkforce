from __future__ import annotations

WORKSPACE_WORKTREE_SCHEMA_SQL = r'''
CREATE TABLE IF NOT EXISTS workspace_worktrees7(
    tenant_id TEXT NOT NULL,
    id TEXT NOT NULL,
    grant_id TEXT NOT NULL,
    repo_relative TEXT NOT NULL,
    worktree_relative TEXT NOT NULL,
    branch TEXT NOT NULL,
    start_ref TEXT NOT NULL DEFAULT 'HEAD',
    status TEXT NOT NULL DEFAULT 'active'
        CHECK(status IN ('active','removing','removed','error')),
    task_id TEXT NULL,
    created_by TEXT NOT NULL,
    expires_at TEXT NOT NULL,
    last_error TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    removed_at TEXT NULL,
    PRIMARY KEY(tenant_id,id),
    FOREIGN KEY(tenant_id,grant_id)
        REFERENCES workspace_grants6(tenant_id,id) ON DELETE RESTRICT
);
CREATE INDEX IF NOT EXISTS idx_workspace_worktrees7_active
    ON workspace_worktrees7(tenant_id,status,expires_at,id);
CREATE INDEX IF NOT EXISTS idx_workspace_worktrees7_grant
    ON workspace_worktrees7(tenant_id,grant_id,updated_at DESC,id);
'''
