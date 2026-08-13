import { randomUUID } from "node:crypto";

const TERMINAL = new Set(["succeeded", "failed", "cancelled", "expired"]);

export class AgentOrchestratorError extends Error {
  constructor(message, status = 400) {
    super(message);
    this.status = status;
  }
}

function requireString(value, name) {
  if (typeof value !== "string" || !value.trim()) {
    throw new AgentOrchestratorError(`${name} is required`, 400);
  }
  return value.trim();
}

function normalizeToolGrant(value) {
  if (typeof value === "string") {
    return { tool: value, scope: "*", mutating: !/:read$|\.read$/.test(value) };
  }
  if (!value || typeof value !== "object") {
    throw new AgentOrchestratorError("tool grant is invalid", 400);
  }
  return {
    tool: requireString(value.tool, "tool"),
    scope: requireString(value.scope ?? "*", "scope"),
    mutating: Boolean(value.mutating),
  };
}

function normalizeToolGrants(value, { allowEmpty = false } = {}) {
  if (!Array.isArray(value)) {
    throw new AgentOrchestratorError("tool_grants must be an array", 400);
  }
  if (!allowEmpty && value.length === 0) {
    throw new AgentOrchestratorError("tool_grants must not be empty", 400);
  }
  return value.map(normalizeToolGrant);
}

function grantKey(grant) {
  return `${grant.tool}\n${grant.scope}\n${grant.mutating}`;
}

function assertApprovedGrants(requested, approved) {
  const requestedKeys = new Set(requested.map(grantKey));
  for (const grant of approved) {
    if (!requestedKeys.has(grantKey(grant))) {
      throw new AgentOrchestratorError("approved tool grant was not requested", 400);
    }
  }
}

function buildEvent(type, job, now, extra = {}) {
  return {
    event_id: randomUUID(),
    event_type: type,
    event_version: "v1",
    occurred_at: now(),
    tenant_id: job.tenant_id,
    job_id: job.id,
    correlation_id: job.correlation_id,
    ...extra,
  };
}

export class MemoryJobStore {
  constructor({ jobs = new Map() } = {}) {
    this.jobs = jobs;
  }

  async findById(id) {
    return structuredClone(this.jobs.get(id) || null);
  }

  async findByIdempotency(tenantId, idempotencyKey) {
    const found = [...this.jobs.values()].find(
      (job) => job.tenant_id === tenantId && job.idempotency_key === idempotencyKey,
    );
    return structuredClone(found || null);
  }

  async save(job) {
    this.jobs.set(job.id, structuredClone(job));
    return structuredClone(job);
  }
}

export class MemoryQueueAdapter {
  constructor() {
    this.items = [];
  }

  async enqueue(item) {
    if (!this.items.some((queued) => queued.job_id === item.job_id && queued.attempt === item.attempt)) {
      this.items.push(structuredClone(item));
    }
    return structuredClone(item);
  }

  async dequeue() {
    return structuredClone(this.items.shift() || null);
  }

  size() {
    return this.items.length;
  }
}

export class MemoryAuditSink {
  constructor() {
    this.events = [];
  }

  async emit(event) {
    this.events.push(structuredClone(event));
    return structuredClone(event);
  }
}

export class AgentOrchestrator {
  constructor({
    store = new MemoryJobStore(),
    queue = new MemoryQueueAdapter(),
    audit = new MemoryAuditSink(),
    identity,
    worker,
    idGenerator = randomUUID,
    now = () => new Date().toISOString(),
  } = {}) {
    this.store = store;
    this.queue = queue;
    this.audit = audit;
    this.identity = identity;
    this.worker = worker;
    this.idGenerator = idGenerator;
    this.now = now;
  }

  async submit(input) {
    const tenantId = requireString(input.tenant_id, "tenant_id");
    const objective = requireString(input.objective ?? input.task, "task");
    const idempotencyKey = requireString(input.idempotency_key, "idempotency_key");
    const duplicate = await this.store.findByIdempotency(tenantId, idempotencyKey);
    if (duplicate) return { status: 200, job: duplicate };

    const job = {
      id: this.idGenerator(),
      tenant_id: tenantId,
      objective,
      task: objective,
      requested_tool_grants: normalizeToolGrants(input.tool_grants_requested ?? input.tool_grants),
      tool_grants: normalizeToolGrants(input.tool_grants_requested ?? input.tool_grants),
      input_refs: Array.isArray(input.input_refs) ? input.input_refs : [],
      status: "pending_approval",
      approval_state: "pending",
      idempotency_key: idempotencyKey,
      correlation_id: input.correlation_id,
      attempt: 0,
      max_retries: Number(input.max_retries ?? input.execution_policy?.max_retries ?? 1),
      timeout_seconds: Number(input.timeout_seconds ?? input.execution_policy?.timeout_seconds ?? 900),
      created_at: this.now(),
      updated_at: this.now(),
    };
    const saved = await this.store.save(job);
    await this.audit.emit(buildEvent("agent.job.requested.v1", saved, this.now, {
      requested_by: input.requested_by ?? { type: "service", id: "zarvis-task-gateway" },
      objective: saved.objective,
      input_refs: saved.input_refs,
      tool_grants_requested: saved.requested_tool_grants,
      execution_policy: {
        requires_approval: true,
        timeout_seconds: saved.timeout_seconds,
        max_retries: saved.max_retries,
      },
    }));
    return { status: 202, job: saved };
  }

  async approve(id, input) {
    const job = await this.get(id);
    if (job.status !== "pending_approval") {
      throw new AgentOrchestratorError("Job is not awaiting approval", 409);
    }
    const approvedBy = requireString(input.approved_by, "approved_by");
    if (this.identity) await this.identity.assertActorCanApprove({ type: "user", id: approvedBy }, job);
    const grants = normalizeToolGrants(input.tool_grants ?? job.requested_tool_grants);
    assertApprovedGrants(job.requested_tool_grants, grants);
    const next = await this.store.save({
      ...job,
      status: "approved",
      approval_state: "approved",
      approved_by: approvedBy,
      approved_at: this.now(),
      approved_tool_grants: grants,
      constraints: {
        sandbox: input.constraints?.sandbox ?? "restricted",
        network: input.constraints?.network ?? "deny-by-default",
        timeout_seconds: Number(input.constraints?.timeout_seconds ?? job.timeout_seconds),
        max_retries: Number(input.constraints?.max_retries ?? job.max_retries),
      },
      updated_at: this.now(),
    });
    await this.queue.enqueue({
      job_id: next.id,
      tenant_id: next.tenant_id,
      attempt: next.attempt + 1,
      enqueued_at: this.now(),
    });
    await this.audit.emit(buildEvent("agent.job.approved.v1", next, this.now, {
      approved_by: { type: "user", id: approvedBy },
      approval_state: "approved",
      tool_grants: grants,
      constraints: next.constraints,
    }));
    return next;
  }

  async get(id) {
    const job = await this.store.findById(id);
    if (!job) throw new AgentOrchestratorError("Job not found", 404);
    return job;
  }

  async cancel(id, input = {}) {
    const job = await this.get(id);
    if (TERMINAL.has(job.status)) {
      throw new AgentOrchestratorError("Job is already terminal", 409);
    }
    const next = await this.store.save({
      ...job,
      status: "cancelled",
      cancelled_by: input.cancelled_by,
      cancelled_at: this.now(),
      updated_at: this.now(),
    });
    await this.audit.emit(buildEvent("agent.job.completed.v1", next, this.now, {
      status: "cancelled",
      audit: { worker_id: "zarvis-task-gateway", attempt: next.attempt, tool_calls: [] },
    }));
    return next;
  }

  async retry(id) {
    const job = await this.get(id);
    if (job.status !== "failed") throw new AgentOrchestratorError("Only failed jobs can be retried", 409);
    if (job.attempt >= job.max_retries + 1) throw new AgentOrchestratorError("Retry limit exceeded", 409);
    const next = await this.store.save({ ...job, status: "approved", updated_at: this.now() });
    await this.queue.enqueue({
      job_id: next.id,
      tenant_id: next.tenant_id,
      attempt: next.attempt + 1,
      enqueued_at: this.now(),
    });
    return next;
  }

  async runNext() {
    const item = await this.queue.dequeue();
    if (!item) return null;
    const job = await this.get(item.job_id);
    if (job.status !== "approved") return job;
    const running = await this.store.save({
      ...job,
      status: "running",
      attempt: item.attempt,
      started_at: this.now(),
      updated_at: this.now(),
    });
    try {
      const result = await this.worker.execute(running);
      const completed = await this.store.save({
        ...running,
        ...result,
        status: result.status,
        updated_at: this.now(),
      });
      await this.audit.emit(buildEvent("agent.job.completed.v1", completed, this.now, {
        status: completed.status,
        result_refs: completed.result_refs,
        usage: completed.usage,
        audit: completed.audit,
      }));
      return completed;
    } catch (error) {
      const failed = await this.store.save({
        ...running,
        status: "failed",
        error: { code: "WORKER_FAILED", message: error?.message || "Worker failed" },
        audit: { worker_id: "zarvis-plan-worker", attempt: running.attempt, tool_calls: [] },
        updated_at: this.now(),
      });
      await this.audit.emit(buildEvent("agent.job.completed.v1", failed, this.now, {
        status: "failed",
        error: failed.error,
        audit: failed.audit,
      }));
      return failed;
    }
  }
}
