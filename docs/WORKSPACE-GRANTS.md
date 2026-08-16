# Durable Workspace Grants

Workspace grants are tenant-scoped, operator-managed authorization records for local workspace roots. The configured `ZWORKFORCE_WORKSPACE_ROOT` remains the hard host-level ceiling; a grant can only select an existing directory **inside** that ceiling.

This control-plane slice stores and validates grants. It does not by itself claim OS process/network isolation. Filesystem/tool enforcement and bounded process execution are delivered separately so a stored `network_policy` is never mistaken for an enforced network sandbox.

## API

Grant management requires at least the `admin` role plus `workspace:grant`.

```text
GET  /api/v1/workspaces/grants
POST /api/v1/workspaces/grants
POST /api/v1/workspaces/grants/{id}/disable
```

Example creation request:

```json
{
  "name": "Repository A",
  "root": "projects/repository-a",
  "read": true,
  "write": false,
  "commands": ["git"],
  "network_policy": "deny",
  "expires_at": "2026-08-18T06:00:00+07:00"
}
```

`root` must be relative to the configured host workspace root. Absolute POSIX paths, Windows drive/UNC paths, missing directories, traversal outside the host root, and symlink/junction targets outside the host root are rejected.

The durable record stores the approved canonical **relative** root as `root_rel`; it does not persist an absolute host path. This makes the authorization record portable across workers that mount the same approved workspace at different host paths while retaining the configured host ceiling on each worker.

## Grant fields

- `id`: opaque UUID.
- `name`: operator label.
- `root_rel`: canonical relative path inside `ZWORKFORCE_WORKSPACE_ROOT`.
- `read`: whether file-read capabilities may use the grant.
- `write`: whether file-write capabilities may use the grant.
- `commands`: executable names declared for the later process-sandbox boundary. Names must already be in `ZWORKFORCE_SHELL_ALLOWLIST`.
- `network_policy`: `deny` or `allowlisted`, declared for the later process-sandbox boundary.
- `enabled`: false disables future use.
- `expires_at`: timezone-aware ISO-8601 timestamp. New API grants must expire in the future and within 365 days.
- creation/update actor and timestamps.

## Canonical-path safety

Grant creation resolves the requested path against the configured workspace root and requires an existing directory. Grant use must re-resolve the stored relative path every time. This is important because a directory can be replaced with a symlink or junction after approval; a changed path that now resolves outside the host ceiling must fail closed rather than inherit the old authorization.

## Tenant and audit contract

Grant repository reads/writes are scoped by `(tenant_id, id)`. A grant UUID from another tenant is not resolved. API create/update/disable operations are audited with relative root and policy metadata only; no provider credentials or absolute host paths are recorded.

## Process-enforcement boundary

`commands` and `network_policy` are intentionally **not** described as enforced by this control-plane slice. Before shell/coder execution can use a grant, the process sandbox must additionally enforce:

- grant expiry/enabled state and command membership;
- canonical working directory inside the grant root;
- argv execution with `shell=False`;
- sanitized environment;
- time/output/process/resource limits;
- cancellation and cleanup;
- real network isolation for `deny`, or a technically enforced allowlist for `allowlisted`;
- audit evidence without command-output secret leakage.

Until that executor boundary is merged and validated, durable grants are authorization records, not proof of process containment.
