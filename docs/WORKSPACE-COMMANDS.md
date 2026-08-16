# Workspace Slash Command Registry

The workspace slash-command registry is a server-authorized intent layer. It does **not** execute side effects by itself and does not replace task, workflow, skill, context, artifact, FinOps, policy or approval APIs.

## API

Command discovery requires `viewer + workspace:read`:

```text
GET /api/v1/workspaces/commands
```

Each item reports its required role/scope, target intent, mutability classification and whether the authenticated principal currently satisfies that command's authorization envelope.

Command resolution also requires `viewer + workspace:read` before command-specific authorization is evaluated:

```text
POST /api/v1/workspaces/commands/resolve
{"text":"/compact summarize messages 1-20"}
```

A successful response is only a normalized, authorized intent. It never creates a task, invokes a skill, changes a workflow, compacts context, writes feedback or performs another external mutation. The caller must dispatch the returned target through its authoritative API, where normal policy, approvals, idempotency and audit controls still apply.

Resolved intents have a stable presentation-independent shape:

```json
{
  "name": "compact",
  "description": "Create an explicit durable context-compaction snapshot.",
  "role": "operator",
  "scope": "workspace:compact",
  "target": "workspace.compact",
  "mutating": true,
  "available": true,
  "argument": "summarize messages 1-20",
  "tenant_id": "default",
  "resolved": true
}
```

`tenant_id` is derived from the authenticated request after the normal tenant-resolution rules; it is never parsed from the command argument.

## Commands

| Command | Minimum role | Required scope | Target | Mutating intent |
| --- | --- | --- | --- | --- |
| `/plan` | operator | `task:write` | `task.plan` | yes |
| `/review` | viewer | `workforce:read` | `workspace.review` | no |
| `/compact` | operator | `workspace:compact` | `workspace.compact` | yes |
| `/goal` | operator | `workspace:write` | `workspace.goal` | yes |
| `/status` | viewer | `workforce:read` | `workspace.status` | no |
| `/artifacts` | viewer | `workforce:read` | `workspace.artifacts` | no |
| `/cost` | viewer | `workforce:read` | `workspace.cost` | no |
| `/skill` | admin | `skill:write` | `skill.manage` | yes |
| `/workflow` | admin | `automation:write` | `workflow.manage` | yes |
| `/feedback` | operator | `workspace:write` | `workspace.feedback` | yes |

## Security contract

- command names are a fixed server-side allowlist;
- command text and arguments have hard length bounds;
- unknown commands fail closed;
- discovery does not imply authorization; `available` is calculated from the authenticated principal;
- resolution performs command-specific role/scope checks server-side;
- workspace scopes cannot impersonate admin skill/workflow scopes;
- resolution is deliberately non-executing, preventing the parser from becoming an authorization bypass;
- tenant identity comes from the authenticated request and is never accepted from command text;
- later UI dispatch must use authoritative APIs and preserve their policy/approval/idempotency requirements.
