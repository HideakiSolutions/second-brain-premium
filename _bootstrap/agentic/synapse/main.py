"""
main.py — CLI da camada sináptica.

Subcomandos:
  build                                  reconstrói nós + arestas a partir do vault
  status                                 estatísticas do grafo sináptico
  recall <query> [--k 8] [--hops 2] [--kind K] [--project P] [--json] [--brief]
  recall --seed <slug> [...]             expansão associativa a partir de uma nota
  explain <slug-a> <slug-b>              caminho sináptico mais forte entre duas memórias
  activate --paths p1 p2 --source read|write|search|session [--session S]
  reinforce [--session S | --window 240] reforço hebbiano do conjunto co-ativado
  decay [--half-life 90]                 decaimento + poda de sinapses aprendidas
  sync-falkor [--full]                   projeta o grafo no FalkorDB (incremental | reconciliacao)
  consolidate [--keep 10] [--no-dedup] [--no-falkor]   ciclo de "sono" completo

Projecao FalkorDB e near-online: build/reinforce/decay disparam sync incremental
automatico (desative com SB_SYNAPSE_AUTOSYNC=0); consolidate reconcilia full.

Fail-soft: recall por query exige a stack semantica online (Qdrant + Ollama) e
retorna erro acionável quando offline; todos os demais comandos são 100% locais.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import db  # noqa: E402


def _autosync_report() -> None:
    import falkor_sync  # noqa: PLC0415
    out = falkor_sync.autosync()
    if out is None:
        return
    if out.get("skipped"):
        print(f"[synapse] projecao falkor: {out['skipped']} (recupera no proximo sync)")
    else:
        print(f"[synapse] projecao falkor ({out['mode']}): +{out['nodes']} nos, "
              f"+{out['edges']} arestas, -{out['tombstones']} removidas")


def cmd_build(_: argparse.Namespace) -> int:
    import extract  # noqa: PLC0415
    conn = db.connect()
    result = extract.build(conn)
    conn.close()
    print(f"[synapse] build: {result['nodes']} nos, {result['edges']} arestas "
          f"({result['edges_file']} derivadas de arquivo) a partir de {result['files']} arquivos")
    _autosync_report()
    return 0


def cmd_status(args: argparse.Namespace) -> int:
    conn = db.connect()
    s = db.stats(conn)
    conn.close()
    if args.json:
        print(json.dumps(s, ensure_ascii=False, indent=2))
        return 0
    print(f"[synapse] nos={s['nodes']} arestas={s['edges']} (aprendidas={s['learned_edges']}) "
          f"ativacoes={s['activations']} coativacoes-pendentes={s['coactivations_pending']}")
    print(f"[synapse] por tipo: {s['edges_by_kind']}")
    print(f"[synapse] last_build={s['last_build']} last_decay={s['last_decay']} "
          f"last_consolidate={s['last_consolidate']}")
    return 0


def cmd_recall(args: argparse.Namespace) -> int:
    import recall as recall_mod  # noqa: PLC0415
    try:
        out = recall_mod.recall(
            query=args.query, seed_slug=args.seed, k=args.k, hops=args.hops,
            kind=args.kind, project=args.project, session=args.session,
            log=not args.no_log,
        )
    except RuntimeError as exc:
        print(f"[synapse] recall indisponivel: {exc}", file=sys.stderr)
        print("[synapse] suba a stack: bash _bootstrap/agentic/stack.sh start", file=sys.stderr)
        return 2
    if "error" in out:
        print(f"[synapse] {out['error']}", file=sys.stderr)
        return 1
    if args.json:
        print(json.dumps(out, ensure_ascii=False, indent=2))
        return 0
    results = out.get("results", [])
    if not results:
        print("[synapse] nenhuma memoria encontrada")
        return 0
    if args.brief:
        for r in results:
            print(f"- {r['path']} · {r['title']} (score {r['score']})")
        return 0
    label = out.get("query") or f"seed:{out.get('seed')}"
    print(f"\n## Recall associativo — {label!r} ({out['mode']}, {out['hops']} hops)\n")
    for i, r in enumerate(results, 1):
        seed_mark = " [semente]" if r.get("seed") else ""
        print(f"### [{i}] {r['title']}{seed_mark}")
        print(f"    {r['path']} · kind={r['kind']} project={r['project'] or '-'}")
        print(f"    score={r['score']} (semantico={r['semantic']} ativacao={r['activation']} "
              f"forca={r['strength']})")
        chain = r.get("chain") or []
        if len(chain) > 1:
            print(f"    cadeia: {' → '.join(chain)}")
        print()
    hops = out.get("next_hops") or []
    if hops:
        print("## Proximos saltos sugeridos\n")
        for h in hops:
            print(f"- {h['title']} ({h['path']}) — a partir de {h['from']} (peso {h['weight']})")
    return 0


def cmd_explain(args: argparse.Namespace) -> int:
    import recall as recall_mod  # noqa: PLC0415
    out = recall_mod.explain(args.a, args.b, max_hops=args.max_hops)
    if args.json:
        print(json.dumps(out, ensure_ascii=False, indent=2))
        return 0
    if out.get("error"):
        print(f"[synapse] {out['error']}", file=sys.stderr)
        return 1
    if not out.get("path"):
        print(f"[synapse] {out.get('note', 'sem caminho')}")
        return 0
    print(f"\n## Caminho sinaptico: {args.a} → {args.b} "
          f"({out['hops']} hops, forca {out['strength']})\n")
    for i, step in enumerate(out["path"]):
        prefix = "  " * i + ("└─ " if i else "")
        via = f" ← via {step['via']} (peso {step.get('weight')})" if i else ""
        print(f"{prefix}{step['title']} ({step['path']}){via}")
    return 0


def cmd_activate(args: argparse.Namespace) -> int:
    import physiology  # noqa: PLC0415
    n = physiology.activate(args.paths, args.source, session=args.session)
    print(f"[synapse] {n} ativacao(oes) registrada(s) ({args.source})")
    return 0


def cmd_reinforce(args: argparse.Namespace) -> int:
    import physiology  # noqa: PLC0415
    out = physiology.reinforce(session=args.session, window_minutes=args.window)
    print(f"[synapse] reforco: {out['nodes']} nos co-ativados, "
          f"{out['strengthened']} sinapses fortalecidas, {out['learned_created']} aprendidas")
    if out["strengthened"] or out["learned_created"]:
        _autosync_report()
    return 0


def cmd_decay(args: argparse.Namespace) -> int:
    import physiology  # noqa: PLC0415
    out = physiology.decay(half_life_days=args.half_life)
    print(f"[synapse] decay: fator {out['factor']} em {out['elapsed_days']}d, "
          f"{out['pruned_learned']} aprendidas podadas, "
          f"{out['stale_coactivations']} coativacoes velhas limpas")
    _autosync_report()
    return 0


def cmd_sync_falkor(args: argparse.Namespace) -> int:
    import falkor_sync  # noqa: PLC0415
    out = falkor_sync.sync(full=args.full)
    if out.get("skipped"):
        print(f"[synapse] sync-falkor: {out['skipped']}")
        return 2
    print(f"[synapse] sync-falkor ({out['mode']}): {out['nodes']} nos, "
          f"{out['edges']} arestas, {out['tombstones']} tombstones processados")
    return 0


def cmd_consolidate(args: argparse.Namespace) -> int:
    import consolidate  # noqa: PLC0415
    out = consolidate.run(keep=args.keep, dedup=not args.no_dedup, falkor=not args.no_falkor)
    compact = out.get("compact", {})
    print("[synapse] consolidacao concluida — relatorio em _memory/synapse-report.md")
    print(f"[synapse] compact: {compact}")
    print(f"[synapse] duplicatas propostas: {len(out.get('duplicates', []))} · "
          f"sugestoes de link: {len(out.get('link_suggestions', []))}")
    print(f"[synapse] falkor: {out.get('falkor', {})}")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(prog="synapse")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("build")
    p.set_defaults(func=cmd_build)

    p = sub.add_parser("status")
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=cmd_status)

    p = sub.add_parser("recall")
    p.add_argument("query", nargs="?", default=None)
    p.add_argument("--seed", help="slug/path de nota como semente (modo associativo puro)")
    p.add_argument("--k", type=int, default=8)
    p.add_argument("--hops", type=int, default=2)
    p.add_argument("--kind")
    p.add_argument("--project")
    p.add_argument("--session")
    p.add_argument("--json", action="store_true")
    p.add_argument("--brief", action="store_true")
    p.add_argument("--no-log", action="store_true", help="nao registrar ativacoes deste recall")
    p.set_defaults(func=cmd_recall)

    p = sub.add_parser("explain")
    p.add_argument("a")
    p.add_argument("b")
    p.add_argument("--max-hops", type=int, default=6)
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=cmd_explain)

    p = sub.add_parser("activate")
    p.add_argument("--paths", nargs="+", required=True)
    p.add_argument("--source", default="manual",
                   choices=["read", "write", "search", "recall", "session", "manual"])
    p.add_argument("--session")
    p.set_defaults(func=cmd_activate)

    p = sub.add_parser("reinforce")
    p.add_argument("--session")
    p.add_argument("--window", type=int, default=240, help="janela em minutos sem session id")
    p.set_defaults(func=cmd_reinforce)

    p = sub.add_parser("decay")
    p.add_argument("--half-life", type=float, default=90.0)
    p.set_defaults(func=cmd_decay)

    p = sub.add_parser("sync-falkor")
    p.add_argument("--full", action="store_true", help="reconciliacao completa (apaga e reprojeta)")
    p.set_defaults(func=cmd_sync_falkor)

    p = sub.add_parser("consolidate")
    p.add_argument("--keep", type=int, default=10)
    p.add_argument("--no-dedup", action="store_true")
    p.add_argument("--no-falkor", action="store_true")
    p.set_defaults(func=cmd_consolidate)

    args = ap.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
