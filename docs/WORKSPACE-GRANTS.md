# Durable Workspace Grants

Workspace grants are tenant-scoped, operator-managed authorization records for local workspace roots. The configured `ZWORKFORCE_WORKSPACE_ROOT` remains the hard host-level ceiling; a grant can only select an existing directory **inside** that ceiling.

Grant enforcement is layered: file tools use the grant directly, while production shell/coder execution additionally requires the probed process sandbox documented in [PROCESS-SANDBOX.md](PROCESS-SANDBOX.md). A stored `network_policy` is never treated as proof of containment by itself.

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
- `write`: whether file-write or production process capabilities may use the grant.
- `commands`: generic shell executable names permitted by this grant. Names must also be in `ZWORKFORCE_SHELL_ALLOWLIST`.
- `network_policy`: `deny` or `allowlisted`. Production process execution currently supports only `deny`; `allowlisted` fails closed.
- `enabled`: false disables future use.
- `expires_at`: timezone-aware ISO-8601 timestamp. New API grants must expire in the future and within 365 days.
- creation/update actor and timestamps.

## File-tool enforcement

`workspace_list`, `workspace_read` and `workspace_write` expose an optional `workspace_id` parameter in their server-owned tool schemas.

In `production`, `workspace_id` is mandatory for these three local file tools. The runtime resolves the grant by authenticated task tenant, rejects disabled/expired/cross-tenant grants, checks the grant's read/write capability, and re-resolves the approved root for each invocation. The caller cannot supply an absolute host root.

In non-production environments, omission of `workspace_id` retains legacy use of the configured host workspace root for compatibility with existing development/test workflows. Supplying a grant uses the grant-aware path.

Host operators also have independent kill switches:

```text
ZWORKFORCE_WORKSPACE_READ_ENABLED=true|false
ZWORKFORCE_WORKSPACE_WRITE_ENABLED=true|false
```

Both default to `true` for backward compatibility. A grant cannot override a disabled host capability. Production therefore requires both the host capability to be enabled **and** an active tenant grant with the corresponding permission.

File paths are relative to the resolved grant root. Absolute paths and traversal outside that root fail closed. Reads use no-follow semantics where the operating system exposes them; writes remain bounded and atomic through a temporary file + replace within the validated parent directory.

`workspace_write` tool evidence never persists raw file content. It records grant ID, relative path, parent-creation flag and byte count only.

## Process-tool enforcement

`workspace_id` is also part of the server-owned schemas for `shell_exec` and `zworkforce_code_agent`.

In production both process tools require an enabled, unexpired, writable tenant grant. Generic `shell_exec` additionally requires:

- host `ZWORKFORCE_SHELL_ENABLED=true`;
- executable membership in the host shell allowlist;
- executable membership in the grant's `commands`.

The coding-agent tool uses a fixed trusted zWorkforce coder executable rather than expanding the generic shell allowlist. Its working directory must remain inside the grant root.

Production process execution then passes through the probed Bubblewrap + `prlimit` backend. `network_policy=deny` receives an isolated network namespace. `network_policy=allowlisted` is rejected until a technically enforced allowlisted-egress implementation exists.

If Bubblewrap/prlimit is missing or the deployed kernel/container policy prevents namespace creation, process execution fails closed. Installation of the sandbox packages alone is not treated as runtime evidence.

In non-production environments, process calls that omit `workspace_id` retain the pre-existing direct subprocess behavior and are explicitly not labeled sandboxed. Supplying a grant selects the grant-aware sandbox path.

Durable process tool-event metadata excludes shell argument values and coding-agent prompt bodies.

## Canonical-path safety

Grant creation resolves the requested path against the configured workspace root and requires an existing directory. Grant use re-resolves the stored relative path every time. This is important because a directory can be replaced with a symlink or junction after approval; a changed path that now resolves outside the host ceiling must fail closed rather than inherit the old authorization.

Filesystem containment is defense in depth, not a claim that path checks alone form a hostile-OS sandbox. Process isolation is provided separately by the probed process backend.

## Tenant and audit contract

Grant repository reads/writes are scoped by `(tenant_id, id)`. A grant UUID from another tenant is not resolved. API create/update/disable operations are audited with relative root and policy metadata only; no provider credentials or absolute host paths are recorded.
