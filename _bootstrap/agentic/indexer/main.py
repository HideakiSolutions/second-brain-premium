"""
main.py — entrypoint do indexer.

Subcomandos:
  reindex [--full | --paths <p1> <p2> ...]
  search <query> [--k 10] [--kind decisions] [--project meu-projeto]
  status
  delete --paths <p1> <p2> ...
"""

from __future__ import annotations

import argparse
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from chunker import Chunk, chunk_file, walk_vault  # type: ignore
from store import (  # type: ignore
    COLLECTION,
    EMBED_DIM,
    EMBED_MODEL,
    collection_stats,
    delete_by_source,
    embed,
    ensure_collection,
    hash_to_uint64,
    ollama_has_model,
    ollama_ready,
    qdrant_ready,
    search,
    upsert_points,
)

# VAULT_ROOT: env var (definida por sb-reindex.sh) com fallback para a raiz
# do vault inferida pela posição deste arquivo (_bootstrap/agentic/indexer/).
VAULT_ROOT = Path(os.environ.get("VAULT_ROOT", str(Path(__file__).resolve().parents[3])))


def _check_infra() -> bool:
    ok = True
    if not qdrant_ready():
        print("[indexer] Qdrant indisponível em http://127.0.0.1:6333", file=sys.stderr)
        ok = False
    if not ollama_ready():
        print("[indexer] Ollama indisponível em http://127.0.0.1:11434", file=sys.stderr)
        ok = False
    elif not ollama_has_model(EMBED_MODEL):
        print(f"[indexer] Modelo '{EMBED_MODEL}' não está em Ollama. Rode: bash _bootstrap/agentic/stack.sh setup", file=sys.stderr)
        ok = False
    return ok


def _chunk_to_point(c: Chunk) -> dict:
    payload = {
        "source_file": c.source_file,
        "heading_path": c.heading_path,
        "kind": c.kind,
        "project": c.project,
        "tags": c.tags,
        "wikilinks": c.wikilinks[:20],  # limita para não inchar
        "char_count": c.char_count,
        "text": c.text,
    }
    return {
        "id": hash_to_uint64(c.chunk_id),
        "vector": [],  # preenchido em batch logo após
        "payload": payload,
    }


def cmd_reindex(args: argparse.Namespace) -> int:
    if not _check_infra():
        return 1
    ensure_collection(EMBED_DIM, COLLECTION)

    if args.paths:
        files = [Path(p).resolve() for p in args.paths if Path(p).exists()]
    else:
        files = walk_vault(VAULT_ROOT)

    print(f"[indexer] {len(files)} arquivos para processar", file=sys.stderr)

    # Coleta chunks
    all_chunks: list[Chunk] = []
    for f in files:
        cs = chunk_file(f, VAULT_ROOT)
        all_chunks.extend(cs)
    print(f"[indexer] {len(all_chunks)} chunks gerados", file=sys.stderr)

    # Apaga pontos antigos dos arquivos a re-indexar (idempotência)
    sources = sorted({c.source_file for c in all_chunks})
    if sources and args.replace:
        delete_by_source(sources, COLLECTION)
        print(f"[indexer] {len(sources)} arquivos limpos no Qdrant", file=sys.stderr)

    # Gera embeddings + upsert em batches
    BATCH = 32
    total = 0
    t0 = time.monotonic()
    for i in range(0, len(all_chunks), BATCH):
        batch = all_chunks[i : i + BATCH]
        points: list[dict] = []
        for c in batch:
            try:
                vec = embed(c.text)
            except Exception as exc:
                print(f"[indexer] embed falhou em {c.source_file}: {exc}", file=sys.stderr)
                continue
            p = _chunk_to_point(c)
            p["vector"] = vec
            points.append(p)
        if points:
            upsert_points(points, COLLECTION)
            total += len(points)
        if i % (BATCH * 4) == 0:
            elapsed = time.monotonic() - t0
            rate = total / elapsed if elapsed > 0 else 0
            print(f"  [{i+len(batch)}/{len(all_chunks)}] {total} indexados · {rate:.1f}/s", file=sys.stderr)

    elapsed = time.monotonic() - t0
    print(f"[indexer] {total} chunks indexados em {elapsed:.1f}s ({total/max(elapsed,0.001):.1f}/s)", file=sys.stderr)
    return 0


def cmd_search(args: argparse.Namespace) -> int:
    if not _check_infra():
        return 1
    query = args.query
    qvec = embed(query)
    filter_: dict | None = None
    must: list[dict] = []
    if args.kind:
        must.append({"key": "kind", "match": {"value": args.kind}})
    if args.project:
        must.append({"key": "project", "match": {"value": args.project}})
    if must:
        filter_ = {"must": must}

    results = search(qvec, k=args.k, filter_=filter_)

    if args.json:
        import json
        print(json.dumps(results, indent=2, ensure_ascii=False))
        return 0

    if not results:
        print(f"[indexer] nenhum resultado para: {query}", file=sys.stderr)
        return 0

    print(f"\n## Top {len(results)} para: {query!r}\n")
    for i, r in enumerate(results, 1):
        score = r.get("score", 0)
        p = r.get("payload", {})
        snippet = (p.get("text") or "")[:200].replace("\n", " ")
        print(f"### [{i}] {p.get('source_file')} · {p.get('heading_path')}")
        print(f"    kind={p.get('kind')} project={p.get('project')} score={score:.3f}")
        print(f"    {snippet}…")
        print()
    return 0


def cmd_status(args: argparse.Namespace) -> int:
    if not qdrant_ready():
        print("[indexer] Qdrant: OFFLINE")
        return 1
    print("[indexer] Qdrant: online")
    if ollama_ready():
        has = ollama_has_model(EMBED_MODEL)
        print(f"[indexer] Ollama: online · modelo {EMBED_MODEL}: {'✓' if has else '✗ (rode: bash _bootstrap/agentic/stack.sh setup)'}")
    else:
        print("[indexer] Ollama: OFFLINE")
    stats = collection_stats(COLLECTION)
    if stats:
        print(f"[indexer] Collection '{COLLECTION}': {stats.get('points_count', 0)} pontos · "
              f"{stats.get('vectors_count', 0)} vetores · status={stats.get('status', '?')}")
    else:
        print(f"[indexer] Collection '{COLLECTION}' não existe (rode reindex)")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("reindex")
    p.add_argument("--paths", nargs="*", help="paths específicos; default = vault inteiro")
    p.add_argument("--replace", action="store_true", help="apaga pontos antigos antes de upsert")
    p.set_defaults(func=cmd_reindex)

    p = sub.add_parser("search")
    p.add_argument("query")
    p.add_argument("--k", type=int, default=10)
    p.add_argument("--kind", help="filtrar por kind (patterns|features|decisions|...)")
    p.add_argument("--project")
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=cmd_search)

    p = sub.add_parser("status")
    p.set_defaults(func=cmd_status)

    args = ap.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
