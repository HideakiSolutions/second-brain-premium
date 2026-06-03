#!/usr/bin/env python3
"""
concept_extractor — varre _decisions/, _learnings/ e gera CONCEPT-INDEX.md
agregado, listando todos os conceitos referenciados em cada documento.

Reusa o dicionário canônico de auto_linker.
"""

from __future__ import annotations

import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from auto_linker import (  # type: ignore[import]
    VAULT_ROOT,
    Concept,
    build_dictionary,
    split_protected_regions,
    _word_boundary_pattern,
)


def extract_concepts(text: str, concepts: list[Concept]) -> list[str]:
    found: list[str] = []
    seen: set[str] = set()
    regions = split_protected_regions(text)
    for kind, chunk in regions:
        if kind != "plain":
            continue
        for c in concepts:
            if c.slug in seen:
                continue
            for alias in c.aliases:
                if _word_boundary_pattern(alias).search(chunk):
                    found.append(f"{c.kind}/{c.slug}")
                    seen.add(c.slug)
                    break
    return found


def collect_targets() -> list[Path]:
    out: list[Path] = []
    for sub in ("_decisions", "_learnings"):
        base = VAULT_ROOT / sub
        if base.exists():
            out.extend(sorted(p for p in base.glob("*.md") if p.name != "README.md"))
    return out


def main() -> int:
    concepts = build_dictionary()
    targets = collect_targets()

    by_doc: dict[str, list[str]] = {}
    by_concept: dict[str, list[str]] = defaultdict(list)

    for path in targets:
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        rel = str(path.relative_to(VAULT_ROOT))
        found = extract_concepts(text, concepts)
        if found:
            by_doc[rel] = found
            for c in found:
                by_concept[c].append(rel)

    # Emit CONCEPT-INDEX.md
    out_path = VAULT_ROOT / "_index" / "CONCEPT-INDEX.md"
    lines: list[str] = []
    lines.append("---")
    lines.append("tags: [index, concepts, generated]")
    lines.append("status: active")
    lines.append("generated: true")
    lines.append("source: .claude/scripts/lib/concept_extractor.py")
    lines.append("---")
    lines.append("")
    lines.append("# Concept Index")
    lines.append("")
    lines.append("> Auto-gerado. Não editar manualmente.")
    lines.append("> Lista conceitos canônicos (`_patterns/`, `_features/`, projetos) detectados em cada ADR e learning.")
    lines.append("")
    lines.append(f"**Documentos analisados:** {len(targets)}")
    lines.append(f"**Documentos com conceitos detectados:** {len(by_doc)}")
    lines.append(f"**Conceitos referenciados:** {len(by_concept)}")
    lines.append("")
    lines.append("## Por documento")
    lines.append("")
    for doc in sorted(by_doc.keys()):
        link_doc = doc.removesuffix(".md")
        lines.append(f"### [[../{link_doc}|{Path(doc).name}]]")
        lines.append("")
        for c in sorted(by_doc[doc]):
            kind, slug = c.split("/", 1)
            target = f"_{kind}/{slug}" if kind != "projects" else f"_knowledge/projects/{slug}/{slug}"
            lines.append(f"- [[../{target}|{slug}]] ({kind})")
        lines.append("")

    lines.append("## Por conceito (cross-reference)")
    lines.append("")
    for concept_key in sorted(by_concept.keys()):
        kind, slug = concept_key.split("/", 1)
        target = f"_{kind}/{slug}" if kind != "projects" else f"_knowledge/projects/{slug}/{slug}"
        lines.append(f"### [[../{target}|{slug}]] ({kind})")
        lines.append("")
        for doc in sorted(by_concept[concept_key]):
            link_doc = doc.removesuffix(".md")
            lines.append(f"- [[../{link_doc}|{Path(doc).name}]]")
        lines.append("")

    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"[concept-extractor] {len(by_doc)} docs, {len(by_concept)} concepts → {out_path.relative_to(VAULT_ROOT)}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
