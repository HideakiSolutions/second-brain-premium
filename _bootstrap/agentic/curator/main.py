#!/usr/bin/env python3
"""
main.py — entrypoint do self-curation agent.

Subcomandos:
  scan    — executa heurísticas e grava propostas em _pipeline/curation-proposals.md
  report  — imprime fila atual de propostas
  clear   — remove propostas marcadas como aprovadas [x] ou rejeitadas [~]
"""

from __future__ import annotations

import datetime
import re
import sys
from pathlib import Path

VAULT_ROOT = Path(__file__).resolve().parents[3]
PROPOSALS_FILE = VAULT_ROOT / "_pipeline" / "curation-proposals.md"
MAX_PROPOSALS_PER_DAY = 5

TODAY = datetime.date.today().isoformat()


def _load_store():
    """Importa store.py do indexer via sys.path manipulation."""
    indexer_path = VAULT_ROOT / "_bootstrap" / "agentic" / "indexer"
    if str(indexer_path) not in sys.path:
        sys.path.insert(0, str(indexer_path))
    try:
        import store
        return store
    except ImportError as e:
        print(f"[curator] Falha ao importar store: {e}", file=sys.stderr)
        return None


def _check_qdrant(store) -> bool:
    if store is None:
        return False
    try:
        if not store.qdrant_ready():
            print("[curator] Qdrant offline — abortando scan (exit 0).", file=sys.stderr)
            return False
        if not store.ollama_ready():
            print("[curator] Ollama offline — abortando scan (exit 0).", file=sys.stderr)
            return False
        return True
    except Exception as e:
        print(f"[curator] Erro ao verificar serviços: {e}", file=sys.stderr)
        return False


def _load_existing_proposals() -> str:
    if PROPOSALS_FILE.exists():
        return PROPOSALS_FILE.read_text(encoding="utf-8")
    return ""


def _extract_hash_keys(content: str) -> set[str]:
    """Extrai hash_keys das propostas existentes para dedup."""
    return set(re.findall(r"<!--hash:([^>]+)-->", content))


def _count_today_proposals(content: str) -> int:
    """Conta propostas geradas hoje."""
    pattern = re.compile(r"^### Proposta .* \(" + re.escape(TODAY) + r"\)", re.MULTILINE)
    return len(pattern.findall(content))


def _build_proposal_md(proposal: dict, idx: int) -> str:
    status = "[ ]"
    lines = [
        f"### Proposta {idx} — {proposal['title']} ({TODAY})",
        "",
        f"**Tipo:** {proposal['type']}  ",
        f"**Status:** {status}  ",
        f"<!--hash:{proposal['hash_key']}-->",
        "",
        proposal["body"],
        "",
        "---",
        "",
    ]
    return "\n".join(lines)


def _init_proposals_file() -> str:
    """Cria cabeçalho do arquivo se não existir ou estiver vazio."""
    header = (
        "---\n"
        "tags: [memory, knowledge-mgmt, active]\n"
        "status: active\n"
        f"updated: {TODAY}\n"
        "---\n\n"
        "# Curation Proposals\n\n"
        "> Gerado pelo self-curation agent. Humano aprova via `/curate-vault`.\n"
        "> Marcadores: `[x]` aceito | `[~]` rejeitado | `[ ]` pendente.\n\n"
    )
    return header


def cmd_scan() -> int:
    store = _load_store()
    if not _check_qdrant(store):
        return 0

    from heuristics import (
        h1_learning_clusters,
        h2_orphan_notes,
        h3_free_tags,
        h4_stale_decisions,
        h5_pattern_over_implementation,
        h6_decision_contradiction,
        h7_cross_project_adoption_gap,
    )

    existing_content = _load_existing_proposals()
    existing_hashes = _extract_hash_keys(existing_content)
    today_count = _count_today_proposals(existing_content)

    remaining_slots = MAX_PROPOSALS_PER_DAY - today_count
    if remaining_slots <= 0:
        print(f"[curator] Cap diário atingido ({MAX_PROPOSALS_PER_DAY} propostas). Nenhuma nova proposta gerada.", file=sys.stderr)
        return 0

    # Executar heurísticas
    all_proposals: list[dict] = []
    print("[curator] Executando H1 (clusters de learnings)...", file=sys.stderr)
    try:
        all_proposals.extend(h1_learning_clusters(store))
    except Exception as e:
        print(f"[curator/H1] Erro: {e}", file=sys.stderr)

    print("[curator] Executando H2 (notas orfas)...", file=sys.stderr)
    try:
        all_proposals.extend(h2_orphan_notes(store))
    except Exception as e:
        print(f"[curator/H2] Erro: {e}", file=sys.stderr)

    print("[curator] Executando H3 (tags livres)...", file=sys.stderr)
    try:
        all_proposals.extend(h3_free_tags())
    except Exception as e:
        print(f"[curator/H3] Erro: {e}", file=sys.stderr)

    print("[curator] Executando H4 (decisões obsoletas)...", file=sys.stderr)
    try:
        all_proposals.extend(h4_stale_decisions(store))
    except Exception as e:
        print(f"[curator/H4] Erro: {e}", file=sys.stderr)

    print("[curator] Executando H5 (pattern over-implementation)...", file=sys.stderr)
    try:
        all_proposals.extend(h5_pattern_over_implementation())
    except Exception as e:
        print(f"[curator/H5] Erro: {e}", file=sys.stderr)

    print("[curator] Executando H6 (decision contradiction via graph)...", file=sys.stderr)
    try:
        all_proposals.extend(h6_decision_contradiction())
    except Exception as e:
        print(f"[curator/H6] Erro: {e}", file=sys.stderr)

    print("[curator] Executando H7 (cross-project adoption gap)...", file=sys.stderr)
    try:
        all_proposals.extend(h7_cross_project_adoption_gap())
    except Exception as e:
        print(f"[curator/H7] Erro: {e}", file=sys.stderr)

    # Filtrar duplicatas
    new_proposals = [p for p in all_proposals if p["hash_key"] not in existing_hashes]
    new_proposals = new_proposals[:remaining_slots]

    if not new_proposals:
        print("[curator] Nenhuma proposta nova para adicionar.", file=sys.stderr)
        return 0

    # Garantir que o diretório e arquivo existem
    PROPOSALS_FILE.parent.mkdir(parents=True, exist_ok=True)

    if not existing_content.strip():
        base_content = _init_proposals_file()
    else:
        base_content = existing_content

    # Calcular índice de proposta global (para numerar)
    existing_count = len(re.findall(r"^### Proposta \d+", base_content, re.MULTILINE))

    new_blocks = []
    for i, proposal in enumerate(new_proposals, start=existing_count + 1):
        new_blocks.append(_build_proposal_md(proposal, i))

    # Atualizar updated no frontmatter
    updated_content = re.sub(
        r"^updated: .+$", f"updated: {TODAY}", base_content, count=1, flags=re.MULTILINE
    )

    final_content = updated_content.rstrip("\n") + "\n\n" + "\n".join(new_blocks)
    PROPOSALS_FILE.write_text(final_content, encoding="utf-8")

    counts = {"H1": 0, "H2": 0, "H3": 0, "H4": 0, "H5": 0, "H6": 0, "H7": 0}
    for p in new_proposals:
        counts[p["type"]] = counts.get(p["type"], 0) + 1

    print(
        f"[curator] {len(new_proposals)} proposta(s) adicionada(s): "
        f"H1={counts['H1']} H2={counts['H2']} H3={counts['H3']} H4={counts['H4']} "
        f"H5={counts['H5']} H6={counts['H6']} H7={counts['H7']}",
        file=sys.stderr,
    )
    print(f"[curator] -> {PROPOSALS_FILE.relative_to(VAULT_ROOT)}", file=sys.stderr)
    return 0


def cmd_report() -> int:
    if not PROPOSALS_FILE.exists():
        print("Nenhum arquivo de propostas encontrado. Execute: curator scan")
        return 0
    content = PROPOSALS_FILE.read_text(encoding="utf-8")
    proposals = re.findall(r"(### Proposta .+?)(?=### Proposta |\Z)", content, re.DOTALL)
    if not proposals:
        print("Nenhuma proposta encontrada.")
        return 0

    pending = [p for p in proposals if "[ ]" in p.split("\n", 5)[3] if len(p.split("\n")) > 3]
    accepted = [p for p in proposals if "[x]" in p.split("\n", 5)[3] if len(p.split("\n")) > 3]
    rejected = [p for p in proposals if "[~]" in p.split("\n", 5)[3] if len(p.split("\n")) > 3]

    print("=== Curation Proposals ===")
    print(f"Total: {len(proposals)} | Pendentes: {len(pending)} | Aceitas: {len(accepted)} | Rejeitadas: {len(rejected)}")
    print()
    for p in proposals:
        lines = p.strip().split("\n")
        title_line = lines[0] if lines else ""
        status_line = next((ln for ln in lines if "**Status:**" in ln), "")
        print(f"  {title_line}")
        if status_line:
            print(f"    {status_line.strip()}")
    return 0


def cmd_clear() -> int:
    """Remove propostas marcadas como aceitas [x] ou rejeitadas [~]."""
    if not PROPOSALS_FILE.exists():
        print("[curator] Arquivo de propostas não encontrado.")
        return 0

    content = PROPOSALS_FILE.read_text(encoding="utf-8")
    # Separar header do body de propostas
    header_match = re.match(r"(---.*?---\n\n# .+?\n\n>.*?\n\n)", content, re.DOTALL)
    header = header_match.group(1) if header_match else ""
    rest = content[len(header):]

    # Manter apenas propostas pendentes [ ]
    proposals = re.findall(r"(### Proposta .+?)(?=### Proposta |\Z)", rest, re.DOTALL)
    pending = []
    removed = 0
    for p in proposals:
        lines = p.split("\n")
        status_line = next((ln for ln in lines if "**Status:**" in ln), "")
        if "[x]" in status_line or "[~]" in status_line:
            removed += 1
        else:
            pending.append(p)

    # Renumerar
    renumbered = []
    for i, p in enumerate(pending, start=1):
        p_renumbered = re.sub(r"^### Proposta \d+", f"### Proposta {i}", p, count=1)
        renumbered.append(p_renumbered)

    updated_content = re.sub(
        r"^updated: .+$", f"updated: {TODAY}", header, count=1, flags=re.MULTILINE
    )
    final = updated_content + "\n".join(renumbered)
    PROPOSALS_FILE.write_text(final, encoding="utf-8")
    print(f"[curator] {removed} proposta(s) removida(s). {len(pending)} pendente(s) restante(s).")
    return 0


def main() -> int:
    if len(sys.argv) < 2:
        print("Uso: python3 main.py [scan|report|clear]")
        return 1

    cmd = sys.argv[1].lower()
    if cmd == "scan":
        return cmd_scan()
    elif cmd == "report":
        return cmd_report()
    elif cmd == "clear":
        return cmd_clear()
    else:
        print(f"Subcomando desconhecido: {cmd}. Use: scan | report | clear")
        return 1


if __name__ == "__main__":
    sys.exit(main())
