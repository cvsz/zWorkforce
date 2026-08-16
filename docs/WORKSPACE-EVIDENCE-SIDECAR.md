# Workspace Task Evidence Sidecar

The task evidence sidecar is a read-only projection over existing durable zWorkforce execution state. It does not introduce a second task store, workflow store, artifact store, approval system or audit stream.

## API

```text
GET /api/v1/tasks/{task_id}/sidecar
```

Authorization is identical to normal task reads: at least the `viewer` role plus `workforce:read`. Tenant identity is derived from the authenticated principal. A task from another tenant is returned as `404 task_not_found` rather than exposing cross-tenant existence.

## Projected evidence

The response composes bounded records from existing tables:

- task execution metadata and token/cost counters;
- chronological task event metadata;
- approval actor/decision/timestamp metadata;
- tool-call name, mutation/success flags, duration and argument **shape**;
- artifacts linked to the task by ID/hash/name/type/size;
- direct child/sub-agent tasks;
- workflow run/step references that point at the task;
- deterministic next-action hints derived only from task status and artifact presence.

## Data-minimization contract

The sidecar intentionally does not expose:

- raw task prompt;
- raw task result or error body;
- task-event detail bodies;
- approval comments;
- tool argument values;
- artifact `storage_uri` or artifact metadata values;
- workflow input/context/result bodies;
- child-task prompts/results.

Tool arguments are projected as structural types/counts/lengths. Keys that look like authorization, token, password, secret, credential, cookie or API-key material are marked `redacted`.

Artifact metadata is reduced to metadata key names. The artifact content hash remains available for provenance and integrity verification.

## Reliability contract

All projection queries are tenant-scoped and hard bounded. The sidecar is assembled at read time from authoritative durable records, so it cannot drift into a second source of truth. Missing optional evidence produces empty collections rather than synthesized records.

The response uses `returned_counts`, not `total_counts`. Per-collection hard bounds are published in `limits`, and `possibly_truncated[name]` is true whenever the returned collection reaches its bound. Consumers must not infer completeness when that flag is true.

Approvals currently use the existing task-scoped approval read without a separate projection limit because task approval cardinality is itself bounded by task policy. Event, tool-call, artifact, child-task and workflow-reference projections all have explicit sidecar limits.

The sidecar is presentation-independent and may be consumed by Web, WinUI, Z.A.R.V.I.S. or future review panels without changing execution state.
