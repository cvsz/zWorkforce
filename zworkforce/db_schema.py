from __future__ import annotations

SCHEMA_SQL = '''
                CREATE TABLE IF NOT EXISTS schema_meta(key TEXT PRIMARY KEY,value TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS tenants(
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    enabled INTEGER NOT NULL DEFAULT 1,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS agents2(
                    tenant_id TEXT NOT NULL REFERENCES tenants(id),
                    id TEXT NOT NULL,
                    name TEXT NOT NULL,
                    description TEXT NOT NULL DEFAULT '',
                    department TEXT NOT NULL DEFAULT 'general',
                    default_tier TEXT NOT NULL CHECK(default_tier IN ('sol','terra','luna')),
                    max_cost_credits REAL NOT NULL DEFAULT 50,
                    max_iterations INTEGER NOT NULL DEFAULT 8,
                    max_subagents INTEGER NOT NULL DEFAULT 2,
                    required_approvals INTEGER NOT NULL DEFAULT 1,
                    requires_approval_for_mutations INTEGER NOT NULL DEFAULT 1,
                    system_prompt TEXT NOT NULL DEFAULT '',
                    allowed_tools_json TEXT NOT NULL DEFAULT '[]',
                    approval_tools_json TEXT NOT NULL DEFAULT '[]',
                    skill_ids_json TEXT NOT NULL DEFAULT '[]',
                    enabled INTEGER NOT NULL DEFAULT 1,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    PRIMARY KEY(tenant_id,id)
                );
                CREATE TABLE IF NOT EXISTS tasks2(
                    id TEXT PRIMARY KEY,
                    tenant_id TEXT NOT NULL REFERENCES tenants(id),
                    agent_id TEXT NOT NULL,
                    prompt TEXT NOT NULL,
                    created_by TEXT NOT NULL,
                    status TEXT NOT NULL,
                    tier TEXT NOT NULL CHECK(tier IN ('sol','terra','luna')),
                    model TEXT NOT NULL,
                    provider_name TEXT NOT NULL DEFAULT '',
                    mutating INTEGER NOT NULL DEFAULT 0,
                    parent_task_id TEXT NULL REFERENCES tasks2(id),
                    depth INTEGER NOT NULL DEFAULT 0,
                    required_approvals INTEGER NOT NULL DEFAULT 0,
                    approved_at TEXT NULL,
                    priority INTEGER NOT NULL DEFAULT 0,
                    attempt INTEGER NOT NULL DEFAULT 0,
                    max_attempts INTEGER NOT NULL DEFAULT 3,
                    run_after TEXT NOT NULL,
                    lease_owner TEXT NULL,
                    lease_expires_at TEXT NULL,
                    heartbeat_at TEXT NULL,
                    result TEXT NULL,
                    error TEXT NULL,
                    input_tokens INTEGER NOT NULL DEFAULT 0,
                    cached_tokens INTEGER NOT NULL DEFAULT 0,
                    output_tokens INTEGER NOT NULL DEFAULT 0,
                    cost_credits REAL NOT NULL DEFAULT 0,
                    iterations INTEGER NOT NULL DEFAULT 0,
                    cancel_requested INTEGER NOT NULL DEFAULT 0,
                    success_criteria_json TEXT NOT NULL DEFAULT '[]',
                    outcome_status TEXT NULL,
                    outcome_score REAL NULL,
                    outcome_details_json TEXT NOT NULL DEFAULT '{}',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    started_at TEXT NULL,
                    finished_at TEXT NULL,
                    FOREIGN KEY(tenant_id,agent_id) REFERENCES agents2(tenant_id,id)
                );
                CREATE INDEX IF NOT EXISTS idx_tasks2_queue ON tasks2(status,run_after,priority DESC,created_at);
                CREATE INDEX IF NOT EXISTS idx_tasks2_tenant_created ON tasks2(tenant_id,created_at DESC);
                CREATE INDEX IF NOT EXISTS idx_tasks2_lease ON tasks2(status,lease_expires_at);
                CREATE TABLE IF NOT EXISTS task_events2(
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    tenant_id TEXT NOT NULL,
                    task_id TEXT NOT NULL REFERENCES tasks2(id) ON DELETE CASCADE,
                    event_type TEXT NOT NULL,
                    actor TEXT NOT NULL,
                    details_json TEXT NOT NULL DEFAULT '{}',
                    created_at TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_task_events2_task ON task_events2(task_id,id);
                CREATE TABLE IF NOT EXISTS approvals2(
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    tenant_id TEXT NOT NULL,
                    task_id TEXT NOT NULL REFERENCES tasks2(id) ON DELETE CASCADE,
                    actor TEXT NOT NULL,
                    decision TEXT NOT NULL CHECK(decision IN ('approve','reject')),
                    comment TEXT NOT NULL DEFAULT '',
                    created_at TEXT NOT NULL,
                    UNIQUE(task_id,actor)
                );
                CREATE TABLE IF NOT EXISTS usage_events2(
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    tenant_id TEXT NOT NULL,
                    task_id TEXT NOT NULL REFERENCES tasks2(id) ON DELETE CASCADE,
                    agent_id TEXT NOT NULL,
                    department TEXT NOT NULL,
                    tier TEXT NOT NULL,
                    provider_name TEXT NOT NULL,
                    model TEXT NOT NULL,
                    input_tokens INTEGER NOT NULL,
                    cached_tokens INTEGER NOT NULL,
                    output_tokens INTEGER NOT NULL,
                    cost_credits REAL NOT NULL,
                    created_at TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_usage2_tenant_created ON usage_events2(tenant_id,created_at DESC);
                CREATE TABLE IF NOT EXISTS budgets2(
                    tenant_id TEXT NOT NULL,
                    scope_type TEXT NOT NULL CHECK(scope_type IN ('global','department','agent')),
                    scope_id TEXT NOT NULL,
                    period TEXT NOT NULL CHECK(period IN ('daily','monthly')),
                    limit_credits REAL NOT NULL,
                    updated_at TEXT NOT NULL,
                    PRIMARY KEY(tenant_id,scope_type,scope_id,period)
                );
                CREATE TABLE IF NOT EXISTS idempotency_keys2(
                    tenant_id TEXT NOT NULL,
                    actor TEXT NOT NULL,
                    key TEXT NOT NULL,
                    task_id TEXT NOT NULL REFERENCES tasks2(id),
                    request_hash TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    PRIMARY KEY(tenant_id,actor,key)
                );
                CREATE TABLE IF NOT EXISTS audit_events2(
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    tenant_id TEXT NOT NULL,
                    actor TEXT NOT NULL,
                    action TEXT NOT NULL,
                    target_type TEXT NOT NULL,
                    target_id TEXT NOT NULL,
                    details_json TEXT NOT NULL DEFAULT '{}',
                    prev_hash TEXT NOT NULL DEFAULT '',
                    event_hash TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_audit2_tenant ON audit_events2(tenant_id,id DESC);
                CREATE TABLE IF NOT EXISTS api_keys2(
                    id TEXT PRIMARY KEY,
                    tenant_id TEXT NOT NULL REFERENCES tenants(id),
                    name TEXT NOT NULL,
                    key_hash TEXT NOT NULL UNIQUE,
                    role TEXT NOT NULL CHECK(role IN ('viewer','operator','admin','superadmin')),
                    scopes_json TEXT NOT NULL DEFAULT '["*"]',
                    disabled INTEGER NOT NULL DEFAULT 0,
                    created_at TEXT NOT NULL,
                    last_used_at TEXT NULL,
                    revoked_at TEXT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_api_keys2_tenant ON api_keys2(tenant_id,name);
                CREATE TABLE IF NOT EXISTS memories2(
                    id TEXT PRIMARY KEY,
                    tenant_id TEXT NOT NULL REFERENCES tenants(id),
                    agent_id TEXT NULL,
                    title TEXT NOT NULL,
                    content TEXT NOT NULL,
                    tags_json TEXT NOT NULL DEFAULT '[]',
                    created_by TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_memories2_tenant ON memories2(tenant_id,updated_at DESC);
                CREATE TABLE IF NOT EXISTS skills2(
                    tenant_id TEXT NOT NULL REFERENCES tenants(id),
                    id TEXT NOT NULL,
                    version TEXT NOT NULL,
                    manifest_json TEXT NOT NULL,
                    signature TEXT NOT NULL DEFAULT '',
                    enabled INTEGER NOT NULL DEFAULT 1,
                    created_by TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    PRIMARY KEY(tenant_id,id)
                );
                CREATE TABLE IF NOT EXISTS tool_events2(
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    tenant_id TEXT NOT NULL,
                    task_id TEXT NOT NULL REFERENCES tasks2(id) ON DELETE CASCADE,
                    agent_id TEXT NOT NULL,
                    tool_name TEXT NOT NULL,
                    mutating INTEGER NOT NULL DEFAULT 0,
                    success INTEGER NOT NULL,
                    duration_ms REAL NOT NULL DEFAULT 0,
                    args_json TEXT NOT NULL DEFAULT '{}',
                    error TEXT NOT NULL DEFAULT '',
                    created_at TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_tool_events2_task ON tool_events2(task_id,id);
                CREATE TABLE IF NOT EXISTS provider_health2(
                    name TEXT PRIMARY KEY,
                    consecutive_failures INTEGER NOT NULL DEFAULT 0,
                    successes INTEGER NOT NULL DEFAULT 0,
                    failures INTEGER NOT NULL DEFAULT 0,
                    last_latency_ms REAL NULL,
                    last_error TEXT NOT NULL DEFAULT '',
                    last_success_at TEXT NULL,
                    last_failure_at TEXT NULL,
                    open_until TEXT NULL,
                    updated_at TEXT NOT NULL
                );
'''
