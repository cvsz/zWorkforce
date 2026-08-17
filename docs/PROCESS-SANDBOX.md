# Production Process Sandbox

zWorkforce production process tools are isolated from normal host execution through a probed Linux Bubblewrap backend. This boundary applies to `shell_exec` and `zworkforce_code_agent` when they are invoked with a tenant workspace grant.

## Authorization prerequisites

Production process execution requires all of the following:

1. a tenant-scoped `workspace_id` grant;
2. the grant is enabled and unexpired;
3. the grant has `write=true` because process tools can mutate workspace state;
4. `network_policy=deny`;
5. for `shell_exec`, `ZWORKFORCE_SHELL_ENABLED=true`, the executable is in the host `ZWORKFORCE_SHELL_ALLOWLIST`, and it is also listed in the grant's `commands`;
6. the Bubblewrap + `prlimit` backend probe succeeds at runtime.

`zworkforce_code_agent` uses a fixed trusted zWorkforce coder executable and therefore does not expand the generic shell command allowlist. It still requires a writable grant and the same process sandbox.

## Runtime probe

Installing `bwrap` is not treated as proof that namespaces are usable. At first sandbox use, zWorkforce launches a minimal bounded Bubblewrap command with the same namespace/resource-control primitives used for real runs. The result is cached for the executor lifetime.

If the binary is missing, `prlimit` is missing, namespace creation is prohibited by the host/container/kernel policy, or the probe otherwise fails, production process execution fails closed with an explicit backend-unavailable error.

This is important for containerized deployments where an unprivileged container can have Bubblewrap installed but still be denied user-namespace creation by the outer runtime or kernel policy.

## Sandbox construction

For `network_policy=deny`, the command uses:

- `bubblewrap --unshare-all` and does **not** share the host network namespace;
- a new session and parent-death handling;
- cleared environment with a small server-controlled environment;
- all capabilities dropped;
- read-only runtime mounts for `/usr`, `/usr/local` when present, and small selected `/etc` compatibility files;
- isolated `/proc`, `/dev`, `/tmp`, `/run`, and sandbox home;
- exactly one writable host bind for the approved grant root at `/workspace`;
- working directory constrained under `/workspace`;
- `shell=False` argv execution.

The outer `prlimit` launcher applies hard CPU, address-space, process-count, open-file, and file-size ceilings before Bubblewrap starts. The normal zWorkforce wall-clock timeout and output-byte limits also remain in force.

## Credential boundary

The sandbox does not inherit the host process environment. In particular it does not forward provider API keys, GitHub tokens, service credentials, the operator's host `HOME`, or arbitrary environment variables.

A coding engine that needs external authenticated services must use an explicitly designed server-side broker/provider boundary or another scoped credential mechanism; credentials are not injected into the sandbox merely to preserve legacy behavior. Under the currently supported `network_policy=deny`, the sandbox also has no normal external network path.

## Network policy

Only `network_policy=deny` is currently executable. A grant declaring `network_policy=allowlisted` fails closed.

A domain or hostname list in application configuration is not considered OS-level process network isolation. `allowlisted` must not be enabled until a technically enforced egress boundary exists and has tests/evidence for DNS/IP changes, redirects, IPv4/IPv6, proxy bypass, and direct-address connections.

## Development compatibility

In non-production environments only, process calls that omit `workspace_id` continue through the pre-existing direct subprocess path. This preserves existing development and test workflows and is explicitly **not** labeled sandboxed.

If a workspace grant is supplied, the grant-aware process path is selected instead.

## Evidence minimization

Durable process tool events do not store shell argument values or coder prompt bodies:

- `shell_exec`: workspace grant ID, executable name, argument count;
- `zworkforce_code_agent`: workspace grant ID, relative cwd, prompt byte count.

Process stdout/stderr remain bounded return values for the active execution but are not copied into tool-event argument metadata by this boundary.

## Deployment evidence

CI verifies command construction, fail-closed behavior, authorization, data minimization, and the production image contents. Actual production readiness still requires environment evidence that the sandbox probe succeeds under the deployed container/runtime/kernel configuration. A successful CI container build is not a substitute for that external runtime probe.
