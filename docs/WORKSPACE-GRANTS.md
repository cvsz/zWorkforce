# Durable Workspace Grants

Workspace grants are tenant-scoped, operator-managed authorization records for local workspace roots. The configured `ZWORKFORCE_WORKSPACE_ROOT` remains the hard host-level ceiling; a grant can only select an existing directory **inside** that ceiling.

File-tool enforcement is now a separate layer over this control plane. Process/network isolation for shell/coder execution is still a later boundary: a stored `network_policy` is not proof of an enforced process network sandbox.

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

## File-tool enforcement

`workspace_list`, `workspace_read` and `workspace_write` expose an optional `workspace_id` parameter in their server-owned tool schemas.

In `production`, `workspace_id` is mandatory for these three local file tools. The runtime resolves the grant by authenticated task tenant, rejects disabled/expired/cross-tenant grants, checks the grant's read/write capability, and re-resolves the approved root for each invocation. The caller cannot supply an absolute host root.

In non-production environments, omission of `workspace_id` retains legacy use of the configured host workspace root for compatibility with existing development/test workflows. Supplying a grant uses the same grant checks as production.

Host operators also have independent kill switches:

```text
ZWORKFORCE_WORKSPACE_READ_ENABLED=true|false
ZWORKFORCE_WORKSPACE_WRITE_ENABLED=true|false
```

Both default to `true` for backward compatibility. A grant cannot override a disabled host capability. Production therefore requires both the host capability to be enabled **and** an active tenant grant with the corresponding permission.

File paths are relative to the resolved grant root. Absolute paths and traversal outside that root fail closed. Reads use no-follow semantics where the operating system exposes them; writes remain bounded and atomic through a temporary file + replace within the validated parent directory.

`workspace_write` tool evidence never persists raw file content. It records grant ID, relative path, parent-creation flag and byte count only.

## Canonical-path safety

Grant creation resolves the requested path against the configured workspace root and requires an existing directory. Grant use re-resolves the stored relative path every time. This is important because a directory can be replaced with a symlink or junction after approval; a changed path that now resolves outside the host ceiling must fail closed rather than inherit the old authorization.

Filesystem containment is defense in depth, not a claim of a hostile-OS filesystem sandbox. Process isolation and stronger platform-specific containment are handled by the later process-executor boundary.

## Tenant and audit contract

Grant repository reads/writes are scoped by `(tenant_id, id)`. A grant UUID from another tenant is not resolved. API create/update/disable operations are audited with relative root and policy metadata only; no provider credentials or absolute host paths are recorded.

## Process-enforcement boundary

`commands` and `network_policy` are intentionally **not** described as enforced for shell/coder execution yet. Before process execution can use a grant, the process sandbox must additionally enforce:

- grant expiry/enabled state and command membership;
- canonical working directory inside the grant root;
- argv execution with `shell=False`;
- sanitized environment;
- time/output/process/resource limits;
- cancellation and cleanup;
- real network isolation for `deny`, or a technically enforced allowlist for `allowlisted`;
- audit evidence without command-output secret leakage.

Until that executor boundary is merged and validated, durable grants provide file-tool authorization and declared process policy, but not proof of shell/coder process containment.
