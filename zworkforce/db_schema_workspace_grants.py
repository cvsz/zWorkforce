from __future__ import annotations

WORKSPACE_GRANT_SCHEMA_SQL = r'''
CREATE TABLE IF NOT EXISTS workspace_grants6(
    tenant_id TEXT NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    id TEXT NOT NULL,
    name TEXT NOT NULL,
    root_rel TEXT NOT NULL,
    read_enabled INTEGER NOT NULL DEFAULT 1,
    write_enabled INTEGER NOT NULL DEFAULT 0,
    commands_json TEXT NOT NULL DEFAULT '[]',
    network_policy TEXT NOT NULL DEFAULT 'deny' CHECK(network_policy IN ('deny','allowlisted')),
    enabled INTEGER NOT NULL DEFAULT 1,
    expires_at TEXT NULL,
    created_by TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    PRIMARY KEY(tenant_id,id)
);
CREATE INDEX IF NOT EXISTS idx_workspace_grants6_active
    ON workspace_grants6(tenant_id,enabled,expires_at,id);
'''
