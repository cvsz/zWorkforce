# zknowbase Integration

`zworkforce` consumes organizational knowledge from `cvsz/zknowbase` only through the native server-side client in `zworkforce.zknowbase_client`. Agents and tools must never access Qdrant, zknowbase SQLite/Postgres storage, or zknowbase service credentials directly.

## Security and governance boundary

- Keep the zknowbase credential server-side. Never expose it to browser/static code.
- Provision a dedicated zknowbase service key with only `knowledge:read` for workforce retrieval.
- Use a separate privileged key only for administrative ingestion workflows.
- Configure the URL and key together; partial configuration fails during client configuration.
- Every `ask()` and `search()` call requires a `ZKnowbaseExecutionContext` created from the already-authorized zworkforce execution path.
- The service key remains authoritative for tenant authorization. The declared tenant is additional governance evidence and zknowbase rejects a mismatch.
- Do not manufacture governance fields merely to satisfy the client. Bind them to the real actor, agent, tool, policy evaluation, request, and trace that authorized the retrieval.

## Environment

```bash
export ZWORKFORCE_ZKNOWBASE_URL=http://127.0.0.1:8000
export ZWORKFORCE_ZKNOWBASE_API_KEY='<knowledge:read-service-key>'
export ZWORKFORCE_ZKNOWBASE_TIMEOUT_SECONDS=30
```

`ZKnowbaseConfig.from_env()` returns `None` when both URL and key are absent, so the integration remains optional for deployments that do not run zknowbase.

## Governed retrieval

```python
from zworkforce.zknowbase_client import (
    ZKnowbaseClient,
    ZKnowbaseConfig,
    ZKnowbaseExecutionContext,
)

config = ZKnowbaseConfig.from_env()
if config is not None:
    knowledge = ZKnowbaseClient(config)
    context = ZKnowbaseExecutionContext(
        tenant_id=execution.tenant_id,
        actor_id=execution.actor_id,
        agent_id=execution.agent_id,
        tool_id="knowledge.query",
        policy_context=execution.policy_evaluation_id,
        request_id=execution.request_id,
        trace_id=execution.trace_id,
    )
    result = knowledge.ask(
        "What is the annual leave approval policy?",
        context=context,
        top_k=5,
    )
```

For retrieval-only search, use the same authorized execution identity and identify the concrete tool invocation:

```python
search_context = ZKnowbaseExecutionContext(
    tenant_id=execution.tenant_id,
    actor_id=execution.actor_id,
    agent_id=execution.agent_id,
    tool_id="knowledge.search",
    policy_context=execution.policy_evaluation_id,
    request_id=execution.request_id,
    trace_id=execution.trace_id,
)
results = knowledge.search(
    "expense reimbursement workflow",
    context=search_context,
    top_k=8,
)
```

The identifiers above are illustrative field mappings; callers must source them from the repository's actual governed execution object rather than creating a parallel authorization mechanism.

## Wire contract

For governed reads the client sends:

- `X-API-Key`: least-privilege zknowbase service credential.
- `X-Request-ID`: execution request ID.
- `X-ZWorkforce-Context-Version: 1`.
- `X-ZWorkforce-Tenant-ID`.
- `X-ZWorkforce-Actor-ID`.
- `X-ZWorkforce-Agent-ID`.
- `X-ZWorkforce-Tool-ID`.
- `X-ZWorkforce-Policy-Context`.
- `X-ZWorkforce-Request-ID`.
- `X-ZWorkforce-Trace-ID`.

All governed-context values are non-empty, bounded to 256 characters, and reject control characters before a network request is issued. zknowbase additionally verifies that the tenant matches the authenticated service principal and that the governed request ID matches `X-Request-ID`.

`GET /api/v1/health` deliberately does not require or send governed retrieval context because it is service-health probing rather than knowledge access.

## Failure semantics

Network failures, HTTP errors, and invalid/non-object JSON are normalized as `ZKnowbaseError`. Invalid local execution context raises `ValueError` before sending credentials or data. Callers must fail closed for policy/HR decisions: if authoritative knowledge cannot be retrieved, do not fabricate organizational policy; surface the unavailable state or route the task to an approved fallback.

The module intentionally uses Python's standard-library HTTP client so the core `zworkforce` runtime does not gain a production dependency solely for this integration.
