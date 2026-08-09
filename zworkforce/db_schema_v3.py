from __future__ import annotations

V3_SCHEMA_SQL = r"""


CREATE TABLE IF NOT EXISTS policies3(
    tenant_id TEXT NOT NULL,
    id TEXT NOT NULL,
    name TEXT NOT NULL,
    document_json TEXT NOT NULL,
    enabled INTEGER NOT NULL DEFAULT 1,
    created_by TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    PRIMARY KEY(tenant_id,id)
);
CREATE INDEX IF NOT EXISTS idx_policies3_enabled ON policies3(tenant_id,enabled,id);

CREATE TABLE IF NOT EXISTS agent_templates3(
    tenant_id TEXT NOT NULL,
    id TEXT NOT NULL,
    name TEXT NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    template_json TEXT NOT NULL,
    enabled INTEGER NOT NULL DEFAULT 1,
    created_by TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    PRIMARY KEY(tenant_id,id)
);
CREATE TABLE IF NOT EXISTS agent_versions3(
    id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    agent_id TEXT NOT NULL,
    version INTEGER NOT NULL,
    snapshot_json TEXT NOT NULL,
    created_by TEXT NOT NULL,
    created_at TEXT NOT NULL,
    UNIQUE(tenant_id,agent_id,version)
);
CREATE INDEX IF NOT EXISTS idx_agent_versions3_agent ON agent_versions3(tenant_id,agent_id,version DESC);

CREATE TABLE IF NOT EXISTS workflows3(
    tenant_id TEXT NOT NULL,
    id TEXT NOT NULL,
    name TEXT NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    version INTEGER NOT NULL DEFAULT 1,
    definition_json TEXT NOT NULL,
    enabled INTEGER NOT NULL DEFAULT 1,
    created_by TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    PRIMARY KEY(tenant_id,id)
);
CREATE TABLE IF NOT EXISTS workflow_runs3(
    id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    workflow_id TEXT NOT NULL,
    workflow_version INTEGER NOT NULL,
    status TEXT NOT NULL,
    actor TEXT NOT NULL,
    input_json TEXT NOT NULL DEFAULT '{}',
    context_json TEXT NOT NULL DEFAULT '{}',
    error TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL,
    started_at TEXT NULL,
    finished_at TEXT NULL
);
CREATE INDEX IF NOT EXISTS idx_workflow_runs3_tenant ON workflow_runs3(tenant_id,created_at DESC);
CREATE TABLE IF NOT EXISTS workflow_steps3(
    run_id TEXT NOT NULL,
    tenant_id TEXT NOT NULL,
    step_id TEXT NOT NULL,
    agent_id TEXT NOT NULL,
    status TEXT NOT NULL,
    depends_on_json TEXT NOT NULL DEFAULT '[]',
    definition_json TEXT NOT NULL DEFAULT '{}',
    task_id TEXT NULL,
    result TEXT NULL,
    error TEXT NOT NULL DEFAULT '',
    started_at TEXT NULL,
    finished_at TEXT NULL,
    PRIMARY KEY(run_id,step_id)
);
CREATE INDEX IF NOT EXISTS idx_workflow_steps3_task ON workflow_steps3(task_id);
CREATE TABLE IF NOT EXISTS schedules3(
    tenant_id TEXT NOT NULL,
    id TEXT NOT NULL,
    name TEXT NOT NULL,
    target_type TEXT NOT NULL CHECK(target_type IN ('workflow','agent')),
    target_id TEXT NOT NULL,
    schedule_type TEXT NOT NULL CHECK(schedule_type IN ('cron','interval')),
    cron_expr TEXT NOT NULL DEFAULT '',
    interval_seconds INTEGER NOT NULL DEFAULT 0,
    timezone TEXT NOT NULL DEFAULT 'UTC',
    payload_json TEXT NOT NULL DEFAULT '{}',
    next_run_at TEXT NOT NULL,
    last_run_at TEXT NULL,
    last_error TEXT NOT NULL DEFAULT '',
    enabled INTEGER NOT NULL DEFAULT 1,
    created_by TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    PRIMARY KEY(tenant_id,id)
);
CREATE INDEX IF NOT EXISTS idx_schedules3_due ON schedules3(enabled,next_run_at);
CREATE TABLE IF NOT EXISTS event_rules3(
    tenant_id TEXT NOT NULL,
    id TEXT NOT NULL,
    name TEXT NOT NULL,
    event_type TEXT NOT NULL,
    target_type TEXT NOT NULL CHECK(target_type IN ('workflow','agent')),
    target_id TEXT NOT NULL,
    filter_json TEXT NOT NULL DEFAULT '{}',
    payload_template_json TEXT NOT NULL DEFAULT '{}',
    enabled INTEGER NOT NULL DEFAULT 1,
    created_by TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    PRIMARY KEY(tenant_id,id)
);
CREATE INDEX IF NOT EXISTS idx_event_rules3_type ON event_rules3(tenant_id,event_type,enabled);
CREATE TABLE IF NOT EXISTS events3(
    id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    event_type TEXT NOT NULL,
    source TEXT NOT NULL,
    dedupe_key TEXT NOT NULL DEFAULT '',
    payload_json TEXT NOT NULL DEFAULT '{}',
    status TEXT NOT NULL DEFAULT 'pending',
    attempts INTEGER NOT NULL DEFAULT 0,
    error TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL,
    processed_at TEXT NULL
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_events3_dedupe ON events3(tenant_id,source,dedupe_key) WHERE dedupe_key<>'';
CREATE INDEX IF NOT EXISTS idx_events3_pending ON events3(status,created_at);
CREATE TABLE IF NOT EXISTS evaluation_suites3(
    tenant_id TEXT NOT NULL,
    id TEXT NOT NULL,
    name TEXT NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    agent_id TEXT NOT NULL,
    cases_json TEXT NOT NULL,
    variants_json TEXT NOT NULL,
    enabled INTEGER NOT NULL DEFAULT 1,
    created_by TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    PRIMARY KEY(tenant_id,id)
);
CREATE TABLE IF NOT EXISTS evaluation_runs3(
    id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    suite_id TEXT NOT NULL,
    status TEXT NOT NULL,
    actor TEXT NOT NULL,
    summary_json TEXT NOT NULL DEFAULT '{}',
    error TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL,
    finished_at TEXT NULL
);
CREATE TABLE IF NOT EXISTS evaluation_results3(
    id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    run_id TEXT NOT NULL,
    case_id TEXT NOT NULL,
    variant TEXT NOT NULL,
    task_id TEXT NOT NULL,
    status TEXT NOT NULL,
    outcome_status TEXT NULL,
    outcome_score REAL NULL,
    cost_credits REAL NOT NULL DEFAULT 0,
    duration_ms REAL NOT NULL DEFAULT 0,
    result TEXT NULL,
    error TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL,
    finished_at TEXT NULL,
    UNIQUE(run_id,case_id,variant)
);
CREATE INDEX IF NOT EXISTS idx_eval_results3_run ON evaluation_results3(run_id);
CREATE TABLE IF NOT EXISTS artifacts3(
    id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    task_id TEXT NULL,
    workflow_run_id TEXT NULL,
    name TEXT NOT NULL,
    content_type TEXT NOT NULL DEFAULT 'application/octet-stream',
    storage_uri TEXT NOT NULL,
    sha256 TEXT NOT NULL,
    size_bytes INTEGER NOT NULL,
    metadata_json TEXT NOT NULL DEFAULT '{}',
    created_by TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_artifacts3_tenant ON artifacts3(tenant_id,created_at DESC);
CREATE TABLE IF NOT EXISTS slo_policies3(
    tenant_id TEXT NOT NULL,
    id TEXT NOT NULL,
    metric TEXT NOT NULL CHECK(metric IN ('success_rate','outcome_rate','p95_duration_ms','avg_queue_ms','dead_letter_rate')),
    comparator TEXT NOT NULL CHECK(comparator IN ('gte','lte')),
    target REAL NOT NULL,
    window_hours INTEGER NOT NULL DEFAULT 24,
    severity TEXT NOT NULL DEFAULT 'warning',
    enabled INTEGER NOT NULL DEFAULT 1,
    updated_at TEXT NOT NULL,
    PRIMARY KEY(tenant_id,id)
);
CREATE TABLE IF NOT EXISTS tenant_settings3(
    tenant_id TEXT PRIMARY KEY,
    currency TEXT NOT NULL DEFAULT 'USD',
    currency_per_credit REAL NOT NULL DEFAULT 0.01,
    target_worker_utilization REAL NOT NULL DEFAULT 0.70,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS memory_vectors3(
    memory_id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    agent_id TEXT NULL,
    dimension INTEGER NOT NULL,
    vector_json TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_memory_vectors3_tenant ON memory_vectors3(tenant_id,updated_at DESC);


CREATE TABLE IF NOT EXISTS service_leases3(
    name TEXT PRIMARY KEY,
    owner TEXT NOT NULL,
    expires_at TEXT NOT NULL,
    heartbeat_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_service_leases3_expires ON service_leases3(expires_at);

CREATE TABLE IF NOT EXISTS outbox3(
    id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    topic TEXT NOT NULL,
    destination TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    signature TEXT NOT NULL DEFAULT '',
    status TEXT NOT NULL DEFAULT 'pending',
    attempts INTEGER NOT NULL DEFAULT 0,
    next_attempt_at TEXT NOT NULL,
    last_error TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL,
    delivered_at TEXT NULL
);
CREATE INDEX IF NOT EXISTS idx_outbox3_due ON outbox3(status,next_attempt_at);
"""
