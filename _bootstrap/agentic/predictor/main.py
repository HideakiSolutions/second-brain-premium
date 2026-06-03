"""
main.py — CLI do predictor de próximas tarefas por projeto.

Uso:
  python3 main.py predict --project <slug> [--k 5] [--vault /path/to/vault]
  python3 main.py types-distribution --project <slug> [--vault /path/to/vault]
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

# Adiciona o diretório pai ao path para facilitar imports diretos
_HERE = Path(__file__).parent
sys.path.insert(0, str(_HERE))

from llm_analyst import _type_distribution_from_history, predict
from parser import parse_roadmap, parse_state, parse_worklog

# Vault padrão — detectado por variável de env ou caminho canônico
_DEFAULT_VAULT = os.environ.get(
    "SB_VAULT_ROOT", "$VAULT"
)


# ---------------------------------------------------------------------------
# Helpers de formatação
# ---------------------------------------------------------------------------

_CONFIDENCE_BAR = {
    (0.8, 1.01): "████████",
    (0.6, 0.80): "██████░░",
    (0.4, 0.60): "████░░░░",
    (0.2, 0.40): "██░░░░░░",
    (0.0, 0.20): "░░░░░░░░",
}


def _confidence_bar(c: float) -> str:
    for (lo, hi), bar in _CONFIDENCE_BAR.items():
        if lo <= c < hi:
            return bar
    return "░░░░░░░░"


def _fmt_predictions(
    project: str,
    predictions: list[dict],
    state: dict,
    roadmap: dict,
    source: str,
) -> str:
    phase = state.get("phase") or roadmap.get("current_phase") or "desconhecida"
    lines: list[str] = [
        "",
        f"Predictor — {project}",
        f"Fase atual: {phase}",
        f"Fonte: {source}",
        "",
        f"{'#':<3} {'Tipo':<10} {'Confiança':<12} {'Incerteza':<12} Tarefa prevista",
        f"{'-'*3} {'-'*10} {'-'*12} {'-'*12} {'-'*50}",
    ]
    for p in predictions:
        rank = p.get("rank", "?")
        ptype = p.get("type", "task")
        conf = p.get("confidence", 0.0)
        unc = p.get("uncertainty", "?")
        desc = p.get("description", "")
        lines.append(
            f"{rank:<3} {ptype:<10} {_confidence_bar(conf)} {conf:.0%}  {unc:<12} {desc}"
        )

    lines.append("")
    lines.append("Detalhamento:")
    for p in predictions:
        lines.append(
            f"  [{p.get('rank','?')}] {p.get('description', '')}"
        )
        if p.get("rationale"):
            lines.append(f"       Racional: {p['rationale']}")
    lines.append("")
    return "\n".join(lines)


def _fmt_types_distribution(project: str, entries: list[dict]) -> str:
    dist = _type_distribution_from_history(entries, n=30)
    total = len(entries[:30])
    lines: list[str] = [
        "",
        f"Distribuição de tipos — {project} (últimas {total} entradas)",
        "",
        f"{'Tipo':<12} {'Freq.':<8} {'%':<6} Barra",
        f"{'-'*12} {'-'*8} {'-'*6} {'-'*20}",
    ]
    counts: dict[str, int] = {}
    for e in entries[:total]:
        t = e.get("type", "task")
        counts[t] = counts.get(t, 0) + 1

    for tipo, prob in sorted(dist.items(), key=lambda x: x[1], reverse=True):
        count = counts.get(tipo, 0)
        bar = "█" * int(prob * 20)
        lines.append(f"{tipo:<12} {count:<8} {prob:.0%}    {bar}")
    lines.append("")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Loader de arquivos do projeto
# ---------------------------------------------------------------------------

def _load_project(vault: Path, project: str) -> tuple[list[dict], dict, dict, list[str]]:
    """Retorna (entries, roadmap, state, warnings)."""
    warnings: list[str] = []
    proj_dir = vault / "_knowledge" / "projects" / project

    if not proj_dir.exists():
        warnings.append(f"AVISO: Projeto '{project}' não encontrado em {proj_dir}")

    wl_path = proj_dir / "work-log.md"
    rm_path = proj_dir / "roadmap.md"
    st_path = proj_dir / "state.md"

    entries = parse_worklog(wl_path)
    if not entries and wl_path.exists():
        warnings.append("AVISO: work-log.md existe mas está vazio ou sem entradas tabulares.")
    elif not wl_path.exists():
        warnings.append("AVISO: work-log.md não encontrado — predição sem histórico.")

    roadmap = parse_roadmap(rm_path)
    if not rm_path.exists():
        warnings.append("AVISO: roadmap.md não encontrado — predição sem contexto de fase.")

    state = parse_state(st_path)
    if not st_path.exists():
        warnings.append("AVISO: state.md não encontrado — predição sem próximo passo declarado.")

    return entries, roadmap, state, warnings


# ---------------------------------------------------------------------------
# Subcomandos
# ---------------------------------------------------------------------------

def cmd_predict(args: argparse.Namespace) -> int:
    vault = Path(args.vault)
    project = args.project
    k = args.k

    entries, roadmap, state, warnings = _load_project(vault, project)

    for w in warnings:
        print(w, file=sys.stderr)

    predictions, source = predict(project, entries, roadmap, state, k=k)
    output = _fmt_predictions(project, predictions, state, roadmap, source)
    print(output)
    return 0


def cmd_types_distribution(args: argparse.Namespace) -> int:
    vault = Path(args.vault)
    project = args.project

    entries, _, _, warnings = _load_project(vault, project)

    for w in warnings:
        print(w, file=sys.stderr)

    if not entries:
        print(f"Nenhuma entrada no work-log de '{project}'.")
        return 0

    print(_fmt_types_distribution(project, entries))
    return 0


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="predictor",
        description="Preditor de próximas tarefas por projeto do vault.",
    )
    parser.add_argument(
        "--vault",
        default=_DEFAULT_VAULT,
        help="Caminho raiz do vault (padrão: $SB_VAULT_ROOT ou $VAULT)",
    )

    sub = parser.add_subparsers(dest="command", required=True)

    # predict
    p_pred = sub.add_parser("predict", help="Projeta 3-5 próximas tarefas para um projeto.")
    p_pred.add_argument("--project", "-p", required=True, help="Slug do projeto")
    p_pred.add_argument("--k", type=int, default=5, help="Número de predições (padrão: 5)")
    p_pred.set_defaults(func=cmd_predict)

    # types-distribution
    p_dist = sub.add_parser(
        "types-distribution", help="Mostra distribuição de tipos do work-log."
    )
    p_dist.add_argument("--project", "-p", required=True, help="Slug do projeto")
    p_dist.set_defaults(func=cmd_types_distribution)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
