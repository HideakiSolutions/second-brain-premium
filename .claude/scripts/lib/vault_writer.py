#!/usr/bin/env python3
"""
vault_writer — CLI de escrita normalizada no vault.

Substitui em escala MCP-server: opera local, com convenções padronizadas.
Tools (subcomandos):
  append-work-log   → adiciona linha em _knowledge/projects/<X>/work-log.md
  append-activity   → adiciona linha em _memory/activity-log.md
  update-state      → patch em _knowledge/projects/<X>/state.md (campos do front-matter)
  create-decision   → arquivo em _decisions/YYYY-MM-DD-<slug>.md
  append-gotcha     → cria entrada em _knowledge/projects/<X>/gotchas/ e atualiza manifesto
  append-project-decision → cria entrada em _knowledge/projects/<X>/decisions/ e atualiza manifesto

Idempotência: cada comando aceita --event-id <hash>; se o hash já estiver no
índice de dedup, a operação é skipada.
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import re
import sqlite3
import sys
import unicodedata
from pathlib import Path

VAULT_ROOT = Path(__file__).resolve().parents[3]
DEDUP_DB = VAULT_ROOT / "_memory" / ".events" / "dedup.db"
DEDUP_DB.parent.mkdir(parents=True, exist_ok=True)


def dedup_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DEDUP_DB)
    conn.execute(
        "CREATE TABLE IF NOT EXISTS events ("
        "  event_id TEXT PRIMARY KEY,"
        "  op TEXT NOT NULL,"
        "  target TEXT,"
        "  timestamp TEXT NOT NULL"
        ")"
    )
    return conn


def claim_event(event_id: str, op: str, target: str = "") -> bool:
    """Retorna True se o evento foi reclamado agora; False se já existia."""
    if not event_id:
        return True
    conn = dedup_conn()
    try:
        conn.execute(
            "INSERT INTO events(event_id, op, target, timestamp) VALUES (?, ?, ?, ?)",
            (event_id, op, target, dt.datetime.now().isoformat()),
        )
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()


def hash_payload(*parts: str) -> str:
    h = hashlib.sha256()
    for p in parts:
        h.update(p.encode("utf-8"))
        h.update(b"\x1f")
    return h.hexdigest()[:16]


def slugify(value: str) -> str:
    value = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")
    value = re.sub(r"`([^`]+)`", r"\1", value.lower())
    value = re.sub(r"\[\[([^]|]+)(?:\|([^]]+))?\]\]", lambda m: m.group(2) or m.group(1).split("/")[-1], value)
    value = re.sub(r"[^a-z0-9]+", "-", value).strip("-")
    return value[:72].strip("-") or "entry"


def first_line_summary(text: str) -> str:
    for line in text.splitlines():
        line = line.strip(" -")
        if not line or line.startswith("|"):
            continue
        line = re.sub(r"\*\*([^*]+):\*\*", r"\1:", line)
        return re.sub(r"\s+", " ", line)[:150]
    return "Sem resumo registrado."


def update_project_manifest(manifest: Path, kind: str, slug: str, title: str, date: str, summary: str) -> None:
    text = manifest.read_text(encoding="utf-8") if manifest.exists() else ""
    link = f"[[{kind}/{slug}|{title}]]"
    recent_line = f"- {link} — {summary}"
    archive_line = f"- {date}: {link}"

    def replace_section(src: str, heading: str, lines: list[str], cap: int | None = None) -> str:
        pattern = rf"(## {re.escape(heading)}\n\n)(.*?)(?=\n## |\Z)"
        match = re.search(pattern, src, flags=re.S)
        existing: list[str] = []
        if match:
            existing = [ln for ln in match.group(2).strip().splitlines() if ln.strip()]
        merged = lines + [ln for ln in existing if link not in ln and "Nenhuma entrada detalhada" not in ln]
        if cap:
            merged = merged[:cap]
        body = "\n".join(merged) if merged else "- Nenhuma entrada detalhada registrada."
        if match:
            return src[: match.start()] + match.group(1) + body + "\n" + src[match.end() :]
        suffix = f"\n\n## {heading}\n\n{body}\n"
        rel = src.find("\n## Related")
        return src[:rel] + suffix + src[rel:] if rel != -1 else src.rstrip() + suffix

    text = replace_section(text, "Entradas Ativas e Recentes", [recent_line], cap=10)
    text = replace_section(text, "Arquivo Completo", [archive_line], cap=None)
    manifest.write_text(text.rstrip() + "\n", encoding="utf-8")


def create_project_note(project: str, kind: str, title: str, body: str, date: str | None = None, status: str = "active") -> Path:
    today = dt.date.today().isoformat()
    note_date = date or today
    project_dir = VAULT_ROOT / "_knowledge" / "projects" / project
    manifest = project_dir / f"{kind}.md"
    out_dir = project_dir / kind
    out_dir.mkdir(parents=True, exist_ok=True)

    slug_base = slugify(f"{note_date}-{title}")
    slug = slug_base
    n = 2
    while (out_dir / f"{slug}.md").exists():
        slug = f"{slug_base}-{n}"
        n += 1

    note_path = out_dir / f"{slug}.md"
    singular = kind[:-1] if kind.endswith("s") else kind
    content = "\n".join([
        "---",
        f"tags: [project, {kind}, {project}]",
        f"status: {status}",
        f"created: {note_date}",
        f"updated: {today}",
        f"project: {project}",
        f"{singular}_date: {note_date}",
        "---",
        "",
        f"# {title}",
        "",
        f"> Projeto: [[../{project}|{project}]] · Manifesto: [[../{kind}|{kind}.md]]",
        "",
        body.strip(),
        "",
        "## Related",
        "",
        f"- [[../{project}|{project}]]",
        f"- [[../{kind}|{kind}.md]]",
        "",
    ])
    note_path.write_text(content, encoding="utf-8")
    update_project_manifest(manifest, kind, slug, title, note_date, first_line_summary(body))
    return note_path


# ---------- subcomandos ----------

def append_work_log(args: argparse.Namespace) -> int:
    proj = args.project
    work_log = VAULT_ROOT / "_knowledge" / "projects" / proj / "work-log.md"
    if not work_log.exists():
        print(f"[vault-writer] work-log inexistente: {work_log}", file=sys.stderr)
        return 1

    today = args.date or dt.date.today().isoformat()
    event_id = args.event_id or hash_payload("work-log", proj, today, args.type, args.description)
    if not claim_event(event_id, "append-work-log", str(work_log.relative_to(VAULT_ROOT))):
        if not args.quiet:
            print(f"[vault-writer] dedup: event {event_id} já registrado")
        return 0

    text = work_log.read_text(encoding="utf-8")

    # Detectar tabela existente (header com pipes) ou usar formato append simples
    new_line = (
        f"| {today} | {args.type} | {args.description} | {args.epic_id or '—'} | "
        f"{args.status or 'concluído'} |"
    )

    # Apenas append idempotente — se a linha exata já existe, skip
    if new_line in text:
        if not args.quiet:
            print(f"[vault-writer] linha já presente, skip")
        return 0

    suffix_marker = args.suffix or ""
    if suffix_marker:
        new_line += f" {suffix_marker}"

    work_log.write_text(text.rstrip() + "\n" + new_line + "\n", encoding="utf-8")
    if not args.quiet:
        print(f"[vault-writer] +1 linha em {work_log.relative_to(VAULT_ROOT)}")
    return 0


def append_activity(args: argparse.Namespace) -> int:
    log = VAULT_ROOT / "_memory" / "activity-log.md"
    timestamp = args.timestamp or dt.datetime.now().strftime("%Y-%m-%d %H:%M")
    op = args.op
    proj = args.project or "—"
    desc = args.description

    event_id = args.event_id or hash_payload("activity", timestamp, op, proj, desc)
    if not claim_event(event_id, "append-activity", op):
        return 0

    suffix = " [auto]" if args.auto else ""
    line = f"## [{timestamp}] {op} | {proj} — {desc}{suffix}\n"

    text = log.read_text(encoding="utf-8") if log.exists() else "# Activity Log\n\n"
    if line in text:
        return 0
    log.write_text(text.rstrip() + "\n\n" + line, encoding="utf-8")
    if not args.quiet:
        print(f"[vault-writer] +1 entrada em activity-log.md")
    return 0


def update_state(args: argparse.Namespace) -> int:
    state = VAULT_ROOT / "_knowledge" / "projects" / args.project / "state.md"
    if not state.exists():
        print(f"[vault-writer] state inexistente: {state}", file=sys.stderr)
        return 1

    today = dt.date.today().isoformat()
    text = state.read_text(encoding="utf-8")

    # Atualiza campo "updated:" no frontmatter
    if text.startswith("---\n"):
        end = text.find("\n---\n", 4)
        if end != -1:
            fm = text[4:end]
            new_fm_lines: list[str] = []
            seen_updated = False
            for line in fm.splitlines():
                if line.startswith("updated:"):
                    new_fm_lines.append(f"updated: {today}")
                    seen_updated = True
                else:
                    new_fm_lines.append(line)
            if not seen_updated:
                new_fm_lines.append(f"updated: {today}")
            text = "---\n" + "\n".join(new_fm_lines) + "\n---\n" + text[end + 5 :]

    if args.next_step:
        text = re.sub(r"(\*\*Pr[óo]ximo passo:\*\*).*", rf"\1 {args.next_step}", text, count=1)
    if args.phase:
        text = re.sub(r"(\*\*Fase:\*\*).*", rf"\1 {args.phase}", text, count=1)

    state.write_text(text, encoding="utf-8")
    if not args.quiet:
        print(f"[vault-writer] {state.relative_to(VAULT_ROOT)} atualizado")
    return 0


def create_decision(args: argparse.Namespace) -> int:
    today = args.date or dt.date.today().isoformat()
    slug = re.sub(r"[^a-z0-9]+", "-", args.title.lower()).strip("-")
    out_path = VAULT_ROOT / "_decisions" / f"{today}-{slug}.md"

    event_id = args.event_id or hash_payload("decision", today, slug)
    if not claim_event(event_id, "create-decision", str(out_path.relative_to(VAULT_ROOT))):
        return 0

    if out_path.exists():
        if not args.quiet:
            print(f"[vault-writer] decisão já existe: {out_path.relative_to(VAULT_ROOT)}")
        return 0

    domain_tags = args.domain_tags or "governance"
    body = args.body or "_(sem corpo fornecido)_"

    out = [
        "---",
        f"tags: [decision, {domain_tags}]",
        "status: active",
        f"created: {today}",
        f"updated: {today}",
    ]
    if args.source_url:
        out.append(f"source: {args.source_url}")
    out.extend([
        "---",
        "",
        f"# {args.title}",
        "",
        body,
        "",
    ])
    if args.project:
        out.extend([
            "## Projetos relacionados",
            "",
            f"- [[../_knowledge/projects/{args.project}/{args.project}|{args.project}]]",
            "",
        ])

    out_path.write_text("\n".join(out), encoding="utf-8")
    if not args.quiet:
        print(f"[vault-writer] criado: {out_path.relative_to(VAULT_ROOT)}")
    return 0


def append_gotcha(args: argparse.Namespace) -> int:
    gotchas = VAULT_ROOT / "_knowledge" / "projects" / args.project / "gotchas.md"
    if not gotchas.exists():
        print(f"[vault-writer] gotchas inexistente: {gotchas}", file=sys.stderr)
        return 1

    today = dt.date.today().isoformat()
    event_id = args.event_id or hash_payload("gotcha", args.project, args.description)
    if not claim_event(event_id, "append-gotcha", str(gotchas.relative_to(VAULT_ROOT))):
        return 0

    severity = args.severity or "medium"
    title = args.title or args.description[:80]
    body = (
        f"**Severidade:** {severity}\n"
        f"**Status:** active\n\n"
        f"**O que acontece:** {args.description}\n"
    )
    note_path = create_project_note(args.project, "gotchas", title, body, date=today, status="active")
    if not args.quiet:
        print(f"[vault-writer] +1 gotcha em {note_path.relative_to(VAULT_ROOT)}")
    return 0


def append_project_decision(args: argparse.Namespace) -> int:
    decisions = VAULT_ROOT / "_knowledge" / "projects" / args.project / "decisions.md"
    if not decisions.exists():
        print(f"[vault-writer] decisions inexistente: {decisions}", file=sys.stderr)
        return 1

    today = args.date or dt.date.today().isoformat()
    event_id = args.event_id or hash_payload("project-decision", args.project, today, args.title, args.body or "")
    if not claim_event(event_id, "append-project-decision", str(decisions.relative_to(VAULT_ROOT))):
        return 0

    if args.body:
        body = args.body
    else:
        body = "\n".join([
            f"**Contexto:** {args.context or 'Não registrado.'}",
            f"**Decisão:** {args.decision or 'Não registrada.'}",
            f"**Consequências:** {args.consequences or 'Não registradas.'}",
            f"**Reversibilidade:** {args.reversibility or 'Não registrada.'}",
        ])
    note_path = create_project_note(args.project, "decisions", args.title, body, date=today, status="active")
    if not args.quiet:
        print(f"[vault-writer] +1 decisão local em {note_path.relative_to(VAULT_ROOT)}")
    return 0


# ---------- CLI ----------

def main() -> int:
    ap = argparse.ArgumentParser(prog="vault-writer", description="API normalizada de escrita no vault second-brain")
    ap.add_argument("--quiet", action="store_true")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("append-work-log")
    p.add_argument("--project", required=True)
    p.add_argument("--type", required=True, choices=["feat", "fix", "chore", "task", "story", "epic", "spike", "session"])
    p.add_argument("--description", required=True)
    p.add_argument("--epic-id")
    p.add_argument("--status")
    p.add_argument("--date")
    p.add_argument("--suffix", help="texto extra no fim da linha (ex: '[auto]')")
    p.add_argument("--event-id")
    p.set_defaults(func=append_work_log)

    p = sub.add_parser("append-activity")
    p.add_argument("--op", required=True, help="ex: session-end, auto-commit, auto-pr-merge, deploy")
    p.add_argument("--project")
    p.add_argument("--description", required=True)
    p.add_argument("--timestamp")
    p.add_argument("--auto", action="store_true", help="adiciona sufixo [auto]")
    p.add_argument("--event-id")
    p.set_defaults(func=append_activity)

    p = sub.add_parser("update-state")
    p.add_argument("--project", required=True)
    p.add_argument("--phase")
    p.add_argument("--next-step")
    p.set_defaults(func=update_state)

    p = sub.add_parser("create-decision")
    p.add_argument("--title", required=True)
    p.add_argument("--body")
    p.add_argument("--project")
    p.add_argument("--source-url")
    p.add_argument("--domain-tags", help="ex: 'fintech,compliance'")
    p.add_argument("--date")
    p.add_argument("--event-id")
    p.set_defaults(func=create_decision)

    p = sub.add_parser("append-gotcha")
    p.add_argument("--project", required=True)
    p.add_argument("--description", required=True)
    p.add_argument("--title")
    p.add_argument("--severity", choices=["low", "medium", "high", "critical"])
    p.add_argument("--event-id")
    p.set_defaults(func=append_gotcha)

    p = sub.add_parser("append-project-decision")
    p.add_argument("--project", required=True)
    p.add_argument("--title", required=True)
    p.add_argument("--body")
    p.add_argument("--context")
    p.add_argument("--decision")
    p.add_argument("--consequences")
    p.add_argument("--reversibility")
    p.add_argument("--date")
    p.add_argument("--event-id")
    p.set_defaults(func=append_project_decision)

    args = ap.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
