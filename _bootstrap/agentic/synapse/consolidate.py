"""
consolidate.py — ciclo de consolidação ("sono") da memória.

Fases (todas fail-soft, nada é apagado — só movido, proposto ou agregado):
  1. compact   — `_memory/current-state.md` mantém os N rollups mais recentes;
                 o excedente vai para `_memory/current-state-history/` (íntegro).
  2. expire    — decay de capturas pendentes (delegado ao memory_reviewer).
  3. dedup     — quase-duplicatas semânticas em _decisions/_learnings (proposta,
                 gate humano; requer stack online).
  4. propose   — sinapses LEARNED fortes viram sugestões de WikiLink real;
                 co-ativações recorrentes sem nota-hub viram sugestão de conceito.
  5. sync      — projeção do grafo sináptico (com pesos) para o FalkorDB
                 (graph `synapse`), consultável via Cypher/MCP.
  6. report    — `_memory/synapse-report.md` com o resultado do ciclo.
"""
from __future__ import annotations

import re
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import db  # noqa: E402

VAULT = db.VAULT
CURRENT_STATE = VAULT / "_memory" / "current-state.md"
HISTORY_DIR = VAULT / "_memory" / "current-state-history"
REPORT = VAULT / "_memory" / "synapse-report.md"
KEEP_ROLLUPS = 10
DEDUP_THRESHOLD = 0.93
LEARNED_SUGGEST_MIN = 0.45


def compact_current_state(keep: int = KEEP_ROLLUPS) -> dict:
    """Move rollups antigos do current-state para o histórico. Nunca perde conteúdo."""
    if not CURRENT_STATE.exists():
        return {"skipped": "current-state.md ausente"}
    text = CURRENT_STATE.read_text(encoding="utf-8", errors="replace")
    parts = re.split(r"(?=^## )", text, flags=re.MULTILINE)
    header, sections = parts[0], parts[1:]
    if len(sections) <= keep:
        return {"sections": len(sections), "moved": 0,
                "size_kb": round(len(text) / 1024, 1)}

    kept, moved = sections[:keep], sections[keep:]
    stamp = datetime.now(UTC).strftime("%Y-%m-%d")
    HISTORY_DIR.mkdir(parents=True, exist_ok=True)
    hist_file = HISTORY_DIR / f"rollups-ate-{stamp}.md"
    hist_header = (
        f"# Rollups consolidados em {stamp}\n\n"
        f"> Movidos de `current-state.md` pelo ciclo de consolidacao sinaptica.\n"
        f"> Conteudo integral preservado; ordem original mantida.\n\n"
    )
    existing = hist_file.read_text(encoding="utf-8", errors="replace") if hist_file.exists() else ""
    hist_file.write_text(
        (existing + "\n" if existing else hist_header) + "".join(moved),
        encoding="utf-8",
    )

    note = (
        f"\n---\n\n> Rollups anteriores consolidados em "
        f"`_memory/current-state-history/rollups-ate-{stamp}.md` "
        f"({len(moved)} secoes movidas em {stamp}).\n"
    )
    new_text = header + "".join(kept) + note
    CURRENT_STATE.write_text(new_text, encoding="utf-8")
    return {"sections": len(sections), "moved": len(moved),
            "size_kb_before": round(len(text) / 1024, 1),
            "size_kb_after": round(len(new_text) / 1024, 1),
            "history_file": hist_file.relative_to(VAULT).as_posix()}


def expire_captures() -> str:
    """Delegado ao memory_reviewer (respeita o allowlist dele)."""
    script = VAULT / ".claude" / "scripts" / "lib" / "memory_reviewer.py"
    if not script.exists():
        return "memory_reviewer ausente"
    proc = subprocess.run(
        [sys.executable, str(script), "expire"],
        cwd=str(VAULT), capture_output=True, text=True, timeout=60, check=False,
    )
    return (proc.stdout or proc.stderr or "").strip()


def find_near_duplicates(threshold: float = DEDUP_THRESHOLD) -> list[dict]:
    """Quase-duplicatas semânticas entre decisões/learnings (proposta, gate humano)."""
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "indexer"))
    try:
        from store import embed, ollama_ready, qdrant_ready, search  # noqa: PLC0415
    except ImportError:
        return []
    if not (qdrant_ready() and ollama_ready()):
        return []

    conn = db.connect()
    rows = conn.execute(
        "SELECT path, title, kind FROM nodes WHERE kind IN ('decisions', 'learnings') ORDER BY path"
    ).fetchall()
    conn.close()

    pairs: list[dict] = []
    seen: set[tuple[str, str]] = set()
    for row in rows:
        try:
            qvec = embed(row["title"])
            hits = search(qvec, k=4, filter_={"must": [{"key": "kind", "match": {"value": row["kind"]}}]})
        except Exception:
            continue
        for h in hits:
            other = h.get("payload", {}).get("source_file", "")
            score = float(h.get("score", 0.0))
            if not other or other == row["path"] or score < threshold:
                continue
            key = tuple(sorted((row["path"], other)))
            if key in seen:
                continue
            seen.add(key)
            pairs.append({"a": row["path"], "b": other, "score": round(score, 3)})
    return pairs


def learned_suggestions() -> list[dict]:
    """Sinapses LEARNED fortes → candidatas a WikiLink real (curadoria humana)."""
    conn = db.connect()
    rows = conn.execute(
        """
        SELECT e.boost, na.path AS a_path, na.title AS a_title,
               nb.path AS b_path, nb.title AS b_title
        FROM edges e
        JOIN nodes na ON na.id = e.src
        JOIN nodes nb ON nb.id = e.dst
        WHERE e.source = 'learned' AND e.boost >= ?
        ORDER BY e.boost DESC LIMIT 20
        """,
        (LEARNED_SUGGEST_MIN,),
    ).fetchall()
    conn.close()
    return [
        {"a": r["a_path"], "b": r["b_path"], "boost": round(float(r["boost"]), 2),
         "suggestion": f"[[{Path(r['b_path']).stem}]] em {r['a_path']}"}
        for r in rows
    ]


def sync_falkor() -> dict:
    """Reconciliação full da projeção FalkorDB (delega ao falkor_sync).

    O caminho near-online é o sync incremental automático pós build/reinforce/
    decay; aqui, no ciclo semanal, a projeção é refeita do zero para eliminar
    qualquer resíduo divergente (deleções perdidas, drift).
    """
    import falkor_sync  # noqa: PLC0415
    return falkor_sync.sync(full=True)


def run(keep: int = KEEP_ROLLUPS, dedup: bool = True, falkor: bool = True) -> dict:
    """Ciclo completo de consolidação. Escreve o relatório e retorna o resumo."""
    result: dict = {"ts": db.now_iso()}
    result["compact"] = compact_current_state(keep=keep)
    result["expire"] = expire_captures()
    result["duplicates"] = find_near_duplicates() if dedup else []
    result["link_suggestions"] = learned_suggestions()
    result["falkor"] = sync_falkor() if falkor else {"skipped": "desativado"}

    conn = db.connect()
    result["stats"] = db.stats(conn)
    db.set_meta(conn, "last_consolidate", db.now_iso())
    conn.commit()
    conn.close()

    _write_report(result)
    return result


def _write_report(result: dict) -> None:
    stamp = datetime.now(UTC).strftime("%Y-%m-%d %H:%M")
    stats = result.get("stats", {})
    compact = result.get("compact", {})
    lines = [
        "---",
        "tags: [memory, knowledge-mgmt, generated]",
        "status: active",
        f"updated: {datetime.now(UTC).strftime('%Y-%m-%d')}",
        "source: _bootstrap/agentic/synapse/consolidate.py",
        "---",
        "",
        f"# Synapse Report — {stamp}",
        "",
        "> Auto-gerado pelo ciclo de consolidacao. Propostas exigem curadoria humana.",
        "",
        "## Grafo sinaptico",
        "",
        f"- Nos: {stats.get('nodes', '?')} · Arestas: {stats.get('edges', '?')} "
        f"(aprendidas: {stats.get('learned_edges', 0)})",
        f"- Ativacoes registradas: {stats.get('activations', 0)} · "
        f"Co-ativacoes pendentes: {stats.get('coactivations_pending', 0)}",
        f"- Arestas por tipo: {stats.get('edges_by_kind', {})}",
        "",
        "## Consolidacao do current-state",
        "",
        f"- {compact}",
        "",
        "## Expiracao de capturas",
        "",
        f"- {result.get('expire', '')}",
        "",
        "## Quase-duplicatas propostas (gate humano)",
        "",
    ]
    dups = result.get("duplicates", [])
    if dups:
        lines += [f"- `{d['a']}` ≈ `{d['b']}` (score {d['score']})" for d in dups]
    else:
        lines.append("- nenhuma acima do threshold")
    lines += ["", "## Sinapses aprendidas → sugestoes de WikiLink (gate humano)", ""]
    sugg = result.get("link_suggestions", [])
    if sugg:
        lines += [f"- {s['suggestion']} (boost {s['boost']})" for s in sugg]
    else:
        lines.append("- nenhuma sinapse aprendida forte o suficiente ainda")
    lines += ["", "## Projecao FalkorDB", "", f"- {result.get('falkor', {})}", ""]
    REPORT.write_text("\n".join(lines), encoding="utf-8")
