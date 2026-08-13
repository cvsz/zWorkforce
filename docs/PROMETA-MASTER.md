# ProMeta Master: Agents, Skills and Feature Operating Model

ProMeta is the canonical prompt-metadata and operating blueprint for
zWorkforce agents and skills. It defines what an agent is allowed to know, do,
delegate, approve, record and optimize across the full zWorkforce platform.

This document is intentionally implementation-facing. Runtime APIs are in
[API.md](API.md); production controls are in [PRODUCTION-READINESS.md](PRODUCTION-READINESS.md);
GitHub operations are in [GITHUB-OPERATIONS.md](GITHUB-OPERATIONS.md).
Codex-facing skills are stored under [`../.agents/skills/`](../.agents/skills/).
Runtime seed examples are stored in
[`../examples/prometa-agent-catalog.json`](../examples/prometa-agent-catalog.json)
and [`../examples/prometa-skills.json`](../examples/prometa-skills.json).

## Goals

1. Provide a complete master catalog for production-grade zWorkforce agents.
2. Keep skills small, signed, auditable and attachable to multiple agents.
3. Separate read-only analysis, mutating execution, approval authority and
   release authority.
4. Make every agent outcome measurable by cost, latency, quality, risk and
   business value.
5. Preserve tenant isolation, least privilege, explicit mutation intent and
   at-least-once external side-effect boundaries.

## Runtime feature domains

| Domain | Platform capability | Agent use |
| --- | --- | --- |
| Identity and tenancy | API keys, OIDC, signed proxy identity, roles, scopes | Bind every action to tenant, actor, role and scopes. |
| Task runtime | Durable task queue, leases, retries, dead letters | Execute work with idempotency and recoverable state. |
| Model routing | Luna/Terra/Sol tiers, provider pool, failover | Pick the cheapest model tier that can satisfy quality/SLO. |
| Policy | Tenant policy-as-code and explicit deny precedence | Stop unsafe tasks before provider or tool execution. |
| Approvals | Four-eyes and tool-specific approvals | Gate mutating actions and production-affecting changes. |
| Tools | Workspace, shell, HTTP, memory, artifacts, delegation | Expose capabilities through allowlists and audit events. |
| Workflows | DAGs, schedules, events and occurrence keys | Compose agents into repeatable automation. |
| Memory/RAG | Tenant-scoped memories, local/Qdrant vectors | Reuse knowledge without crossing tenant boundaries. |
| Artifacts | Local/S3 content-addressed artifacts | Store durable outputs with hashes and provenance. |
| Evaluation | A/B suites and outcome criteria | Compare agent/model strategies before promotion. |
| FinOps | Budgets, chargeback, capacity and recommendations | Keep cost visible per tenant, department and agent. |
| Observability | Health, readiness, metrics and OTLP traces | Debug operations and enforce SLOs. |
| Release/GitHub | CI, CodeQL, release, GHCR, Dependency Review | Keep repository changes reviewable and releasable. |
| Z.A.R.V.I.S. | Local assistant services, contracts and Windows client | Operate the consolidated package boundary safely. |

## Agent contract

Every production agent should have:

- `id`: DNS-like stable slug.
- `name`: human-readable role.
- `description`: one operational responsibility.
- `department`: chargeback and policy dimension.
- `default_tier`: `luna`, `terra` or `sol`.
- `max_cost_credits`: tenant-visible spend limit.
- `max_iterations`: bounded reasoning/execution loop.
- `max_subagents`: delegation limit.
- `required_approvals`: number of distinct human approvals for risky work.
- `requires_approval_for_mutations`: fail-closed mutation gate.
- `allowed_tools`: exact tool allowlist.
- `approval_tools`: tools treated as sensitive after a mutating task has an
  approval requirement. This does not independently create an approval gate when
  `requires_approval_for_mutations` is false and `required_approvals` is zero.
- `skill_ids`: signed skill manifests attached to this agent.
- `system_prompt`: role, boundaries, output contract and escalation rules.
- `enabled`: deployment switch.

## Master agent catalog

| Agent | Department | Tier | Mutation | Core purpose |
| --- | --- | --- | --- | --- |
| `intake-triage` | operations | luna | no | Classify requests, tenant, priority, risk and required evidence. |
| `planner` | operations | terra | no | Break complex requests into bounded workflow steps and acceptance criteria. |
| `research-analyst` | research | terra | no | Gather evidence, cite sources and separate facts from assumptions. |
| `code-architect` | engineering | sol | no | Design module boundaries, migration plans and risk controls. |
| `implementation-engineer` | engineering | terra | yes | Make scoped code changes with tests and rollback notes. |
| `code-reviewer` | engineering | terra | no | Find defects, regressions, security issues and missing tests. |
| `security-reviewer` | security | sol | no | Threat-model changes, secrets, auth, SSRF, policy and supply chain. |
| `release-engineer` | engineering | terra | yes | Build, test, package, tag and verify releases. |
| `github-operator` | platform | terra | yes | Manage PRs, branches, checks, alerts, releases and GHCR cleanup. |
| `sre-operator` | platform | terra | yes | Run health checks, incidents, backup/restore and rollout operations. |
| `database-operator` | data | sol | yes | Plan schema changes, migrations, PostgreSQL drills and recovery. |
| `finops-analyst` | finance | luna | no | Analyze budgets, chargeback, capacity and model cost efficiency. |
| `workflow-automator` | operations | terra | yes | Create workflows, schedules, event rules and idempotent automation. |
| `memory-curator` | knowledge | luna | yes | Curate tenant memory, tags, embeddings and stale knowledge cleanup. |
| `artifact-librarian` | knowledge | luna | yes | Store, verify and retrieve content-addressed artifacts. |
| `zarvis-operator` | product | terra | yes | Maintain Z.A.R.V.I.S. contracts, services, local runbooks and Windows client. |
| `compliance-auditor` | governance | sol | no | Verify audit chain, approvals, evidence and release governance. |
| `incident-commander` | operations | sol | yes | Coordinate production incidents, rollback, comms and evidence capture. |

## Skill catalog

Skills are reusable prompt/tool policy overlays. They should be signed before
remote installation and remain small enough for audit.

| Skill ID | Applies to | Allowed tools | Purpose |
| --- | --- | --- | --- |
| `repo-review` | code-reviewer, security-reviewer | `workspace_list`, `workspace_read` | Conservative repository review and risk reporting. |
| `release-verification` | release-engineer, compliance-auditor | `workspace_list`, `workspace_read`, `shell_exec` | Run release verifier, tests, SBOM/checksum checks and CI evidence review. |
| `github-operations` | github-operator, release-engineer | `workspace_read`, `shell_exec`, `http_get` | Inspect PRs, checks, review threads, branches, releases and package state. |
| `secure-editing` | implementation-engineer | `workspace_read`, `workspace_write`, `shell_exec` | Scoped code edits with tests, no secret leakage and rollback notes. |
| `policy-audit` | security-reviewer, compliance-auditor | `workspace_read`, `memory_search` | Review RBAC, scopes, policy-as-code and approval behavior. |
| `postgres-recovery` | database-operator, sre-operator | `shell_exec`, `workspace_read` | Backup/restore drills, schema compatibility and recovery evidence. |
| `workflow-design` | planner, workflow-automator | `workspace_read`, `workspace_write` | Author DAGs, schedules, event rules and idempotency criteria. |
| `finops-optimization` | finops-analyst | `memory_search`, `calculator` | Analyze spend, rightsizing, budgets and tier recommendations. |
| `rag-curation` | memory-curator | `memory_search`, `workspace_read`, `workspace_write` | Maintain tenant knowledge, tags and reindex plans. |
| `artifact-provenance` | artifact-librarian, compliance-auditor | `workspace_read`, `workspace_write` | Verify hashes, artifact metadata and release evidence bundles. |
| `zarvis-contracts` | zarvis-operator | `workspace_read`, `shell_exec` | Validate Z.A.R.V.I.S. contracts, package tests and Windows restore checks. |
| `incident-response` | incident-commander, sre-operator | `workspace_read`, `shell_exec`, `http_get` | Drive incident triage, rollback criteria, timelines and evidence. |

The repo-local Codex skill names are prefixed with `zworkforce-` so they can be
discovered as project-specific instructions, while runtime manifests keep short
stable IDs such as `repo-review` and `release-verification`.

## Prompt metadata blocks

Each agent prompt should include these blocks in order:

```text
ROLE:
  One sentence defining responsibility and authority.

TENANT AND ACTOR:
  Tenant id, actor id, role, scopes and delegated authority.

OBJECTIVE:
  Concrete outcome and acceptance criteria.

CONSTRAINTS:
  Budget, model tier, timeout, allowed tools, mutation status and approval state.

CONTEXT:
  Relevant task, workflow, memory, artifact, repository or incident references.

RISK CONTROLS:
  Data isolation, secrets, policy, network, side effects and rollback boundary.

OUTPUT CONTRACT:
  Required result structure, evidence, commands run, residual risk and next step.
```

## Tool policy matrix

| Tool class | Read-only agents | Mutating agents | Production agents |
| --- | --- | --- | --- |
| Workspace read | requires `workspace_read` allowlist from the agent or skill | requires `workspace_read` allowlist from the agent or skill | explicit allowlist with audit |
| Workspace write | denied | approval required | approval and rollback note required |
| Shell execution | denied by default | executable allowlist and active approval requirement | approval, sanitized env and command evidence |
| HTTP fetch | allowlisted public endpoints | allowlisted endpoints only | allowlisted endpoints, no private SSRF |
| Memory search | tenant scoped | tenant scoped | tenant scoped with sensitive-data review |
| Memory write | denied by default | approval or curator role | approval and retention policy |
| Artifact write | task scoped | task/workflow scoped | hash, owner and release evidence required |
| Agent delegation | bounded by `max_subagents` | bounded and audited | bounded, audited and evidence preserving |

## Operating workflows

### Repository change workflow

1. `intake-triage` classifies scope, risk and affected surfaces.
2. `planner` creates a bounded plan and acceptance checks.
3. `implementation-engineer` edits files and adds tests.
4. `code-reviewer` and `security-reviewer` inspect risk.
5. `release-engineer` runs local validation.
6. `github-operator` opens PR, tracks checks, resolves review threads and
   merges only after required checks pass.
7. `compliance-auditor` records evidence for production-affecting changes.

### Release workflow

1. Verify version metadata, changelog, Compose/Kubernetes image references and
   release docs.
2. Run Python, Z.A.R.V.I.S., Windows, security, dependency and release gates.
3. Verify SBOM, checksums, provenance and GHCR image tags.
4. Publish an immutable tag only from a commit reachable from `main`.
5. Attach Windows MSIX only when trusted signing secrets are configured.

### Production incident workflow

1. `incident-commander` opens the incident record and freezes risky automation.
2. `sre-operator` checks health, readiness, queue age, provider circuits,
   scheduler/outbox leadership and recent deploys.
3. `database-operator` verifies PostgreSQL health and backup posture.
4. `security-reviewer` checks auth, secrets, policy and suspicious events.
5. `release-engineer` prepares rollback or hotfix evidence.
6. `compliance-auditor` validates timeline, approvals and recovery evidence.

## Feature completeness map

| Feature | Minimum agent coverage | Minimum skill coverage | Evidence |
| --- | --- | --- | --- |
| Durable task execution | planner, implementation-engineer | workflow-design | task events, retries, dead letters |
| Workflow automation | workflow-automator | workflow-design | workflow run and occurrence key |
| Security review | security-reviewer | policy-audit, repo-review | threat model and tests |
| Release engineering | release-engineer | release-verification, artifact-provenance | CI, SBOM, checksums, provenance |
| GitHub operations | github-operator | github-operations | PR/check/review/branch evidence |
| PostgreSQL operations | database-operator | postgres-recovery | backup/restore and migration logs |
| FinOps | finops-analyst | finops-optimization | chargeback, budget and capacity reports |
| Z.A.R.V.I.S. package | zarvis-operator | zarvis-contracts | package tests, API audit, Windows restore |
| Production readiness | compliance-auditor | incident-response, release-verification | sign-offs and drill evidence |

## Acceptance criteria

An agent/skill set is complete when:

1. Every production-impacting workflow has a named accountable agent.
2. Every mutating tool has approval policy and audit coverage.
3. Every skill manifest validates, is signed when remotely installed, and has a
   versioned purpose.
4. Every release candidate has local validation, GitHub checks, artifact
   evidence and rollback notes.
5. Every operator-owned dependency is marked as external evidence, not assumed
   from repository files.
