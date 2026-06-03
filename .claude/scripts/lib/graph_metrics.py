#!/usr/bin/env python3
"""
graph_metrics — calcula métricas de densidade do grafo de WikiLinks no vault
e atualiza _memory/graph-metrics.md.

Métricas:
- Total .md, total WikiLinks
- % ilhas (zero links de saída em prosa) por categoria
- Grau médio (out-degree)
- Top hubs (mais linkados)
- Projetos com ≥3 patterns linkados (target ≥90%)
- Patterns/features com 0 backlinks (alvo: 0)
- Tags fora da taxonomia (alvo: 0)
- Broken links (alvo: 0)
"""

from __future__ import annotations

import datetime as dt
import os
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

VAULT_ROOT = Path(__file__).resolve().parents[3]

WIKILINK_RE = re.compile(r"\[\[([^\]]+)\]\]")
CODE_FENCE_RE = re.compile(r"^(```|~~~)")
INLINE_CODE_RE = re.compile(r"`[^`\n]+`")

CATEGORIES = {
    "_patterns": "patterns",
    "_features": "features",
    "_decisions": "decisions",
    "_learnings": "learnings",
    "_cores": "cores",
    "_knowledge/projects": "projects",
    "_knowledge": "knowledge",
    "_index": "index",
    "_content": "content",
    "_infrastructure": "infrastructure",
    "_sources": "sources",
}

SEMANTIC_PREFIXES = tuple(CATEGORIES.keys())

EXCLUDED_TOP_LEVEL = {
    ".git",
    ".obsidian",
    ".second-brain",
    ".logs",
    ".claude",
    ".codex",
    ".axon",
    ".github",
    ".worktrees",
    "_bootstrap",
    "_memory",
    "_prompts",
    "_pipeline",
    "_references",
    "node_modules",
}

EXCLUDED_ANY_PART = {
    ".git",
    ".worktrees",
    "node_modules",
}

EXCLUDED_GENERATED_FILES = {
    "_index/CONCEPT-INDEX.md",
    "_infrastructure/SNAPSHOT.md",
    "_cores/weekly-report-latest.md",
}

EXCLUDED_SEMANTIC_DIRS = {
    "_knowledge/projects/_template",
}

LAYER_TAGS = {
    "pattern", "feature", "decision", "learning", "project", "core",
    "infra", "infrastructure", "knowledge", "content", "source", "index",
    "memory", "session", "wiki",
}
MATURITY_TAGS = {
    "production", "beta", "mvp", "spike", "candidate",
    "deprecated", "archived", "active", "wip", "published",
    "draft-ready", "proposed", "approved", "publicado", "rascunho",
    "ativo", "completed", "spec-only",
}
DOMAIN_TAGS = {
    "fintech", "trading", "payments", "compliance", "ai-sdlc", "ai-agents",
    "infra-eng", "devtools", "knowledge-mgmt", "observability", "security",
    "data-platform", "messaging", "frontend", "backend", "mobile", "platform",
    "governance", "forex", "crypto", "events", "automation", "voice-text",
    "architecture", "mandatory",
}
PROJECT_FILE_TYPES = {
    "work-log", "decisions", "gotchas", "roadmap", "state", "modules",
    "integrations", "agents", "skills", "workflows", "servers", "policies",
    "structure", "index",
}

VALID_TAGS = LAYER_TAGS | MATURITY_TAGS | DOMAIN_TAGS | PROJECT_FILE_TYPES


def categorize(rel_path: str) -> str:
    for prefix, label in CATEGORIES.items():
        if rel_path.startswith(prefix + "/") or rel_path == prefix:
            return label
    return "other"


def strip_frontmatter_and_code(text: str) -> str:
    """Remove frontmatter, blocos e inline code para contar links em prosa."""
    if text.startswith("---\n"):
        end = text.find("\n---\n", 4)
        if end != -1:
            text = text[end + 5 :]
    out: list[str] = []
    in_code = False
    for line in text.split("\n"):
        if CODE_FENCE_RE.match(line):
            in_code = not in_code
            continue
        if in_code:
            continue
        out.append(line)
    return INLINE_CODE_RE.sub("", "\n".join(out))


def parse_frontmatter(text: str) -> dict:
    if not text.startswith("---\n"):
        return {}
    end = text.find("\n---\n", 4)
    if end == -1:
        return {}
    fm: dict = {}
    for line in text[4:end].splitlines():
        if ":" not in line:
            continue
        k, v = line.split(":", 1)
        fm[k.strip()] = v.strip()
    return fm


def parse_tags_value(value: str) -> list[str]:
    value = value.strip()
    if value.startswith("[") and value.endswith("]"):
        inner = value[1:-1]
        return [t.strip().strip('"').strip("'") for t in inner.split(",") if t.strip()]
    return [t.strip() for t in value.split(",") if t.strip()]


def collect_files() -> list[Path]:
    out: list[Path] = []
    for root, dirs, files in os.walk(VAULT_ROOT):
        rel_root = Path(root).relative_to(VAULT_ROOT)
        # Medir o grafo semântico, não o runtime operacional do agente.
        if rel_root.parts and (
            rel_root.parts[0] in EXCLUDED_TOP_LEVEL
            or any(part in EXCLUDED_ANY_PART for part in rel_root.parts)
        ):
            dirs[:] = []
            continue
        for f in files:
            if not f.endswith(".md"):
                continue
            path = Path(root) / f
            rel = str(path.relative_to(VAULT_ROOT))
            if rel in EXCLUDED_GENERATED_FILES:
                continue
            if any(rel.startswith(prefix + "/") for prefix in EXCLUDED_SEMANTIC_DIRS):
                continue
            if any(rel.startswith(prefix + "/") for prefix in SEMANTIC_PREFIXES):
                out.append(path)
    return out


def collect_resolvable_files() -> list[Path]:
    """Arquivos que podem ser alvo válido de WikiLink.

    Nem todo alvo válido deve entrar no grafo visual principal. Exemplo:
    `_memory/current-state.md` existe e pode ser linkado por notas pessoais,
    mas não deve distorcer métricas semânticas como hub operacional.
    """
    out: list[Path] = []
    for root, dirs, files in os.walk(VAULT_ROOT):
        rel_root = Path(root).relative_to(VAULT_ROOT)
        if rel_root.parts and (
            rel_root.parts[0] in {".git", ".obsidian", ".second-brain", ".logs", "_references", "node_modules"}
            or any(part in EXCLUDED_ANY_PART for part in rel_root.parts)
        ):
            dirs[:] = []
            continue
        for f in files:
            if f.endswith(".md"):
                out.append(Path(root) / f)
    return out


def normalize_link_target(raw: str) -> str:
    """Resolve target de WikiLink para um path relativo do vault sem extensão."""
    target = raw.split("|")[0].strip()
    target = target.split("#")[0]
    target = target.replace("\\", "/")
    return target.removesuffix(".md").rstrip("/")


_LITERAL_PATTERNS = {
    "WikiLinks", "...", "...|...", "wiki-links", "tag",
    "YYYY-MM-DD", "title", "name", "slug",
}


def find_md_for_target(target: str, source: Path, all_files: set[Path]) -> Path | None:
    """Resolve um target de WikiLink em um caminho real."""
    if "{{" in target or "}}" in target or "$" in target:
        return source
    if not target or target in _LITERAL_PATTERNS:
        # Padrões literais usados em documentação (ex: explicar formato de WikiLink)
        return source  # marca como "resolvido" para não contar como broken
    if "/" in target:
        candidates: list[Path] = []
        if target.startswith("/"):
            candidates.append((VAULT_ROOT / target.lstrip("/")).with_suffix(".md"))
        else:
            # Obsidian aceita tanto path relativo ao arquivo quanto path a partir
            # da raiz do vault. Tentar os dois evita falso broken em links como
            # `[[_patterns/cqrs]]`.
            candidates.append((source.parent / target).with_suffix(".md"))
            candidates.append((VAULT_ROOT / target).with_suffix(".md"))
            leaf = target.split("/")[-1]
            candidates.append(VAULT_ROOT / target / f"{leaf}.md")
        for p in candidates:
            try:
                rp = p.resolve()
            except OSError:
                continue
            if rp in all_files:
                return rp
        return None
    # target sem slash: bate exato por nome de arquivo
    name = target + ".md"
    matches = [f for f in all_files if f.name == name]
    if matches:
        return matches[0]
    # tentativa: slug parcial (ex: 'cqrs-source-of-truth' bate '2026-04-11-cqrs-source-of-truth.md')
    suffix_matches = [f for f in all_files if f.stem.endswith("-" + target) or f.stem.endswith(target)]
    if len(suffix_matches) == 1:
        return suffix_matches[0]
    return None


def main() -> int:
    files = collect_files()
    graph_files = {f.resolve() for f in files}
    all_files = {f.resolve() for f in collect_resolvable_files()}

    total_files = len(files)
    by_category: Counter[str] = Counter()
    out_degree: dict[Path, int] = {}
    in_degree: Counter[Path] = Counter()
    islands: dict[str, list[str]] = defaultdict(list)
    broken_links: list[tuple[str, str]] = []
    tag_violations: list[tuple[str, list[str]]] = []
    project_pattern_count: dict[str, int] = {}
    project_feature_count: dict[str, int] = {}

    for f in files:
        try:
            text = f.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        rel = str(f.relative_to(VAULT_ROOT))
        cat = categorize(rel)
        by_category[cat] += 1

        # Tags: violação = ausência de camada+maturidade+domínio.
        # Maturidade pode estar no campo `status:` separado (compatibilidade legada).
        # Tags livres adicionais são permitidas.
        fm = parse_frontmatter(text)
        if "tags" in fm:
            tags = parse_tags_value(fm["tags"])
            has_layer = any(t in LAYER_TAGS for t in tags)
            has_maturity = any(t in MATURITY_TAGS for t in tags)
            if not has_maturity and fm.get("status", "").strip().strip('"') in MATURITY_TAGS:
                has_maturity = True
            missing: list[str] = []
            if not has_layer:
                missing.append("layer")
            if not has_maturity:
                missing.append("maturity")
            if missing:
                tag_violations.append((rel, missing))

        # Out-degree (em prosa, ignora code/frontmatter)
        prose = strip_frontmatter_and_code(text)
        out_links_raw = WIKILINK_RE.findall(prose)
        out_count = len(out_links_raw)
        out_degree[f.resolve()] = out_count
        if out_count == 0:
            islands[cat].append(rel)

        for raw in out_links_raw:
            target = normalize_link_target(raw)
            tgt = find_md_for_target(target, f.resolve(), all_files)
            if tgt is None:
                broken_links.append((rel, raw))
            else:
                if tgt in graph_files:
                    in_degree[tgt] += 1

    # Projects: count linked patterns/features
    projects_dir = VAULT_ROOT / "_knowledge" / "projects"
    if projects_dir.exists():
        for d in projects_dir.iterdir():
            if not d.is_dir():
                continue
            if d.name == "_template":
                continue
            patterns: set[str] = set()
            features: set[str] = set()
            for md in d.glob("*.md"):
                try:
                    text = md.read_text(encoding="utf-8")
                except (OSError, UnicodeDecodeError):
                    continue
                for raw in WIKILINK_RE.findall(text):
                    target = raw.split("|")[0].strip()
                    if "_patterns/" in target:
                        slug = target.split("_patterns/")[-1].split("/")[0]
                        patterns.add(slug)
                    elif "_features/" in target:
                        slug = target.split("_features/")[-1].split("/")[0]
                        features.add(slug)
            project_pattern_count[d.name] = len(patterns)
            project_feature_count[d.name] = len(features)

    # Patterns/features without backlinks
    patterns_no_backlinks: list[str] = []
    for p in (VAULT_ROOT / "_patterns").glob("*.md"):
        if in_degree.get(p.resolve(), 0) == 0:
            patterns_no_backlinks.append(p.stem)
    features_no_backlinks: list[str] = []
    for p in (VAULT_ROOT / "_features").glob("*.md"):
        if in_degree.get(p.resolve(), 0) == 0:
            features_no_backlinks.append(p.stem)

    # Hubs (top in-degree)
    hubs = sorted(in_degree.items(), key=lambda kv: kv[1], reverse=True)[:15]

    total_links = sum(out_degree.values())
    avg_degree = total_links / total_files if total_files else 0.0

    # Output
    today = dt.date.today().isoformat()
    out_path = VAULT_ROOT / "_memory" / "graph-metrics.md"
    lines: list[str] = []
    lines.append("---")
    lines.append("tags: [memory, knowledge-mgmt, active, generated]")
    lines.append("status: active")
    lines.append(f"updated: {today}")
    lines.append("source: .claude/scripts/lib/graph_metrics.py")
    lines.append("---")
    lines.append("")
    lines.append(f"# Graph Metrics — {today}")
    lines.append("")
    lines.append("> Auto-gerado. Snapshot do estado do grafo de WikiLinks.")
    lines.append("")
    lines.append("## Resumo")
    lines.append("")
    lines.append(f"- **Arquivos .md analisados:** {total_files}")
    lines.append(f"- **WikiLinks totais (prosa, ignorando code/frontmatter):** {total_links}")
    lines.append(f"- **Grau médio (out-degree):** {avg_degree:.2f}")
    lines.append(f"- **Broken links:** {len(broken_links)}")
    lines.append(f"- **Tags fora da taxonomia:** {len(tag_violations)}")
    lines.append("")

    lines.append("## Ilhas (arquivos sem links de saída)")
    lines.append("")
    lines.append("| Categoria | Arquivos | Ilhas | % |")
    lines.append("|---|---|---|---|")
    for cat, total in sorted(by_category.items(), key=lambda kv: -kv[1]):
        cat_islands = len(islands.get(cat, []))
        pct = (cat_islands / total * 100) if total else 0
        lines.append(f"| {cat} | {total} | {cat_islands} | {pct:.1f}% |")
    total_islands = sum(len(v) for v in islands.values())
    overall_pct = (total_islands / total_files * 100) if total_files else 0
    lines.append(f"| **TOTAL** | **{total_files}** | **{total_islands}** | **{overall_pct:.1f}%** |")
    lines.append("")

    lines.append("## Cobertura projetos × patterns/features")
    lines.append("")
    lines.append("| Projeto | Patterns | Features | Atinge ≥3 patterns? |")
    lines.append("|---|---|---|---|")
    for proj in sorted(project_pattern_count.keys()):
        np = project_pattern_count[proj]
        nf = project_feature_count[proj]
        ok = "✓" if np >= 3 else "—"
        lines.append(f"| {proj} | {np} | {nf} | {ok} |")
    if project_pattern_count:
        meeting = sum(1 for n in project_pattern_count.values() if n >= 3)
        total_proj = len(project_pattern_count)
        coverage_pct = meeting / total_proj * 100
        lines.append(f"| **Cobertura ≥3** | — | — | **{meeting}/{total_proj} ({coverage_pct:.1f}%)** |")
    lines.append("")

    lines.append(f"## Patterns sem backlinks ({len(patterns_no_backlinks)})")
    lines.append("")
    if patterns_no_backlinks:
        for slug in sorted(patterns_no_backlinks):
            lines.append(f"- `{slug}`")
    else:
        lines.append("_Nenhum — todos os patterns têm pelo menos 1 backlink._")
    lines.append("")

    lines.append(f"## Features sem backlinks ({len(features_no_backlinks)})")
    lines.append("")
    if features_no_backlinks:
        for slug in sorted(features_no_backlinks):
            lines.append(f"- `{slug}`")
    else:
        lines.append("_Nenhum — todas as features têm pelo menos 1 backlink._")
    lines.append("")

    lines.append("## Top hubs (in-degree)")
    lines.append("")
    lines.append("| # | Arquivo | Backlinks |")
    lines.append("|---|---|---|")
    for i, (path, deg) in enumerate(hubs, 1):
        rel = path.relative_to(VAULT_ROOT)
        lines.append(f"| {i} | `{rel}` | {deg} |")
    lines.append("")

    if broken_links:
        lines.append(f"## Broken links ({len(broken_links)})")
        lines.append("")
        for src, raw in broken_links[:30]:
            lines.append(f"- `{src}` → `[[{raw}]]`")
        if len(broken_links) > 30:
            lines.append(f"_... e {len(broken_links) - 30} mais_")
        lines.append("")

    if tag_violations:
        lines.append(f"## Tags fora da taxonomia ({len(tag_violations)})")
        lines.append("")
        for src, tags in tag_violations[:30]:
            lines.append(f"- `{src}`: {tags}")
        if len(tag_violations) > 30:
            lines.append(f"_... e {len(tag_violations) - 30} mais_")
        lines.append("")

    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"[graph-metrics] {out_path.relative_to(VAULT_ROOT)} atualizado", file=sys.stderr)
    print(f"  ilhas: {overall_pct:.1f}% · grau médio: {avg_degree:.2f} · broken: {len(broken_links)} · tags-violations: {len(tag_violations)}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
