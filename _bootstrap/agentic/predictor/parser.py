"""
parser.py — parsers determinísticos para work-log, roadmap e state do vault.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Work-log
# ---------------------------------------------------------------------------

_WORKLOG_ROW_RE = re.compile(
    r"^\|\s*(?P<date>\d{4}-\d{2}-\d{2})\s*\|"
    r"\s*(?P<type>\w+)\s*\|"
    r"\s*(?P<description>[^|]+)\|"
    r"\s*(?P<epic>[^|]*)\|"
    r"\s*(?P<status>[^|]+)\|",
)


def parse_worklog(path: str | Path) -> list[dict[str, str]]:
    """Retorna lista de entradas do work-log, mais recente primeiro.

    Cada entrada: {date, type, description, epic, status}
    Se o arquivo não existe ou está vazio, retorna lista vazia.
    """
    p = Path(path)
    if not p.exists():
        return []

    entries: list[dict[str, str]] = []
    try:
        text = p.read_text(encoding="utf-8")
    except OSError:
        return []

    for line in text.splitlines():
        m = _WORKLOG_ROW_RE.match(line.strip())
        if m:
            entries.append(
                {
                    "date": m.group("date").strip(),
                    "type": m.group("type").strip().lower(),
                    "description": m.group("description").strip(),
                    "epic": m.group("epic").strip(),
                    "status": m.group("status").strip().lower(),
                }
            )

    # Inverte para recente-primeiro (o arquivo é append-only crescente)
    entries.reverse()
    return entries


# ---------------------------------------------------------------------------
# Roadmap
# ---------------------------------------------------------------------------

_PHASE_HEADING_RE = re.compile(r"^#{1,3}\s+(?P<name>.+?)(?:\s*←\s*atual|\s*✅)?$")
_CURRENT_MARKER_RE = re.compile(r"←\s*atual", re.IGNORECASE)
_DONE_MARKER_RE = re.compile(r"✅")
_ITEM_RE = re.compile(r"^[-*]\s+(.+)$")


def parse_roadmap(path: str | Path) -> dict[str, Any]:
    """Retorna estrutura do roadmap.

    {
        "phases": [
            {
                "name": str,
                "status": "done" | "current" | "pending",
                "items": [str, ...]
            }
        ],
        "current_phase": str | None
    }
    """
    p = Path(path)
    if not p.exists():
        return {"phases": [], "current_phase": None}

    try:
        text = p.read_text(encoding="utf-8")
    except OSError:
        return {"phases": [], "current_phase": None}

    phases: list[dict[str, Any]] = []
    current_phase_name: str | None = None
    current_phase: dict[str, Any] | None = None

    for line in text.splitlines():
        stripped = line.strip()

        # Detecta heading de fase (## Fase X / ### ...)
        m = _PHASE_HEADING_RE.match(stripped)
        if m and stripped.startswith("#"):
            name_raw = stripped.lstrip("#").strip()
            is_current = bool(_CURRENT_MARKER_RE.search(name_raw))
            is_done = bool(_DONE_MARKER_RE.search(name_raw))

            # Limpa marcadores do nome
            name = _CURRENT_MARKER_RE.sub("", name_raw)
            name = _DONE_MARKER_RE.sub("", name).strip(" —-")

            if not name:
                continue

            status = "done" if is_done else ("current" if is_current else "pending")

            current_phase = {"name": name, "status": status, "items": []}
            phases.append(current_phase)

            if is_current:
                current_phase_name = name

        elif current_phase is not None:
            item_m = _ITEM_RE.match(stripped)
            if item_m:
                current_phase["items"].append(item_m.group(1).strip())

    # Heurística: se nenhuma fase foi marcada como "current", a última
    # fase "pending" após todas as "done" é a atual.
    if current_phase_name is None:
        seen_done = False
        for ph in phases:
            if ph["status"] == "done":
                seen_done = True
            elif seen_done and ph["status"] == "pending":
                ph["status"] = "current"
                current_phase_name = ph["name"]
                break

    return {"phases": phases, "current_phase": current_phase_name}


# ---------------------------------------------------------------------------
# State
# ---------------------------------------------------------------------------

# Suporta dois formatos:
#   **Chave:** valor   (dois-pontos dentro do bold, antes do **)
#   **Chave**: valor   (dois-pontos fora do bold, depois do **)
_STATE_FIELD_RE = re.compile(
    r"^\*\*(?P<key>[^*:]+):?\*\*:?\s*(?P<value>.+)$"
)


def parse_state(path: str | Path) -> dict[str, str | list[str]]:
    """Retorna campos do state.md como dicionário normalizado.

    Chaves normalizadas: phase, next_step, blockers, open_questions, branch, prs
    Valor ausente → string vazia ou lista vazia.
    """
    p = Path(path)
    if not p.exists():
        return {
            "phase": "",
            "next_step": "",
            "blockers": "",
            "open_questions": [],
            "branch": "",
            "prs": "",
        }

    try:
        text = p.read_text(encoding="utf-8")
    except OSError:
        return {
            "phase": "",
            "next_step": "",
            "blockers": "",
            "open_questions": [],
            "branch": "",
            "prs": "",
        }

    raw: dict[str, str] = {}
    open_questions: list[str] = []
    in_questions = False

    for line in text.splitlines():
        stripped = line.strip()

        # Seção de perguntas abertas (pode ser lista após heading)
        if re.match(r"^#{1,4}\s+.*open.question", stripped, re.IGNORECASE):
            in_questions = True
            continue
        if in_questions and stripped.startswith("#"):
            in_questions = False
        if in_questions and re.match(r"^[-*]\s+", stripped):
            open_questions.append(stripped.lstrip("-* ").strip())
            continue

        m = _STATE_FIELD_RE.match(stripped)
        if m:
            key = m.group("key").strip().lower()
            value = m.group("value").strip()

            # Mapeamento flexível de chaves
            if "fase" in key or "phase" in key:
                raw["phase"] = value
            elif "próximo" in key or "next" in key or "next_step" in key:
                raw["next_step"] = value
            elif "bloq" in key or "block" in key:
                raw["blockers"] = value
            elif "branch" in key:
                raw["branch"] = value
            elif "pr" == key or key.startswith("pr"):
                raw["prs"] = value

    return {
        "phase": raw.get("phase", ""),
        "next_step": raw.get("next_step", ""),
        "blockers": raw.get("blockers", ""),
        "open_questions": open_questions,
        "branch": raw.get("branch", ""),
        "prs": raw.get("prs", ""),
    }


# ---------------------------------------------------------------------------
# CLI de diagnóstico (python parser.py <work-log-path>)
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import json

    if len(sys.argv) < 2:
        print("Uso: python parser.py <work-log.md> [roadmap.md] [state.md]")
        sys.exit(1)

    wl_path = Path(sys.argv[1])
    entries = parse_worklog(wl_path)
    print(f"=== Work-log ({len(entries)} entradas) ===")
    for e in entries[:10]:
        print(f"  {e['date']} | {e['type']:8s} | {e['description'][:60]}")

    # Tenta inferir roadmap/state do mesmo diretório
    base = wl_path.parent
    rm_path = base / "roadmap.md"
    st_path = base / "state.md"

    if rm_path.exists():
        rm = parse_roadmap(rm_path)
        print(f"\n=== Roadmap (fase atual: {rm['current_phase']}) ===")
        for ph in rm["phases"]:
            marker = " ← atual" if ph["status"] == "current" else (" ✅" if ph["status"] == "done" else "")
            print(f"  {ph['name']}{marker} — {len(ph['items'])} items")

    if st_path.exists():
        st = parse_state(st_path)
        print("\n=== State ===")
        print(json.dumps(st, ensure_ascii=False, indent=2))
