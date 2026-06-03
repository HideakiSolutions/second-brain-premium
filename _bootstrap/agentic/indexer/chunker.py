"""
chunker.py — chunker markdown-aware do vault.

Estratégia:
- Frontmatter YAML vira metadata (não vai pro corpus de embedding)
- Headings (## e ###) viram unidades de chunk (semantic boundaries)
- Chunks > 1500 chars são quebrados em parágrafos respeitando word boundaries
- Cada chunk carrega: text, heading_path (breadcrumb), tags, kind, project, source_file
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from pathlib import Path

MAX_CHARS = 1500
MIN_CHARS = 100   # chunks menores são consolidados com vizinho

CODE_FENCE_RE = re.compile(r"^(```|~~~)")
HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*$")
WIKILINK_RE = re.compile(r"\[\[([^\]]+)\]\]")


@dataclass
class Chunk:
    chunk_id: str               # hash determinístico
    source_file: str            # path relativo ao vault
    heading_path: str           # ex: "Cambio Real > Padrões Aplicados"
    text: str                   # corpo do chunk
    kind: str                   # patterns | features | decisions | learnings | projects | content | infra | index | source | memory | other
    project: str | None         # se kind==projects
    tags: list[str] = field(default_factory=list)
    wikilinks: list[str] = field(default_factory=list)
    char_count: int = 0


def _categorize(rel_path: str) -> tuple[str, str | None]:
    """Retorna (kind, project_slug)."""
    parts = rel_path.split("/")
    if not parts:
        return ("other", None)
    head = parts[0]
    mapping = {
        "_patterns": "patterns",
        "_features": "features",
        "_decisions": "decisions",
        "_learnings": "learnings",
        "_cores": "cores",
        "_index": "index",
        "_content": "content",
        "_infrastructure": "infra",
        "_sources": "source",
        "_memory": "memory",
        "_sessions": "session",
        "_pipeline": "pipeline",
        "_prompts": "prompt",
    }
    if head in mapping:
        return (mapping[head], None)
    if head == "_knowledge" and len(parts) >= 3 and parts[1] == "projects":
        return ("projects", parts[2])
    return ("other", None)


def _parse_frontmatter(text: str) -> tuple[dict, str]:
    """Retorna (metadata, body_without_frontmatter)."""
    if not text.startswith("---\n"):
        return ({}, text)
    end = text.find("\n---\n", 4)
    if end == -1:
        return ({}, text)
    fm: dict = {}
    for line in text[4:end].splitlines():
        if ":" not in line:
            continue
        k, v = line.split(":", 1)
        fm[k.strip()] = v.strip()
    return (fm, text[end + 5 :])


def _parse_tags(value: str) -> list[str]:
    value = value.strip()
    if value.startswith("[") and value.endswith("]"):
        inner = value[1:-1]
        return [t.strip().strip('"').strip("'") for t in inner.split(",") if t.strip()]
    return [t.strip() for t in value.split(",") if t.strip()]


def _strip_code_blocks(body: str) -> str:
    """Mantém apenas prosa (code blocks viram '<code-fence>')."""
    out: list[str] = []
    in_code = False
    for line in body.split("\n"):
        if CODE_FENCE_RE.match(line):
            in_code = not in_code
            if not in_code:
                out.append("[code]")
            continue
        if in_code:
            continue
        out.append(line)
    return "\n".join(out)


def _split_by_size(text: str, max_chars: int) -> list[str]:
    """Quebra texto em chunks ≤ max_chars respeitando parágrafos."""
    if len(text) <= max_chars:
        return [text.strip()] if text.strip() else []
    paras = re.split(r"\n\n+", text)
    chunks: list[str] = []
    buf = ""
    for p in paras:
        p = p.strip()
        if not p:
            continue
        if len(buf) + len(p) + 2 <= max_chars:
            buf = (buf + "\n\n" + p) if buf else p
        else:
            if buf:
                chunks.append(buf)
            if len(p) > max_chars:
                # quebra por sentenças
                sentences = re.split(r"(?<=[.!?])\s+", p)
                buf2 = ""
                for s in sentences:
                    if len(buf2) + len(s) + 1 <= max_chars:
                        buf2 = (buf2 + " " + s) if buf2 else s
                    else:
                        if buf2:
                            chunks.append(buf2)
                        buf2 = s
                buf = buf2
            else:
                buf = p
    if buf:
        chunks.append(buf)
    return chunks


def chunk_file(path: Path, vault_root: Path) -> list[Chunk]:
    """Quebra um arquivo .md em chunks com metadata."""
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return []

    rel = str(path.relative_to(vault_root))
    kind, project = _categorize(rel)
    fm, body = _parse_frontmatter(text)
    tags = _parse_tags(fm.get("tags", ""))
    if "status" in fm:
        # status é maturidade para fins de busca
        status = fm["status"].strip().strip('"').strip("'")
        if status and status not in tags:
            tags.append(f"status:{status}")

    body = _strip_code_blocks(body)
    wikilinks = WIKILINK_RE.findall(body)

    # H1 = título do doc
    h1 = ""
    m1 = re.search(r"^#\s+(.+)$", body, re.MULTILINE)
    if m1:
        h1 = m1.group(1).strip()

    chunks: list[Chunk] = []
    current_heading_stack: list[str] = []
    current_section_text: list[str] = []

    def flush_section(stack: list[str], text: str):
        if not text.strip():
            return
        heading_path = " > ".join([h1] + stack) if h1 else " > ".join(stack)
        if not heading_path:
            heading_path = path.stem
        for sub in _split_by_size(text, MAX_CHARS):
            if len(sub) < MIN_CHARS and chunks and len(chunks[-1].text) + len(sub) < MAX_CHARS:
                # consolida com chunk anterior se ambos pequenos
                chunks[-1].text += "\n\n" + sub
                chunks[-1].char_count = len(chunks[-1].text)
                continue
            chunk_id = hashlib.sha256(f"{rel}::{heading_path}::{sub[:200]}".encode()).hexdigest()[:32]
            chunks.append(Chunk(
                chunk_id=chunk_id,
                source_file=rel,
                heading_path=heading_path,
                text=sub,
                kind=kind,
                project=project,
                tags=tags,
                wikilinks=wikilinks,
                char_count=len(sub),
            ))

    for line in body.splitlines():
        m = HEADING_RE.match(line)
        if m and len(m.group(1)) >= 2:  # ## ou maior
            flush_section(current_heading_stack, "\n".join(current_section_text))
            current_section_text = []
            level = len(m.group(1)) - 2  # ## → 0, ### → 1
            current_heading_stack = current_heading_stack[:level]
            current_heading_stack.append(m.group(2).strip())
        else:
            current_section_text.append(line)

    flush_section(current_heading_stack, "\n".join(current_section_text))

    return chunks


def walk_vault(vault_root: Path) -> list[Path]:
    """Lista todos os .md indexáveis no vault."""
    SKIP = {".git", "node_modules", ".obsidian", ".second-brain", ".logs",
            "_references", "data", "__pycache__"}
    out: list[Path] = []
    for p in vault_root.rglob("*.md"):
        if any(part in SKIP for part in p.relative_to(vault_root).parts):
            continue
        out.append(p)
    return sorted(out)


if __name__ == "__main__":
    import sys
    root = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("$VAULT")
    files = walk_vault(root)
    total_chunks = 0
    for f in files:
        cs = chunk_file(f, root)
        total_chunks += len(cs)
    print(f"{len(files)} files → {total_chunks} chunks")
