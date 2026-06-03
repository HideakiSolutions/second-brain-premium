#!/usr/bin/env python3
"""
auto_linker — backlink builder determinístico para o vault second-brain.

Lê dicionário canônico de slugs em _patterns/, _features/, _decisions/, _learnings/
e _knowledge/projects/, e substitui a PRIMEIRA ocorrência de cada termo em prosa
(fora de code-blocks, frontmatter e WikiLinks existentes) por um WikiLink.

Idempotente: nunca duplica link, nunca toca dentro de codeblock ou link existente.
"""

from __future__ import annotations

import argparse
import os
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable

VAULT_ROOT = Path(__file__).resolve().parents[3]


# ---------- Dicionário canônico ----------

@dataclass(frozen=True)
class Alias:
    text: str
    case_sensitive: bool = False


@dataclass(frozen=True)
class Concept:
    slug: str          # filename sem .md
    kind: str          # patterns | features | decisions | learnings | projects
    aliases: tuple[Alias, ...]
    display: str       # texto exibido no link

    @property
    def target_dir(self) -> str:
        return f"_{self.kind}" if self.kind != "projects" else "_knowledge/projects"


# Aliases canônicos. Por padrão case-insensitive. Termos genéricos que
# colidem com nomes de tabela / variável / arquivo são marcados case-sensitive
# (ou substituídos por variantes multi-palavra mais específicas).
def _ci(*words: str) -> tuple[Alias, ...]:
    return tuple(Alias(w, case_sensitive=False) for w in words)


def _cs(*words: str) -> tuple[Alias, ...]:
    return tuple(Alias(w, case_sensitive=True) for w in words)


PATTERN_ALIASES: dict[str, tuple[Alias, ...]] = {
    "cqrs": _cs("CQRS"),
    "event-sourcing": _ci("Event Sourcing"),
    "event-driven-messaging": _ci("event-driven messaging", "event-driven architecture"),
    "hexagonal-architecture": _ci("Hexagonal Architecture", "ports and adapters"),
    "kyc-aml-compliance": _cs("KYC/AML", "KYC", "AML"),
    "multi-tenancy": _ci("multi-tenancy", "multi-tenant"),
    "outbox-inbox": _ci("Outbox/Inbox", "outbox pattern", "inbox pattern"),
    "saga-pattern": _ci("Saga Pattern"),
    "orleans-virtual-actors": _ci("Orleans Virtual Actors", "virtual actor"),
    "idempotency": _ci("idempotency", "idempotent"),
    "api-gateway": _ci("API Gateway"),
    "gitops-argocd": _cs("GitOps"),  # ArgoCD coberto pelo feature dedicado
    "double-entry-ledger": _ci("double-entry ledger"),
}

FEATURE_ALIASES: dict[str, tuple[Alias, ...]] = {
    "outbox-exactly-once": _ci("Outbox Exactly-Once", "outbox exactly once"),
    "double-entry-journal": _ci("Double-Entry Journal"),
    "trade-saga": _cs("TradeSaga", "Trade Saga"),
    "aml-risk-scoring": _ci("AML Risk Scoring"),
    "ctr-sar-auto-reporting": _cs("CTR/SAR Auto-Reporting", "CTR/SAR"),
    "ofac-sanctions-check": _cs("OFAC sanctions check"),
    "rabbitmq-event-bus": _ci("RabbitMQ event bus"),
    "kafka-event-bus": _ci("Kafka event bus"),
    "kong-dbless-gateway": _ci("Kong DB-less"),
    "yarp-api-gateway": _ci("YARP API Gateway"),
    "marten-event-store": _ci("Marten event store"),
    "midaz-ledger-adapter": _cs("Midaz"),
    "redis-distributed-lock": _ci("distributed lock"),
    "redis-idempotency-keys": _ci("idempotency keys"),
    "kyc-document-verification": _ci("KYC document verification"),
    "lgpd-crypto-shredding": _ci("LGPD crypto-shredding", "crypto-shredding"),
    "external-secrets-operator": _cs("External Secrets Operator", "ExternalSecrets"),
    "argocd-app-of-apps": _ci("app-of-apps", "App of Apps"),
    "playwright-e2e-ephemeral": _ci("Playwright E2E"),
    "orleans-grain-per-aggregate": _ci("grain per aggregate"),
    "orleans-saga-manager": _ci("Orleans saga manager"),
    "orleans-reminder-compliance": _ci("Orleans reminders"),
    "inbox-idempotent-consumer": _ci("Inbox idempotent consumer", "inbox consumer"),
    "multi-tenant-header-propagation": _ci("tenant header propagation"),
    "multi-tenant-schema-isolation": _ci("schema-per-tenant", "schema isolation"),
    "keycloak-realm-per-tenant": _ci("realm per tenant"),
    "kustomize-overlay-strategy": _ci("Kustomize overlays"),
    "llm-pipeline-vs-orchestrator": _ci("LLM pipeline vs orchestrator"),
    "redis-session-cache": _ci("Redis session cache"),
    "gin-index-dedup": _ci("GIN index dedup"),
}


def _slug_from_filename(fn: str) -> str:
    return fn.removesuffix(".md")


def _read_h1(path: Path) -> str:
    try:
        with path.open(encoding="utf-8") as fh:
            in_fm = False
            fm_count = 0
            for line in fh:
                line = line.rstrip("\n")
                if line == "---":
                    fm_count += 1
                    in_fm = fm_count == 1
                    if fm_count >= 2:
                        in_fm = False
                    continue
                if in_fm:
                    continue
                if line.startswith("# "):
                    return line[2:].strip()
    except OSError:
        pass
    return _slug_from_filename(path.name).replace("-", " ").title()


def build_dictionary() -> list[Concept]:
    concepts: list[Concept] = []

    patterns_dir = VAULT_ROOT / "_patterns"
    for p in sorted(patterns_dir.glob("*.md")):
        slug = _slug_from_filename(p.name)
        display = _read_h1(p).split(" — ")[0].split(" (")[0]
        aliases = PATTERN_ALIASES.get(slug)
        if aliases is None:
            aliases = _ci(display)
        concepts.append(Concept(slug=slug, kind="patterns", aliases=aliases, display=display))

    features_dir = VAULT_ROOT / "_features"
    for p in sorted(features_dir.glob("*.md")):
        slug = _slug_from_filename(p.name)
        display = _read_h1(p).split(" — ")[0].split(" (")[0]
        aliases = FEATURE_ALIASES.get(slug)
        if aliases is None:
            aliases = _ci(display)
        concepts.append(Concept(slug=slug, kind="features", aliases=aliases, display=display))

    projects_dir = VAULT_ROOT / "_knowledge" / "projects"
    if projects_dir.exists():
        for d in sorted(projects_dir.iterdir()):
            if not d.is_dir():
                continue
            slug = d.name
            primary = d / f"{slug}.md"
            if not primary.exists():
                continue
            display = _read_h1(primary)
            # Projetos: display name (case-insensitive) + slug (case-sensitive
            # para evitar match em prosa genérica como "axon" minúsculo).
            aliases = (Alias(display, False), Alias(slug, True))
            concepts.append(Concept(slug=slug, kind="projects", aliases=aliases, display=display))

    return concepts


# ---------- Parsing markdown ----------

CODE_FENCE_RE = re.compile(r"^(```|~~~)")
WIKILINK_RE = re.compile(r"\[\[[^\]]+\]\]")
INLINE_CODE_RE = re.compile(r"`[^`\n]+`")


def split_protected_regions(text: str) -> list[tuple[str, str]]:
    """Quebra texto em regiões. Tipos: 'frontmatter', 'codeblock', 'inline_code',
    'wikilink', 'plain'. Apenas 'plain' é candidato a substituição."""
    out: list[tuple[str, str]] = []

    # 1. frontmatter: se começa com '---\n', captura até segundo '---\n'
    if text.startswith("---\n"):
        end = text.find("\n---\n", 4)
        if end != -1:
            out.append(("frontmatter", text[: end + 5]))
            text = text[end + 5 :]
        else:
            out.append(("frontmatter", text))
            return out

    # 2. quebra por code-fence
    lines = text.split("\n")
    buf_plain: list[str] = []
    buf_code: list[str] = []
    in_code = False

    def flush_plain():
        if buf_plain:
            out.append(("plainblock", "\n".join(buf_plain) + "\n"))
            buf_plain.clear()

    def flush_code():
        if buf_code:
            out.append(("codeblock", "\n".join(buf_code) + "\n"))
            buf_code.clear()

    for line in lines:
        if CODE_FENCE_RE.match(line):
            if in_code:
                buf_code.append(line)
                flush_code()
                in_code = False
            else:
                flush_plain()
                buf_code.append(line)
                in_code = True
            continue
        if in_code:
            buf_code.append(line)
        else:
            buf_plain.append(line)

    if in_code:
        flush_code()
    else:
        flush_plain()

    # 3. dentro de plainblocks, separar inline code e wikilinks
    refined: list[tuple[str, str]] = []
    for kind, chunk in out:
        if kind != "plainblock":
            refined.append((kind, chunk))
            continue
        i = 0
        while i < len(chunk):
            m_link = WIKILINK_RE.search(chunk, i)
            m_code = INLINE_CODE_RE.search(chunk, i)
            candidates = [m for m in (m_link, m_code) if m]
            if not candidates:
                refined.append(("plain", chunk[i:]))
                break
            m = min(candidates, key=lambda m: m.start())
            if m.start() > i:
                refined.append(("plain", chunk[i : m.start()]))
            kind2 = "wikilink" if m is m_link else "inline_code"
            refined.append((kind2, m.group(0)))
            i = m.end()

    return refined


def join_regions(regions: Iterable[tuple[str, str]]) -> str:
    return "".join(chunk for _, chunk in regions)


# ---------- Substituição ----------

def relative_link_path(file_path: Path, concept: Concept) -> str:
    rel = os.path.relpath(VAULT_ROOT, start=file_path.parent)
    target_dir = concept.target_dir
    if concept.kind == "projects":
        slug = concept.slug
        return f"{rel}/{target_dir}/{slug}/{slug}"
    return f"{rel}/{target_dir}/{concept.slug}"


def _word_boundary_pattern(alias: Alias) -> re.Pattern[str]:
    escaped = re.escape(alias.text)
    if alias.text[0].isalnum():
        # Não permitir prefixo letra/dígito/_/-
        prefix = r"(?<![A-Za-z0-9_\-])"
    else:
        prefix = r"(?<![A-Za-z0-9_])"
    # Sufixo: nunca permitir letra, dígito, _ ou . (para evitar filename.ext)
    # mas — pode aparecer em final de pontuação, então só rejeitamos identifier-like.
    suffix = r"(?![A-Za-z0-9_\.])"
    flags = 0 if alias.case_sensitive else re.IGNORECASE
    return re.compile(prefix + escaped + suffix, flags)


def apply_links(text: str, file_path: Path, concepts: list[Concept]) -> tuple[str, list[str]]:
    regions = split_protected_regions(text)
    applied: list[str] = []

    # Self-link guard: detecta projeto auto-referenciado.
    self_slug = _slug_from_filename(file_path.name)
    self_project_slug: str | None = None
    try:
        rel_parts = file_path.resolve().relative_to(VAULT_ROOT).parts
        if len(rel_parts) >= 3 and rel_parts[0] == "_knowledge" and rel_parts[1] == "projects":
            self_project_slug = rel_parts[2]
    except ValueError:
        pass

    new_regions: list[tuple[str, str]] = []
    already_linked: set[str] = set()

    # Pre-scan: collect concepts already linked anywhere (any alias)
    full_text = text
    for c in concepts:
        rel = relative_link_path(file_path, c)
        if f"[[{rel}" in full_text:
            already_linked.add(c.slug)

    # Walk regions
    for kind, chunk in regions:
        if kind != "plain":
            new_regions.append((kind, chunk))
            continue

        new_chunk = chunk
        for c in concepts:
            if c.slug in already_linked:
                continue
            if c.slug == self_slug:
                continue
            if c.kind == "projects" and self_project_slug == c.slug:
                continue
            rel = relative_link_path(file_path, c)
            for alias in c.aliases:
                pat = _word_boundary_pattern(alias)
                m = pat.search(new_chunk)
                if not m:
                    continue
                matched_text = m.group(0)
                replacement = f"[[{rel}|{matched_text}]]"
                new_chunk = new_chunk[: m.start()] + replacement + new_chunk[m.end() :]
                already_linked.add(c.slug)
                applied.append(f"{c.kind}/{c.slug} ({matched_text})")
                break

        new_regions.append((kind, new_chunk))

    return join_regions(new_regions), applied


# ---------- CLI ----------

def is_target_file(path: Path) -> bool:
    rel = path.relative_to(VAULT_ROOT)
    parts = rel.parts
    if not parts or not path.name.endswith(".md"):
        return False
    if parts[0] == "_knowledge" and len(parts) >= 3 and parts[1] == "projects":
        return True
    if parts[0] in {"_decisions", "_learnings", "_cores"}:
        return True
    if parts[0] == "_content" and len(parts) >= 2 and parts[1] == "articles":
        return True
    return False


def collect_targets(scope: str | None) -> list[Path]:
    if scope:
        s = (VAULT_ROOT / scope).resolve()
        if s.is_file():
            return [s] if is_target_file(s) else []
        if s.is_dir():
            return sorted(p for p in s.rglob("*.md") if is_target_file(p))
        return []

    out: list[Path] = []
    for sub in ("_knowledge/projects", "_decisions", "_learnings", "_cores", "_content/articles"):
        base = VAULT_ROOT / sub
        if base.exists():
            out.extend(sorted(p for p in base.rglob("*.md") if is_target_file(p)))
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description="auto-linker determinístico para o vault second-brain")
    ap.add_argument("--apply", action="store_true", help="aplicar mudanças (default: dry-run)")
    ap.add_argument("--scope", help="caminho relativo ao vault (arquivo ou pasta) — limita escopo")
    ap.add_argument("--quiet", action="store_true", help="reduz output")
    args = ap.parse_args()

    concepts = build_dictionary()
    if not args.quiet:
        print(f"[auto-linker] {len(concepts)} conceitos no dicionário", file=sys.stderr)

    targets = collect_targets(args.scope)
    if not args.quiet:
        print(f"[auto-linker] {len(targets)} arquivos no escopo", file=sys.stderr)

    total_applied = 0
    files_changed = 0

    for path in targets:
        try:
            original = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue

        new_text, applied = apply_links(original, path, concepts)
        if applied:
            files_changed += 1
            total_applied += len(applied)
            if not args.quiet:
                rel = path.relative_to(VAULT_ROOT)
                print(f"  + {rel}: {len(applied)} link(s) — {', '.join(applied)}")
            if args.apply and new_text != original:
                path.write_text(new_text, encoding="utf-8")

    mode = "APPLY" if args.apply else "DRY-RUN"
    print(f"[auto-linker] [{mode}] {files_changed} arquivo(s) tocado(s), {total_applied} link(s) novo(s)", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
