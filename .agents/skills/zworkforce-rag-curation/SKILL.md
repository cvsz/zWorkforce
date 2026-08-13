---
name: zworkforce-rag-curation
description: Curate zWorkforce tenant-scoped memory and RAG behavior including memory records, tags, embeddings, local/Qdrant vector backends, reindexing, stale knowledge cleanup, privacy boundaries, and retrieval quality.
---

# zWorkforce RAG Curation

Keep tenant knowledge useful without crossing privacy or retention boundaries.

## Workflow

1. Identify tenant, agent scope, memory namespace, tags, source artifacts, and
   retention policy.
2. Remove stale, duplicate, or ungrounded memories only with the correct curator
   authority and audit trail.
3. Validate local feature-hash vectors or Qdrant/OpenAI-compatible embedding
   configuration.
4. Reindex after schema, embedding, source, or tag changes.
5. Test retrieval quality with representative queries and cite source records.

## References

- `docs/SECRET-MANAGEMENT.md`
- `zworkforce/rag.py`
- `zworkforce/db_tasks.py`
- `tests/test_v3_rag_artifacts.py`
- `README.md` Memory / RAG section

## Output

Report memory scope, changes made, sources, reindex status, retrieval checks,
privacy risk, and follow-up curation tasks.
