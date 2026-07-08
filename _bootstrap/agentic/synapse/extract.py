"""
extract.py — constrói o grafo sináptico nota-a-nota a partir do vault.

Todo arquivo .md indexável vira um nó; as arestas tipadas nascem de:
  RELATED     — WikiLinks em seções "## Related"/"## Relacionado" e frontmatter `relacionado:`
  SUPERSEDES  — linhas de substituição/evolução em `_decisions/` com WikiLink
  WIKILINK    — WikiLinks em prosa (peso cresce com nº de menções)
  STRUCTURAL  — arquivo de projeto → nota-hub do projeto
  TAG_SIBLING — notas que compartilham tags discriminativas (2..12 notas por tag)

Determinístico, sem LLM. Reutiliza convenções do chunker (kind, source_file)
para casar 1:1 com os payloads do Qdrant.
"""
from __future__ import annotations

import re
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "indexer"))

import db  # noqa: E402
from chunker import _categorize, _parse_frontmatter, _parse_tags, walk_vault  # noqa: E402

VAULT = db.VAULT

WIKILINK_RE = re.compile(r"\[\[([^\]|]+)(?:\|[^\]]*)?\]\]")
WIKILINK_DISPLAY_RE = re.compile(r"\[\[(?:[^\]|]+)\|([^\]]+)\]\]|\[\[([^\]|]+)\]\]")
HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*$")
H1_RE = re.compile(r"^#\s+(.+)$", re.MULTILINE)
RELATED_HEADING_RE = re.compile(r"related|relacionad|conceitos relacionados|ver tamb", re.IGNORECASE)
SUPERSEDES_LINE_RE = re.compile(r"supersede|substitui|evolui|deprecat|revoga", re.IGNORECASE)
CODE_FENCE_RE = re.compile(r"^(```|~~~)")

# Pesos iniciais por tipo de sinapse (weight_base)
W_RELATED = 0.75
W_SUPERSEDES = 0.90
W_WIKILINK = 0.55
W_WIKILINK_PER_MENTION = 0.05   # cada menção extra, teto em W_WIKILINK_MAX
W_WIKILINK_MAX = 0.75
W_STRUCTURAL = 0.50
W_TAG_SIBLING = 0.30

# Prior de importância por kind (memórias duráveis pesam mais no recall)
KIND_IMPORTANCE = {
    "decisions": 1.30, "learnings": 1.25, "patterns": 1.20, "features": 1.15,
    "cores": 1.10, "projects": 1.00, "infra": 1.00, "index": 0.90,
    "content": 0.90, "source": 0.90, "session": 0.70, "memory": 0.70,
    "pipeline": 0.60, "prompt": 0.60, "other": 0.80,
}
# Dentro de um projeto, alguns arquivos são mais "memória" que outros
PROJECT_FILE_IMPORTANCE = {
    "gotchas": 1.15, "decisions": 1.15, "state": 1.05, "roadmap": 1.00,
    "modules": 1.00, "integrations": 1.00, "work-log": 0.80,
}

# Tags genéricas demais para gerar sinapse TAG_SIBLING
TAG_STOPLIST = {
    "project", "projects", "state", "decisions", "decision", "gotchas", "roadmap",
    "work-log", "modules", "integrations", "active", "completed", "archived",
    "index", "learning", "learnings", "memory", "template", "wiki", "navigation",
    "session-start", "knowledge-mgmt", "generated", "architecture", "ai-sdlc",
    "tooling", "knowledge-management", "current", "feature", "pattern",
}
TAG_SIBLING_MIN = 2
TAG_SIBLING_MAX = 12


def _strip_code(body: str) -> list[str]:
    out: list[str] = []
    in_code = False
    for line in body.split("\n"):
        if CODE_FENCE_RE.match(line):
            in_code = not in_code
            continue
        if not in_code:
            out.append(line)
    return out


def _note_importance(rel: str, kind: str, project: str | None) -> float:
    imp = KIND_IMPORTANCE.get(kind, 0.8)
    if kind == "projects" and project:
        stem = Path(rel).stem
        if stem == project:
            imp = 1.15  # nota-hub do projeto
        elif stem in PROJECT_FILE_IMPORTANCE:
            imp = PROJECT_FILE_IMPORTANCE[stem]
    return imp


def _resolve_target(raw: str, src_path: Path, by_path: dict[str, int],
                    by_slug: dict[str, list[str]], project: str | None) -> int | None:
    """Resolve um alvo de WikiLink para node id: path relativo primeiro, slug depois."""
    target = raw.strip().replace("\\", "/")
    if not target or target.startswith("#"):
        return None
    # 1) resolução por caminho relativo ao arquivo de origem
    if "/" in target:
        cand = (src_path.parent / target).resolve()
        for c in (cand, cand.with_suffix(".md") if cand.suffix != ".md" else cand):
            try:
                rel = c.relative_to(VAULT).as_posix()
            except ValueError:
                continue
            if rel in by_path:
                return by_path[rel]
    # 2) resolução por slug (stem)
    slug = Path(target).stem
    paths = by_slug.get(slug)
    if not paths:
        return None
    if len(paths) == 1:
        return by_path[paths[0]]
    # desempate determinístico: mesmo projeto > caminho mais curto > ordem lexical
    if project:
        same = [p for p in paths if f"/projects/{project}/" in f"/{p}"]
        if same:
            return by_path[sorted(same, key=lambda p: (len(p), p))[0]]
    return by_path[sorted(paths, key=lambda p: (len(p), p))[0]]


def build(conn) -> dict:
    """Reconstrói nodes + arestas `file` do grafo sináptico. Preserva boost/LEARNED."""
    files = walk_vault(VAULT)

    # ---- passo 1: nós ----
    notes: list[dict] = []
    for f in files:
        rel = f.relative_to(VAULT).as_posix()
        kind, project = _categorize(rel)
        try:
            text = f.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        fm, body = _parse_frontmatter(text)
        m = H1_RE.search(body)
        title = m.group(1).strip() if m else Path(rel).stem
        # títulos com WikiLink cru viram só o texto de exibição
        title = WIKILINK_DISPLAY_RE.sub(
            lambda mm: (mm.group(1) or Path(mm.group(2) or "").stem or "").strip(), title
        )
        notes.append({
            "path": rel, "slug": Path(rel).stem, "kind": kind, "project": project,
            "title": title[:200], "status": fm.get("status") or None,
            "created": fm.get("created") or None, "updated": fm.get("updated") or None,
            "importance": _note_importance(rel, kind, project),
            "tags": _parse_tags(fm.get("tags", "")),
            "relacionado": fm.get("relacionado", ""),
            "body": body, "abs": f,
        })

    by_path: dict[str, int] = {}
    for n in notes:
        nid = db.upsert_node(
            conn, path=n["path"], slug=n["slug"], kind=n["kind"], project=n["project"],
            title=n["title"], status=n["status"], created=n["created"],
            updated=n["updated"], importance=n["importance"],
        )
        by_path[n["path"]] = nid

    # nós órfãos: notas removidas do vault saem do grafo (com tombstone p/ projeção)
    current_paths = set(by_path)
    orphans = [
        (int(r["id"]), r["path"])
        for r in conn.execute("SELECT id, path FROM nodes")
        if r["path"] not in current_paths
    ]
    if orphans:
        path_of = {int(r["id"]): r["path"] for r in conn.execute("SELECT id, path FROM nodes")}
        for oid, opath in orphans:
            for e in conn.execute(
                "SELECT src, dst, kind FROM edges WHERE src = ? OR dst = ?", (oid, oid)
            ):
                db.add_edge_tombstone(conn, path_of.get(int(e["src"]), "?"),
                                      path_of.get(int(e["dst"]), "?"), e["kind"])
            conn.execute("DELETE FROM edges WHERE src = ? OR dst = ?", (oid, oid))
            conn.execute("DELETE FROM activations WHERE node = ?", (oid,))
            conn.execute("DELETE FROM coactivations WHERE a = ? OR b = ?", (oid, oid))
            conn.execute("DELETE FROM nodes WHERE id = ?", (oid,))
            db.add_node_tombstone(conn, opath)

    by_slug: dict[str, list[str]] = defaultdict(list)
    for n in notes:
        by_slug[n["slug"]].append(n["path"])

    # ---- passo 2: arestas derivadas de arquivo ----
    edge_acc: dict[tuple[int, int, str], int] = defaultdict(int)  # mentions

    for n in notes:
        src_id = by_path[n["path"]]
        lines = _strip_code(n["body"])
        section = ""
        for line in lines:
            hm = HEADING_RE.match(line)
            if hm:
                section = hm.group(2)
                continue
            in_related = bool(RELATED_HEADING_RE.search(section))
            is_supersede = n["kind"] == "decisions" and bool(SUPERSEDES_LINE_RE.search(line))
            for lm in WIKILINK_RE.finditer(line):
                dst_id = _resolve_target(lm.group(1), n["abs"], by_path, by_slug, n["project"])
                if dst_id is None or dst_id == src_id:
                    continue
                if is_supersede:
                    kind = "SUPERSEDES"
                elif in_related:
                    kind = "RELATED"
                else:
                    kind = "WIKILINK"
                edge_acc[(src_id, dst_id, kind)] += 1
        # frontmatter `relacionado:` → RELATED
        for lm in WIKILINK_RE.finditer(n["relacionado"]):
            dst_id = _resolve_target(lm.group(1), n["abs"], by_path, by_slug, n["project"])
            if dst_id is not None and dst_id != src_id:
                edge_acc[(src_id, dst_id, "RELATED")] += 1
        # STRUCTURAL: arquivo de projeto → hub
        if n["kind"] == "projects" and n["project"] and n["slug"] != n["project"]:
            hub = f"_knowledge/projects/{n['project']}/{n['project']}.md"
            if hub in by_path:
                edge_acc[(src_id, by_path[hub], "STRUCTURAL")] += 1

    # TAG_SIBLING: tags discriminativas compartilhadas
    tag_map: dict[str, list[int]] = defaultdict(list)
    for n in notes:
        nid = by_path[n["path"]]
        for tag in n["tags"]:
            t = tag.strip().lower()
            if not t or t in TAG_STOPLIST or t.startswith("status:"):
                continue
            tag_map[t].append(nid)
    for _tag, ids in tag_map.items():
        uniq = sorted(set(ids))
        if not (TAG_SIBLING_MIN <= len(uniq) <= TAG_SIBLING_MAX):
            continue
        for i, a in enumerate(uniq):
            for b in uniq[i + 1:]:
                edge_acc[(a, b, "TAG_SIBLING")] += 1

    for (src, dst, kind), mentions in edge_acc.items():
        if kind == "WIKILINK":
            w = min(W_WIKILINK + W_WIKILINK_PER_MENTION * (mentions - 1), W_WIKILINK_MAX)
        elif kind == "RELATED":
            w = W_RELATED
        elif kind == "SUPERSEDES":
            w = W_SUPERSEDES
        elif kind == "STRUCTURAL":
            w = W_STRUCTURAL
        else:  # TAG_SIBLING — menções = nº de tags compartilhadas
            w = min(W_TAG_SIBLING + 0.05 * (mentions - 1), 0.45)
        db.upsert_file_edge(conn, src, dst, kind, w, mentions)

    # limpeza: arestas file que sumiram dos arquivos
    # (com boost aprendido: preserva a sinapse zerando só a base; sem boost: remove)
    id_to_path = {nid: p for p, nid in by_path.items()}
    current_keys = set(edge_acc.keys())
    ts = db.now_iso()
    for e in conn.execute(
        "SELECT src, dst, kind, boost FROM edges WHERE source = 'file'"
    ).fetchall():
        key = (int(e["src"]), int(e["dst"]), e["kind"])
        if key in current_keys:
            continue
        if float(e["boost"]) > 0:
            conn.execute(
                "UPDATE edges SET weight_base = 0.0, updated_at = ? "
                "WHERE src = ? AND dst = ? AND kind = ?",
                (ts, e["src"], e["dst"], e["kind"]),
            )
        else:
            conn.execute(
                "DELETE FROM edges WHERE src = ? AND dst = ? AND kind = ?",
                (e["src"], e["dst"], e["kind"]),
            )
            db.add_edge_tombstone(conn, id_to_path.get(int(e["src"]), "?"),
                                  id_to_path.get(int(e["dst"]), "?"), e["kind"])

    db.set_meta(conn, "last_build", db.now_iso())
    conn.commit()

    return {
        "files": len(files),
        "nodes": len(by_path),
        "edges": conn.execute("SELECT COUNT(*) AS c FROM edges").fetchone()["c"],
        "edges_file": conn.execute(
            "SELECT COUNT(*) AS c FROM edges WHERE source = 'file' AND weight_base > 0"
        ).fetchone()["c"],
    }
