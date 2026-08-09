from __future__ import annotations

import hashlib
import json
import math
import os
import re
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Protocol

TOKEN_RE = re.compile(r"[\w'-]+", re.UNICODE)


class RagError(RuntimeError):
    pass


def feature_hash_embedding(text: str, dimensions: int = 128) -> list[float]:
    dimensions = max(32, min(int(dimensions), 2048))
    vector = [0.0] * dimensions
    for token in TOKEN_RE.findall(text.lower()):
        digest = hashlib.blake2b(token.encode("utf-8"), digest_size=8).digest()
        value = int.from_bytes(digest, "big")
        index = value % dimensions
        sign = -1.0 if (value >> 63) else 1.0
        vector[index] += sign
    norm = math.sqrt(sum(x * x for x in vector)) or 1.0
    return [x / norm for x in vector]


def cosine(a: list[float], b: list[float]) -> float:
    if len(a) != len(b) or not a:
        return 0.0
    return sum(x * y for x, y in zip(a, b))


class Embedder(Protocol):
    def embed(self, text: str) -> list[float]: ...


class FeatureHashEmbedder:
    def __init__(self, dimensions: int = 128): self.dimensions = dimensions
    def embed(self, text: str) -> list[float]: return feature_hash_embedding(text, self.dimensions)


class OpenAICompatibleEmbedder:
    def __init__(self, base_url: str, api_key: str, model: str, dimensions: int = 0, timeout: int = 30):
        parsed = urllib.parse.urlsplit(base_url)
        if parsed.scheme not in {"https", "http"} or not parsed.hostname:
            raise RagError("embedding base URL must be HTTP(S)")
        if parsed.scheme == "http" and parsed.hostname not in {"localhost", "127.0.0.1", "::1"}:
            raise RagError("remote embedding endpoints must use HTTPS")
        self.base_url, self.api_key, self.model, self.dimensions, self.timeout = base_url.rstrip("/"), api_key, model, max(0, int(dimensions)), timeout

    def embed(self, text: str) -> list[float]:
        body: dict[str, Any] = {"model": self.model, "input": text}
        if self.dimensions:
            body["dimensions"] = self.dimensions
        headers = {"Content-Type": "application/json", "User-Agent": "zWorkforce-RAG/3"}
        if self.api_key:
            headers["Authorization"] = "Bearer " + self.api_key
        request = urllib.request.Request(self.base_url + "/embeddings", data=json.dumps(body, separators=(",", ":")).encode(), headers=headers, method="POST")
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                data = json.loads(response.read(4_194_304))
        except Exception as exc:
            raise RagError("embedding request failed") from exc
        try:
            vector = [float(x) for x in data["data"][0]["embedding"]]
        except (KeyError, IndexError, TypeError, ValueError) as exc:
            raise RagError("embedding response is invalid") from exc
        if not vector:
            raise RagError("embedding response is empty")
        return vector


class LocalSemanticMemory:
    """Dependency-free feature-hashing retriever for small/medium corpora."""

    def __init__(self, db, dimensions: int = 128, embedder: Embedder | None = None):
        self.db = db
        self.dimensions = dimensions
        self.embedder = embedder or FeatureHashEmbedder(dimensions)

    def index_memory(self, tenant_id: str, memory_id: str) -> None:
        memory = self.db.get_memory(tenant_id, memory_id)
        if not memory:
            raise ValueError("memory not found")
        text = _memory_text(memory)
        self.db.upsert_memory_vector(tenant_id, memory_id, memory.get("agent_id"), self.embedder.embed(text))

    def reindex(self, tenant_id: str, limit: int = 5000) -> dict[str, int]:
        items = self.db.list_memories(tenant_id, limit)
        for item in items:
            self.index_memory(tenant_id, item["id"])
        return {"indexed": len(items), "backend": "local"}

    def search(self, tenant_id: str, query: str, agent_id: str | None = None, limit: int = 10) -> list[dict[str, Any]]:
        q = self.embedder.embed(query)
        scored = []
        for item in self.db.list_memory_vectors(tenant_id, agent_id, 5000):
            vector = item.get("vector") or []
            score = cosine(q, [float(x) for x in vector])
            result = dict(item)
            result["score"] = round(score, 6)
            if len(result.get("content", "")) > 3000:
                result["content"] = result["content"][:3000] + "…"
            scored.append(result)
        scored.sort(key=lambda x: x["score"], reverse=True)
        return scored[:max(1, min(int(limit), 50))]


class QdrantVectorStore:
    def __init__(self, base_url: str, collection: str, api_key: str = "", timeout: int = 10):
        parsed = urllib.parse.urlsplit(base_url)
        if parsed.scheme not in {"https", "http"} or not parsed.hostname:
            raise RagError("Qdrant URL must be HTTP(S)")
        if parsed.scheme == "http" and parsed.hostname not in {"localhost", "127.0.0.1", "::1"}:
            raise RagError("remote Qdrant endpoints must use HTTPS")
        self.base_url = base_url.rstrip("/")
        self.collection = collection
        self.api_key = api_key
        self.timeout = timeout

    def _request(self, method: str, path: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        headers = {"Content-Type": "application/json", "User-Agent": "zWorkforce-RAG/3"}
        if self.api_key:
            headers["api-key"] = self.api_key
        request = urllib.request.Request(self.base_url + path, data=(json.dumps(payload, separators=(",", ":")).encode() if payload is not None else None), headers=headers, method=method)
        with urllib.request.urlopen(request, timeout=self.timeout) as response:
            raw = response.read(4_194_304)
        return json.loads(raw or b"{}")

    def ensure_collection(self, dimension: int) -> None:
        try:
            self._request("GET", f"/collections/{self.collection}")
            return
        except urllib.error.HTTPError as exc:
            if exc.code != 404:
                raise
        self._request("PUT", f"/collections/{self.collection}", {"vectors": {"size": int(dimension), "distance": "Cosine"}})

    def upsert(self, point_id: str, vector: list[float], payload: dict[str, Any]) -> dict[str, Any]:
        self.ensure_collection(len(vector))
        return self._request("PUT", f"/collections/{self.collection}/points?wait=true", {"points": [{"id": point_id, "vector": vector, "payload": payload}]})

    def search(self, vector: list[float], limit: int = 10, filter_: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        body: dict[str, Any] = {"vector": vector, "limit": max(1, min(int(limit), 100)), "with_payload": True}
        if filter_:
            body["filter"] = filter_
        data = self._request("POST", f"/collections/{self.collection}/points/search", body)
        return list(data.get("result") or [])


class QdrantSemanticMemory:
    def __init__(self, db, store: QdrantVectorStore, embedder: Embedder):
        self.db, self.store, self.embedder = db, store, embedder

    def index_memory(self, tenant_id: str, memory_id: str) -> None:
        memory = self.db.get_memory(tenant_id, memory_id)
        if not memory: raise ValueError("memory not found")
        vector = self.embedder.embed(_memory_text(memory))
        payload = {"memory_id": memory["id"], "tenant_id": tenant_id, "agent_id": memory.get("agent_id"), "title": memory.get("title", ""), "content": memory.get("content", ""), "tags": memory.get("tags") or []}
        self.store.upsert(memory_id, vector, payload)

    def reindex(self, tenant_id: str, limit: int = 5000) -> dict[str, int]:
        items = self.db.list_memories(tenant_id, limit)
        for item in items: self.index_memory(tenant_id, item["id"])
        return {"indexed": len(items), "backend": "qdrant"}

    def search(self, tenant_id: str, query: str, agent_id: str | None = None, limit: int = 10) -> list[dict[str, Any]]:
        vector = self.embedder.embed(query)
        filt = {"must": [{"key": "tenant_id", "match": {"value": tenant_id}}]}
        rows = self.store.search(vector, max(int(limit) * 3, int(limit)), filt)
        out=[]
        for row in rows:
            payload = dict(row.get("payload") or {})
            if agent_id and payload.get("agent_id") not in {None, "", agent_id}: continue
            payload["score"] = round(float(row.get("score") or 0), 6)
            out.append(payload)
            if len(out) >= max(1, min(int(limit), 50)): break
        return out


def build_semantic_memory(db):
    backend = os.getenv("ZWORKFORCE_VECTOR_BACKEND", "local").strip().lower()
    if backend == "local":
        dimensions = int(os.getenv("ZWORKFORCE_LOCAL_VECTOR_DIMENSIONS", "128"))
        return LocalSemanticMemory(db, dimensions)
    if backend == "qdrant":
        embedder = OpenAICompatibleEmbedder(
            os.getenv("ZWORKFORCE_EMBEDDING_BASE_URL", ""),
            os.getenv("ZWORKFORCE_EMBEDDING_API_KEY", ""),
            os.getenv("ZWORKFORCE_EMBEDDING_MODEL", ""),
            int(os.getenv("ZWORKFORCE_EMBEDDING_DIMENSIONS", "0")),
            int(os.getenv("ZWORKFORCE_EMBEDDING_TIMEOUT_SECONDS", "30")),
        )
        if not embedder.base_url or not embedder.model:
            raise RagError("Qdrant backend requires embedding base URL and model")
        store = QdrantVectorStore(os.getenv("ZWORKFORCE_QDRANT_URL", ""), os.getenv("ZWORKFORCE_QDRANT_COLLECTION", "zworkforce-memory"), os.getenv("ZWORKFORCE_QDRANT_API_KEY", ""))
        return QdrantSemanticMemory(db, store, embedder)
    raise RagError("ZWORKFORCE_VECTOR_BACKEND must be local or qdrant")


def _memory_text(memory: dict[str, Any]) -> str:
    return f"{memory.get('title','')}\n{memory.get('content','')}\n{' '.join(memory.get('tags') or [])}"
