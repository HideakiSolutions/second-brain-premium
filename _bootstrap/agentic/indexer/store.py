"""
store.py — clientes HTTP para Ollama (embeddings) e Qdrant (vector DB).

Stdlib-only (urllib + json) para evitar dependências externas.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import Any

OLLAMA_URL = "http://127.0.0.1:11434"
QDRANT_URL = "http://127.0.0.1:6333"
EMBED_MODEL = "bge-m3"
EMBED_DIM = 1024
COLLECTION = "secondbrain"


def _http_request(method: str, url: str, payload: dict | None = None, timeout: float = 60.0) -> dict:
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    headers = {"Content-Type": "application/json"} if data else {}
    req = urllib.request.Request(url, data=data, method=method, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP {e.code} on {url}: {body}") from e


# ---------- Ollama ----------

def embed(text: str, model: str = EMBED_MODEL) -> list[float]:
    """Gera embedding para um texto via Ollama."""
    res = _http_request("POST", f"{OLLAMA_URL}/api/embeddings",
                         {"model": model, "prompt": text})
    return res["embedding"]


def embed_batch(texts: list[str], model: str = EMBED_MODEL) -> list[list[float]]:
    """Gera embeddings em sequência (Ollama não suporta batch nativo no /api/embeddings)."""
    return [embed(t, model) for t in texts]


def ollama_ready() -> bool:
    try:
        _http_request("GET", f"{OLLAMA_URL}/api/tags", timeout=5)
        return True
    except (urllib.error.URLError, RuntimeError, OSError):
        return False


def ollama_has_model(model: str = EMBED_MODEL) -> bool:
    try:
        res = _http_request("GET", f"{OLLAMA_URL}/api/tags", timeout=5)
        names = [m.get("name", "") for m in res.get("models", [])]
        return any(model == n or n.startswith(model + ":") for n in names)
    except (urllib.error.URLError, RuntimeError, OSError):
        return False


# ---------- Qdrant ----------

def qdrant_ready() -> bool:
    try:
        _http_request("GET", f"{QDRANT_URL}/", timeout=5)
        return True
    except (urllib.error.URLError, RuntimeError, OSError):
        return False


def ensure_collection(dim: int = EMBED_DIM, name: str = COLLECTION) -> None:
    try:
        _http_request("GET", f"{QDRANT_URL}/collections/{name}", timeout=5)
        return
    except RuntimeError:
        pass
    payload = {
        "vectors": {"size": dim, "distance": "Cosine"},
        "optimizers_config": {"default_segment_number": 2},
    }
    _http_request("PUT", f"{QDRANT_URL}/collections/{name}", payload)


def upsert_points(points: list[dict], name: str = COLLECTION) -> None:
    """points: [{id, vector, payload}, ...]"""
    BATCH = 64
    for i in range(0, len(points), BATCH):
        batch = points[i : i + BATCH]
        _http_request("PUT", f"{QDRANT_URL}/collections/{name}/points?wait=true",
                       {"points": batch})


def delete_by_source(source_files: list[str], name: str = COLLECTION) -> int:
    """Apaga todos os pontos cujo payload.source_file está em source_files."""
    if not source_files:
        return 0
    res = _http_request("POST", f"{QDRANT_URL}/collections/{name}/points/delete?wait=true", {
        "filter": {"must": [{"key": "source_file", "match": {"any": source_files}}]}
    })
    return res.get("result", {}).get("operation_id", 0)


def search(query_vector: list[float], k: int = 10, filter_: dict | None = None,
           name: str = COLLECTION) -> list[dict]:
    payload: dict[str, Any] = {
        "vector": query_vector,
        "limit": k,
        "with_payload": True,
    }
    if filter_:
        payload["filter"] = filter_
    res = _http_request("POST", f"{QDRANT_URL}/collections/{name}/points/search", payload)
    return res.get("result", [])


def collection_stats(name: str = COLLECTION) -> dict:
    try:
        return _http_request("GET", f"{QDRANT_URL}/collections/{name}").get("result", {})
    except RuntimeError:
        return {}


def hash_to_uint64(hex_str: str) -> int:
    """Converte hex para uint64 (Qdrant aceita id como int ou UUID)."""
    return int(hex_str[:16], 16)
