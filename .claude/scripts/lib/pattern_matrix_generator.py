#!/usr/bin/env python3
"""
pattern_matrix_generator — gera bloco delimitado em PATTERN-MATRIX.md e
FEATURE-CATALOG.md mostrando, por projeto, quais padrões/features estão
explicitamente linkados em qualquer arquivo do projeto.

Bloco delimitado preserva células manuais. Substitui apenas o conteúdo
entre `<!-- AUTO-MATRIX:start -->` e `<!-- AUTO-MATRIX:end -->`.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

VAULT_ROOT = Path(__file__).resolve().parents[3]
PATTERNS_DIR = VAULT_ROOT / "_patterns"
FEATURES_DIR = VAULT_ROOT / "_features"
PROJECTS_DIR = VAULT_ROOT / "_knowledge" / "projects"

START_MARKER = "<!-- AUTO-MATRIX:start -->"
END_MARKER = "<!-- AUTO-MATRIX:end -->"
START_FEATURES = "<!-- AUTO-FEATURES:start -->"
END_FEATURES = "<!-- AUTO-FEATURES:end -->"

WIKILINK_RE = re.compile(r"\[\[([^\]]+)\]\]")


def list_slugs(path: Path) -> list[str]:
    return sorted(p.stem for p in path.glob("*.md") if p.name != "README.md")


def list_projects() -> list[str]:
    if not PROJECTS_DIR.exists():
        return []
    return sorted(d.name for d in PROJECTS_DIR.iterdir() if d.is_dir())


def collect_project_links(project_slug: str) -> tuple[set[str], set[str]]:
    """Retorna (patterns_linkados, features_linkados) varrendo todos os .md do projeto."""
    project_dir = PROJECTS_DIR / project_slug
    patterns: set[str] = set()
    features: set[str] = set()
    for md in project_dir.glob("*.md"):
        try:
            text = md.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        for m in WIKILINK_RE.finditer(text):
            target = m.group(1).split("|")[0].strip()
            if "_patterns/" in target:
                slug = target.split("_patterns/")[-1].split("/")[0]
                patterns.add(slug)
            elif "_features/" in target:
                slug = target.split("_features/")[-1].split("/")[0]
                features.add(slug)
    return patterns, features


def build_matrix(slugs: list[str], by_project: dict[str, set[str]]) -> list[str]:
    projects = sorted(by_project.keys())
    if not projects:
        projects = list_projects()

    header = "| Slug | " + " | ".join(projects) + " |"
    separator = "|" + "---|" * (len(projects) + 1)
    rows: list[str] = []
    for slug in slugs:
        cells: list[str] = []
        cells.append(f"[[../_patterns/{slug}\\|{slug}]]" if (PATTERNS_DIR / f"{slug}.md").exists() else f"[[../_features/{slug}\\|{slug}]]")
        for proj in projects:
            cells.append("✓" if slug in by_project.get(proj, set()) else "—")
        rows.append("| " + " | ".join(cells) + " |")

    return [header, separator, *rows]


def replace_block(text: str, start_marker: str, end_marker: str, new_block: str) -> str:
    if start_marker in text and end_marker in text:
        before = text.split(start_marker, 1)[0]
        after = text.split(end_marker, 1)[1]
        return f"{before}{start_marker}\n{new_block}\n{end_marker}{after}"
    # Append at end
    addition = f"\n\n{start_marker}\n{new_block}\n{end_marker}\n"
    return text.rstrip() + addition


def regenerate_pattern_matrix() -> None:
    pattern_slugs = list_slugs(PATTERNS_DIR)
    by_project_patterns: dict[str, set[str]] = {}
    for proj in list_projects():
        patterns, _ = collect_project_links(proj)
        by_project_patterns[proj] = patterns

    block_lines = [
        "## Auto-Generated Coverage (Pattern × Project)",
        "",
        "> Auto-gerado por `pattern-matrix-generator.sh`. Não editar manualmente entre os marcadores.",
        "> ✓ = padrão linkado em algum arquivo do projeto · — = não linkado",
        "",
        *build_matrix(pattern_slugs, by_project_patterns),
        "",
        f"_Patterns no vault: {len(pattern_slugs)} · Projetos: {len(by_project_patterns)}_",
    ]
    new_block = "\n".join(block_lines)

    matrix_path = VAULT_ROOT / "_index" / "PATTERN-MATRIX.md"
    text = matrix_path.read_text(encoding="utf-8") if matrix_path.exists() else ""
    new_text = replace_block(text, START_MARKER, END_MARKER, new_block)
    if new_text != text:
        matrix_path.write_text(new_text, encoding="utf-8")
        print(f"[matrix-gen] {matrix_path.relative_to(VAULT_ROOT)} atualizado", file=sys.stderr)
    else:
        print(f"[matrix-gen] {matrix_path.relative_to(VAULT_ROOT)} sem mudanças", file=sys.stderr)


def regenerate_feature_catalog() -> None:
    feature_slugs = list_slugs(FEATURES_DIR)
    by_project_features: dict[str, set[str]] = {}
    for proj in list_projects():
        _, features = collect_project_links(proj)
        by_project_features[proj] = features

    block_lines = [
        "## Auto-Generated Coverage (Feature × Project)",
        "",
        "> Auto-gerado por `pattern-matrix-generator.sh`. Não editar manualmente entre os marcadores.",
        "> ✓ = feature linkado em algum arquivo do projeto",
        "",
        *build_matrix(feature_slugs, by_project_features),
        "",
        f"_Features no vault: {len(feature_slugs)} · Projetos: {len(by_project_features)}_",
    ]
    new_block = "\n".join(block_lines)

    catalog_path = VAULT_ROOT / "_index" / "FEATURE-CATALOG.md"
    text = catalog_path.read_text(encoding="utf-8") if catalog_path.exists() else ""
    new_text = replace_block(text, START_FEATURES, END_FEATURES, new_block)
    if new_text != text:
        catalog_path.write_text(new_text, encoding="utf-8")
        print(f"[matrix-gen] {catalog_path.relative_to(VAULT_ROOT)} atualizado", file=sys.stderr)
    else:
        print(f"[matrix-gen] {catalog_path.relative_to(VAULT_ROOT)} sem mudanças", file=sys.stderr)


def main() -> int:
    regenerate_pattern_matrix()
    regenerate_feature_catalog()
    return 0


if __name__ == "__main__":
    sys.exit(main())
