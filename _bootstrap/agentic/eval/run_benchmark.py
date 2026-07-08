#!/usr/bin/env python3
"""
run_benchmark.py — roda queries-gabarito e mede recall@K (top-K contém pelo
menos 1 dos arquivos esperados) por motor de retrieval.

Motores:
  search — busca vetorial pura (Qdrant top-K)
  recall — recall associativo da camada sináptica (sementes + spreading activation)
  both   — roda os dois e compara lado a lado (default)

Uso:
  python3 run_benchmark.py [--k 5] [--engine search|recall|both]
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

AGENTIC = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(AGENTIC / "indexer"))
sys.path.insert(0, str(AGENTIC / "synapse"))
from store import embed, search  # type: ignore  # noqa: E402


def run_search(query: str, k: int) -> list[str]:
    qvec = embed(query)
    results = search(qvec, k=k)
    return [r.get("payload", {}).get("source_file", "") for r in results]


def run_recall(query: str, k: int) -> list[str]:
    import recall as recall_mod  # type: ignore  # noqa: PLC0415
    out = recall_mod.recall(query=query, k=k, log=False)
    return [r["path"] for r in out.get("results", [])]


ENGINES = {"search": run_search, "recall": run_recall}


def run_engine(name: str, cases: list[dict], k: int) -> dict:
    fn = ENGINES[name]
    hits = 0
    latencies: list[float] = []
    rows: list[str] = []
    for case in cases:
        query = case["query"]
        expected = case.get("expect_files_any", [])
        t0 = time.monotonic()
        try:
            retrieved = fn(query, k)
        except Exception as exc:
            rows.append(f"! [ erro ] {query[:50]:50s} → {exc}")
            latencies.append(0.0)
            continue
        latency_ms = (time.monotonic() - t0) * 1000
        latencies.append(latency_ms)

        stems = {Path(f).stem for f in retrieved}
        hit = any(any(exp in stem or stem in exp for stem in stems) for exp in expected)
        if hit:
            hits += 1
        top = retrieved[0] if retrieved else "—"
        rows.append(f"{'✓' if hit else '✗'} [{latency_ms:5.0f}ms] {query[:50]:50s} → {top}")

    total = len(cases)
    avg = sum(latencies) / len(latencies) if latencies else 0
    p95 = sorted(latencies)[int(len(latencies) * 0.95)] if len(latencies) >= 5 else max(latencies, default=0)
    return {"engine": name, "hits": hits, "total": total,
            "recall_pct": hits / total * 100 if total else 0,
            "avg_ms": avg, "p95_ms": p95, "rows": rows}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--k", type=int, default=5)
    ap.add_argument("--engine", choices=["search", "recall", "both"], default="both")
    ap.add_argument("--bench", default=str(Path(__file__).parent / "benchmark.jsonl"))
    args = ap.parse_args()

    bench_path = Path(args.bench)
    if not bench_path.exists():
        print(f"benchmark not found: {bench_path}", file=sys.stderr)
        return 1

    cases = [json.loads(line) for line in bench_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    engines = ["search", "recall"] if args.engine == "both" else [args.engine]

    print(f"# Benchmark — {len(cases)} queries · k={args.k} · engines: {', '.join(engines)}\n")

    summaries = []
    for name in engines:
        print(f"## engine: {name}\n")
        summary = run_engine(name, cases, args.k)
        summaries.append(summary)
        for row in summary["rows"]:
            print(row)
        print(f"\n- recall@{args.k}: {summary['hits']}/{summary['total']} ({summary['recall_pct']:.1f}%)")
        print(f"- latência média: {summary['avg_ms']:.0f}ms · p95: {summary['p95_ms']:.0f}ms\n")

    if len(summaries) == 2:
        s, r = summaries
        print("## Comparativo")
        print(f"| Engine | recall@{args.k} | média | p95 |")
        print("|---|---|---|---|")
        for x in (s, r):
            print(f"| {x['engine']} | {x['hits']}/{x['total']} ({x['recall_pct']:.1f}%) | {x['avg_ms']:.0f}ms | {x['p95_ms']:.0f}ms |")
        delta = r["recall_pct"] - s["recall_pct"]
        print(f"\ndelta recall (recall - search): {delta:+.1f} pontos percentuais")
    return 0


if __name__ == "__main__":
    sys.exit(main())
