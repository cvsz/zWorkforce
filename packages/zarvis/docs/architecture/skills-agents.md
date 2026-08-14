# Z.A.R.V.I.S. Skills + Agents Architecture

## 1. Purpose

Z.A.R.V.I.S. uses two different concepts that must not be mixed:

1. **Repository coding-agent skills** under `.agents/skills/` — instructions for coding agents modifying `cvsz/zworkforce`.
2. **Runtime Z.A.R.V.I.S. skills and agents** — capabilities executed by the product under tenant, policy, approval and audit controls.

OpenJarvis's skill catalog and on-demand/scheduled/continuous agent modes are useful references. zWorkforce's existing durable execution and authorization model remains authoritative.

## 2. Runtime skill architecture

A runtime skill is a versioned, policy-governed workflow. It is not arbitrary prompt text and it is not automatically trusted because it exists on disk.

### Required manifest

Every runtime skill MUST declare:

- stable `id` and semantic `version`;
- human-readable name/description;
- `input_schema` and `output_schema`;
- `required_capabilities`;
- `allowed_tools`;
- `mutability`: `read_only`, `proposal`, or `mutating`;
- `approval_policy`;
- timeout and max concurrency;
- retry policy;
- idempotency strategy for durable/external effects;
- audit event types;
- owner and rollback/version policy;
- optional dependencies on other skills.

### Discovery rules

- deterministic search paths and precedence;
- duplicate IDs fail closed unless a documented version selection rule resolves them;
- dependency graph validation rejects cycles;
- missing tools/capabilities reject activation;
- a `mutating` skill without approval policy is invalid;
- production activation is explicit; discovery alone does not grant execution rights;
- trace-mined/generated skills are candidates only and require review/tests before activation.

### Initial runtime skill domains

| Domain | Example skills | Default policy |
|---|---|---|
| Conversation | concise reply, multilingual response, spoken summary | read-only |
| Memory | recall, summarize session, propose memory, forget conversation | recall read-only; durable write/delete policy-bound |
| Research | source collection, synthesis, fact verification | read-only network tools only when granted |
| Engineering | repo explore, review, test diagnosis, repair proposal | read-only by default; edits require scoped mutation grant |
| Operations | service health, incident triage, release evidence | read-only by default; remediation approval-gated |
| Productivity | briefings, reminders, task coordination | subscription/connector scoped |
| Governance | policy explanation, audit review, approval preparation | read-only/proposal |

## 3. Runtime agent architecture

### Agent modes

#### `on_demand`

Triggered by a user/API request. Ends when the requested outcome or bounded failure condition is reached.

Required controls:

- authenticated tenant/subject context;
- max turns/tool calls/time;
- capability/tool allowlist;
- explicit mutation approvals;
- trace and audit correlation.

#### `scheduled`

Triggered by the existing durable zWorkforce scheduler. It MUST NOT introduce a parallel scheduler.

Additional controls:

- stable occurrence/idempotency key;
- version-pinned agent definition;
- missed-run/catch-up policy;
- concurrency policy;
- subscription/owner context.

#### `continuous`

A persistent/long-horizon operator implemented as bounded recurring work with durable state, not an unbounded process with unrestricted authority.

Additional controls:

- lease/heartbeat;
- stalled-run detection;
- per-agent rate limit and max concurrency;
- pause/resume/disable;
- failure budget/backoff;
- version pin and rollback;
- bounded memory/session growth;
- no privilege expansion without operator-approved configuration change.

## 4. Agent catalog

### New orchestration agents

#### `voice-orchestrator`

Purpose: optimize the spoken-turn path for latency and clarity while preserving policy.

Responsibilities:

- classify a final transcript into conversation, read-only skill, approval-required proposal or specialist-agent handoff;
- keep spoken responses concise while preserving full structured result for the UI/audit trail;
- support interruption/cancel;
- never treat a spoken command as implicit approval for a mutating action;
- prefer existing specialists rather than solving every domain itself.

#### `operator-supervisor`

Purpose: supervise scheduled/continuous agents.

Responsibilities:

- heartbeat/liveness status;
- detect stale or repeatedly failing operators;
- enforce rate/concurrency/failure budgets;
- recommend pause/restart/rollback;
- produce operator-visible diagnostics;
- never broaden permissions or deploy production infrastructure autonomously.

### Existing agents to reuse

The current `packages/zarvis/agents/` catalog already contains specialist roles. Integration should reuse them instead of cloning equivalent agents.

Key reuse groups:

- **Coordination:** `chief-of-staff`.
- **Memory/context:** `brain-memory-agent`.
- **Architecture/exploration:** `architect`, `code-architect`, `code-explorer`.
- **Review/quality:** `code-reviewer`, language/framework reviewers, accessibility/performance specialists.
- **Build/repair:** build-error resolvers and framework-specific repair agents.

## 5. Agent handoff contract

A handoff should be structured rather than free-form:

```json
{
  "schema_version": "zarvis.agent.handoff.v1",
  "request_id": "...",
  "session_id": "...",
  "from_agent": "voice-orchestrator",
  "to_agent": "code-explorer",
  "objective": "...",
  "context_refs": ["..."],
  "required_capabilities": ["repo.read"],
  "allowed_tools": ["github.read"],
  "mutation": false,
  "deadline_ms": 30000
}
```

The receiving agent cannot expand `required_capabilities`, `allowed_tools` or mutation scope. Any expansion requires a new policy/approval decision.

## 6. Voice-to-agent routing

```text
PTT final transcript
       |
       v
voice-orchestrator
       |
       +--> normal conversation
       |
       +--> runtime skill (read-only)
       |
       +--> specialist agent
       |
       +--> proposal needing approval
                    |
                    v
             task/action gateway
                    |
             explicit approval
                    |
                    v
               execution
```

The voice UI exposes `approval_required` as a first-class state and reads the proposal back when useful. Approval is recorded through the existing approval contract, not inferred from model intent.

## 7. Skill + agent observability

Record, with redaction:

- agent/skill ID + version;
- trigger mode;
- model/provider route;
- latency by phase;
- tool invocations and policy decisions;
- approval transitions;
- outcome status/score;
- retries, lease recovery and rate-limit events;
- cost/energy metrics when available;
- trace correlation IDs, not raw secrets/audio.

## 8. Repository coding-agent skills

Two repository skills accompany this architecture:

- `.agents/skills/zworkforce-zarvis-voice-ui/SKILL.md`
- `.agents/skills/zworkforce-zarvis-runtime-orchestration/SKILL.md`

These are development guardrails. They do not become runtime product skills and do not grant runtime permissions.

## 9. Feature matrix

| Capability | Existing baseline | Upgrade |
|---|---|---|
| Realtime voice | ZVoice AudioWorklet/PCM16 + gateway/agent | shared voice client + dashboard card |
| Animated presence | ZVoice orb + humanoid | compact state-driven dashboard orb |
| Interruption | existing ZVoice barge-in/cancel | shared contract across both clients |
| STT/TTS | current voice runtime | typed provider registry/capability health |
| Agent catalog | broad specialist markdown catalog | add voice orchestrator + operator supervisor |
| Runtime skills | orchestration/tool capabilities exist | explicit manifest/catalog/policy model |
| Scheduled work | durable zWorkforce scheduler | agent-mode integration, no new scheduler |
| Continuous work | proactive/runtime pieces exist | leases/heartbeat/rate limit/version rollback |
| Memory | tenant/context services exist | voice-session continuity + consent-bound writes |
| Cloud routing | provider routing/FinOps exists | complexity/redaction/taint-aware policy |
| Observability | platform telemetry exists | voice + skill + operator phase metrics |

## 10. Definition of done

Skills + Agents are complete when manifests are validated and versioned; runtime invocation cannot exceed declared capabilities; scheduled and continuous modes use the durable zWorkforce scheduler/lease semantics; voice routing can hand work to existing specialists; supervision detects stalled/runaway work; and every mutation still passes through explicit approval/action controls.