#!/usr/bin/env python3
"""
post_tool_use_validator — invocado pelo hook PostToolUse do Claude Code.

Lê JSON de stdin (CLAUDE_TOOL_OUTPUT format), extrai tool_input.file_path.
Se path está em _knowledge/projects/*/, _patterns/, _features/, _decisions/,
_learnings/, _cores/, _index/ — valida frontmatter (taxonomia + datas) e,
para arquivos de projeto, presença de seções obrigatórias.

Modos via env:
  LINT_STRICT=0  → warnings em stderr, exit 0 (default — primeiros 7 dias)
  LINT_STRICT=1  → bloqueia (exit 2) se violação crítica
"""

from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

VAULT_ROOT = Path(os.environ.get("VAULT_ROOT") or os.environ.get("VAULT") or Path(__file__).resolve().parents[3]).resolve()
TAXONOMY_PATH = VAULT_ROOT / "_index" / "TAG-TAXONOMY.md"

LAYER_TAGS = {
    "pattern", "feature", "decision", "learning", "project", "core",
    "infra", "content", "source", "index", "memory", "session", "wiki",
}
MATURITY_TAGS = {
    "production", "beta", "mvp", "spike", "candidate",
    "deprecated", "archived", "active", "wip",
}
DOMAIN_TAGS = {
    "fintech", "trading", "payments", "compliance", "ai-sdlc", "ai-agents",
    "infra-eng", "devtools", "knowledge-mgmt", "observability", "security",
    "data-platform", "messaging", "frontend", "backend", "mobile", "platform",
    "governance", "forex", "crypto", "events", "automation", "voice-text",
    "architecture", "mandatory",  # legacy frontmatter
}

PROJECT_FILE_TYPES = {"work-log", "decisions", "gotchas", "roadmap", "state",
                      "modules", "integrations", "agents", "skills", "workflows",
                      "servers", "policies", "structure", "index"}

CRITICAL_FOR_TEMPLATE = {"state", "decisions", "gotchas", "modules", "index"}


def parse_frontmatter(text: str) -> dict | None:
    if not text.startswith("---\n"):
        return None
    end = text.find("\n---\n", 4)
    if end == -1:
        return None
    fm_text = text[4:end]
    fm: dict = {}
    for line in fm_text.splitlines():
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        fm[key.strip()] = value.strip()
    return fm


def parse_tags(value: str) -> list[str]:
    value = value.strip()
    if value.startswith("[") and value.endswith("]"):
        inner = value[1:-1]
        return [t.strip().strip('"').strip("'") for t in inner.split(",") if t.strip()]
    return [t.strip() for t in value.split(",") if t.strip()]


def section_present(text: str, heading: str) -> bool:
    pattern = re.compile(rf"^##\s+{re.escape(heading)}\s*$", re.MULTILINE)
    return bool(pattern.search(text))


def count_links_in_section(text: str, heading: str) -> int:
    pattern = re.compile(
        rf"^##\s+{re.escape(heading)}\s*$\n(.*?)(?=^##\s|\Z)",
        re.MULTILINE | re.DOTALL,
    )
    m = pattern.search(text)
    if not m:
        return 0
    body = m.group(1)
    return len(re.findall(r"\[\[[^\]]+\]\]", body))


def is_vault_target(path: Path) -> str | None:
    """Retorna a categoria do arquivo no vault, ou None se fora do escopo."""
    try:
        rel = path.resolve().relative_to(VAULT_ROOT)
    except ValueError:
        return None
    parts = rel.parts
    if not parts or not path.name.endswith(".md"):
        return None
    if parts[0] == "_knowledge" and len(parts) >= 3 and parts[1] == "projects":
        return f"project:{path.stem}"
    if parts[0] in {"_patterns", "_features", "_decisions", "_learnings", "_cores"}:
        return parts[0][1:]
    if parts[0] in {"_index", "_memory", "_content", "_infrastructure"}:
        return parts[0][1:]
    return None


def validate_file(path: Path, category: str) -> tuple[list[str], list[str]]:
    """Retorna (warnings, errors)."""
    warnings: list[str] = []
    errors: list[str] = []

    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        return ([], [f"unreadable: {exc}"])

    fm = parse_frontmatter(text)
    if fm is None:
        errors.append("frontmatter ausente ou inválido")
        return (warnings, errors)

    if "tags" not in fm:
        errors.append("frontmatter sem 'tags'")
    else:
        tags = parse_tags(fm["tags"])
        layer_hits = [t for t in tags if t in LAYER_TAGS]
        maturity_hits = [t for t in tags if t in MATURITY_TAGS]
        domain_hits = [t for t in tags if t in DOMAIN_TAGS]
        if not layer_hits:
            errors.append(f"tags sem camada (esperado 1 de {sorted(LAYER_TAGS)[:5]}…)")
        elif len(layer_hits) > 1:
            errors.append(f"tags com múltiplas camadas: {layer_hits}")
        if not maturity_hits and fm.get("status", "").strip() not in MATURITY_TAGS:
            warnings.append("tags ou status sem maturidade (production/beta/mvp/active/...)")
        elif len(maturity_hits) > 1:
            warnings.append(f"tags com múltiplas maturidades: {maturity_hits}")
        if not domain_hits and category.startswith("project:"):
            warnings.append("tags sem domínio (esperado ≥1 de fintech/ai-sdlc/...)")
        # Tags livres adicionais são permitidas — não validamos contra um whitelist.

    if "status" not in fm:
        warnings.append("frontmatter sem 'status'")

    # Templates obrigatórios para arquivos críticos de projeto
    if category.startswith("project:"):
        stem = path.stem
        if stem in CRITICAL_FOR_TEMPLATE or stem == path.parent.name:
            if not section_present(text, "Padrões Aplicados"):
                warnings.append("seção '## Padrões Aplicados' ausente")
            else:
                links = count_links_in_section(text, "Padrões Aplicados")
                if links < 2:
                    warnings.append(f"seção 'Padrões Aplicados' tem {links} link(s); mínimo 2")
            if stem in {"index", path.parent.name, "modules"}:
                if not section_present(text, "Features Reutilizadas"):
                    warnings.append("seção '## Features Reutilizadas' ausente")
            if stem in {"decisions", "gotchas"}:
                if not section_present(text, "Decisões Relacionadas"):
                    warnings.append("seção '## Decisões Relacionadas' ausente")

    return (warnings, errors)


def main() -> int:
    raw = sys.stdin.read()
    try:
        payload = json.loads(raw) if raw.strip() else {}
    except json.JSONDecodeError:
        return 0

    tool_name = payload.get("tool_name") or payload.get("tool", "")
    tool_input = payload.get("tool_input", {})
    file_path_raw = tool_input.get("file_path") or tool_input.get("path") or ""
    if not file_path_raw:
        return 0

    path = Path(file_path_raw)
    category = is_vault_target(path)
    if category is None:
        return 0

    warnings, errors = validate_file(path, category)
    if not warnings and not errors:
        return 0

    rel = path.resolve().relative_to(VAULT_ROOT) if path.is_absolute() else path
    print(f"[vault-lint] {rel} (via {tool_name})", file=sys.stderr)
    for e in errors:
        print(f"  ERROR: {e}", file=sys.stderr)
    for w in warnings:
        print(f"  warn:  {w}", file=sys.stderr)

    if os.environ.get("LINT_STRICT") == "1" and errors:
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
