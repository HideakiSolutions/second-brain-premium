#!/usr/bin/env python3
"""
run_benchmark.py — roda queries-gabarito contra a collection Qdrant
e mede recall@5 (retorno top-5 contém pelo menos 1 dos arquivos esperados).

Uso:
  python3 run_benchmark.py [--k 5]
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "indexer"))
from store import embed, search  # type: ignore


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--k", type=int, default=5)
    ap.add_argument("--bench", default=str(Path(__file__).parent / "benchmark.jsonl"))
    args = ap.parse_args()

    bench_path = Path(args.bench)
    if not bench_path.exists():
        print(f"benchmark not found: {bench_path}", file=sys.stderr)
        return 1

    cases = [json.loads(line) for line in bench_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    hits = 0
    total = len(cases)
    latencies: list[float] = []

    print(f"# Benchmark — {total} queries · k={args.k}\n")

    for case in cases:
        query = case["query"]
        expected = case.get("expect_files_any", [])

        t0 = time.monotonic()
        qvec = embed(query)
        results = search(qvec, k=args.k)
        latency_ms = (time.monotonic() - t0) * 1000
        latencies.append(latency_ms)

        retrieved_files = [r.get("payload", {}).get("source_file", "") for r in results]
        retrieved_stems = {Path(f).stem for f in retrieved_files}

        hit = any(any(exp in stem or stem in exp for stem in retrieved_stems) for exp in expected)
        status = "✓" if hit else "✗"
        if hit:
            hits += 1

        top_file = retrieved_files[0] if retrieved_files else "—"
        top_score = results[0].get("score", 0) if results else 0
        print(f"{status} [{latency_ms:5.0f}ms] {query[:50]:50s} → {top_file} (score {top_score:.3f})")

    avg_latency = sum(latencies) / len(latencies) if latencies else 0
    p95 = sorted(latencies)[int(len(latencies) * 0.95)] if len(latencies) >= 5 else max(latencies, default=0)
    recall = hits / total * 100 if total else 0

    print("\n## Resumo")
    print(f"- recall@{args.k}: {hits}/{total} ({recall:.1f}%)")
    print(f"- latência média: {avg_latency:.0f}ms")
    print(f"- latência p95: {p95:.0f}ms")
    return 0


if __name__ == "__main__":
    sys.exit(main())
