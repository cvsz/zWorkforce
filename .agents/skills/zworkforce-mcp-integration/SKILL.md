---
name: zworkforce-mcp-integration
description: Configure and verify the zWorkforce MCP 2026-07-28 stateless endpoint and client, which exposes task, workflow, event, and memory management as MCP tools to external clients.
---

# zWorkforce MCP Integration

Expose control-plane capability to MCP clients without widening the trust
boundary.

## Workflow

1. Identify which task, workflow, event, or memory operations should be
   exposed as MCP tools for the target tenant and role.
2. Verify the stateless endpoint contract: no server-side session state is
   required between MCP calls, and tenant/actor identity is derived the same
   way as the REST API.
3. Confirm RBAC/scopes are enforced identically through MCP as through the
   REST control plane; an MCP client must never gain broader access than the
   same actor would have through the API.
4. Verify provider, storage, and database secrets never appear in MCP tool
   schemas, descriptions, or responses.
5. Exercise the client path end-to-end against a representative MCP client
   before declaring an integration ready.

## References

- `zworkforce/mcp.py`
- `docs/MCP.md`
- `docs/IDENTITY.md`
- `tests/test_v3_mcp.py`

## Output

Report exposed tools, scope/role enforcement evidence, secret-boundary
checks, and any gaps versus the REST control plane's authorization model.
