# zknowbase Integration

`zworkforce` consumes organizational knowledge from `cvsz/zknowbase` only through the native server-side API client in `zworkforce.zknowbase_client`. Agents never access Qdrant directly.

## Security boundary

- Keep every zknowbase credential server-side. Never expose it to browser/static code.
- Provision retrieval credentials with only `knowledge:read`. Administrative ingestion/key-management credentials are separate and are not used by agent retrieval tools.
- Tenant authorization remains authoritative in zknowbase: the tenant attached to the authenticated service key controls retrieval. zworkforce execution-context headers are consistency/audit metadata and cannot select or override another tenant.
- Agent retrieval runs through the normal `ToolExecutor` grant path as the read-only `knowledge_search` or `knowledge_ask` tool. An agent that is not granted one of these tools cannot invoke it through the runtime.
- Returned citations/results are checked by the consumer for the expected tenant as an additional fail-closed boundary.

## Environment

### Single-tenant credential

```bash
export ZWORKFORCE_ZKNOWBASE_URL=http://127.0.0.1:8000
export ZWORKFORCE_ZKNOWBASE_API_KEY='<knowledge-read-service-key>'
export ZWORKFORCE_ZKNOWBASE_TENANT_ID=default
export ZWORKFORCE_ZKNOWBASE_TIMEOUT_SECONDS=30
```

The single service key is bound to `ZWORKFORCE_ZKNOWBASE_TENANT_ID`. A runtime request for another tenant fails before the HTTP request is sent.

### Multi-tenant credential map

For a self-hosted multi-tenant workforce process, provide a dedicated read-only key per tenant through the process secret boundary:

```bash
export ZWORKFORCE_ZKNOWBASE_URL=http://zknowbase:8000
export ZWORKFORCE_ZKNOWBASE_TENANT_KEYS_JSON='{"tenant-a":"<knowledge-read-key-a>","tenant-b":"<knowledge-read-key-b>"}'
```

Do not put this JSON in browser bundles, public configuration, logs, task payloads, prompts, or source control. Missing tenant credentials fail closed.

`ZKnowbaseConfig.from_env()` returns `None` only when the entire integration is absent. Partial or contradictory configuration raises an error.

## Governed agent tools

`knowledge_search` and `knowledge_ask` are non-mutating tools in the normal agent tool registry. They therefore inherit zworkforce agent/skill grants, task lifecycle, tool-event recording, cancellation, bounded iterations, and runtime safety hooks rather than creating a side channel around governance.

The client sends versioned execution metadata for governed calls:

- `X-ZWorkforce-Context-Version: 1`
- `X-ZWorkforce-Tenant-ID`
- `X-ZWorkforce-Actor-ID`
- `X-ZWorkforce-Agent-ID`
- `X-ZWorkforce-Tool-ID`
- `X-ZWorkforce-Policy-Context`
- `X-ZWorkforce-Request-ID`
- `X-ZWorkforce-Trace-ID`
- matching `X-Request-ID`

zknowbase validates the context when the version marker is present. A tenant mismatch with the authenticated service principal is denied and audited. Malformed, incomplete, oversized, or request-ID-inconsistent context fails closed.

When the current ToolExecutor caller does not supply a request ID, the client creates a bounded random request ID and uses it as the trace ID. Callers that have a stronger task/tool-call correlation ID should provide it so that request and trace evidence can be correlated end-to-end.

## Direct server-side client compatibility

The lower-level client remains available for trusted server integrations:

```python
from zworkforce.zknowbase_client import ZKnowbaseClient, ZKnowbaseConfig

config = ZKnowbaseConfig.from_env()
if config is not None:
    knowledge = ZKnowbaseClient(config)
    result = knowledge.ask("What is the annual leave approval policy?", top_k=5)
```

These unmarked calls preserve backward compatibility, but agent execution should use the governed tools rather than calling the client directly.

## Failure semantics

Network failures, bounded HTTP errors, invalid/non-object JSON, unavailable tenant credentials, out-of-range `top_k`, invalid execution context, and cross-tenant response payloads are normalized as `ZKnowbaseError`/`ToolError`. For policy or HR decisions, callers must not fabricate authoritative organizational knowledge when retrieval fails; surface the unavailable state or use an explicitly approved fallback.

## Service contract

The native client uses only the zknowbase REST boundary:

- `POST /api/v1/query` for grounded answers with citations.
- `POST /api/v1/search` for retrieval-only contexts.
- `GET /api/v1/health` for service health.
- `X-API-Key` for server-side service authentication.

The module uses Python's standard-library HTTP client, so this integration adds no mandatory production dependency and no recurring API cost.
