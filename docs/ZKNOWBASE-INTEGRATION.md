# zknowbase Integration

`zworkforce` can consume organizational knowledge from `cvsz/zknowbase` through the native server-side client in `zworkforce.zknowbase_client`.

## Security boundary

- Keep the zknowbase credential server-side. Never expose it to browser/static code.
- Provision a dedicated zknowbase service key with only `knowledge:read` for normal workforce retrieval.
- Use a separate privileged key only for administrative ingestion workflows.
- Configure the URL and key together; partial configuration fails during client configuration.

## Environment

```bash
export ZWORKFORCE_ZKNOWBASE_URL=http://127.0.0.1:8000
export ZWORKFORCE_ZKNOWBASE_API_KEY='<read-only-service-key>'
export ZWORKFORCE_ZKNOWBASE_TIMEOUT_SECONDS=30
```

`ZKnowbaseConfig.from_env()` returns `None` when both URL and key are absent, so the integration remains optional for deployments that do not run zknowbase.

## Query company knowledge

```python
from zworkforce.zknowbase_client import ZKnowbaseClient, ZKnowbaseConfig

config = ZKnowbaseConfig.from_env()
if config is not None:
    knowledge = ZKnowbaseClient(config)
    result = knowledge.ask("What is the annual leave approval policy?", top_k=5)
    print(result["answer"])
    for source in result.get("sources", []):
        print(source.get("document_name"), source.get("score"))
```

## Retrieval-only search

```python
results = knowledge.search("expense reimbursement workflow", top_k=8)
for item in results.get("results", []):
    print(item["text"], item["score"])
```

## Failure semantics

Network failures, HTTP errors, and invalid/non-object JSON are normalized as `ZKnowbaseError`. Callers should fail closed for policy/HR decisions: if authoritative knowledge cannot be retrieved, do not fabricate an organizational policy. Surface the unavailable state or route the task to a human/approved fallback.

## Contract

The native client uses the zknowbase REST boundary:

- `POST /api/v1/query` for grounded answers with citations.
- `POST /api/v1/search` for retrieval-only contexts.
- `GET /api/v1/health` for service health.
- `X-API-Key` for service authentication.

The module intentionally uses Python's standard library HTTP client so the core `zworkforce` runtime does not gain a new production dependency solely for this integration.
