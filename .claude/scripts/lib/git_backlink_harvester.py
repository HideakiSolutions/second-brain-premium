#!/usr/bin/env python3
"""
git_backlink_harvester — para cada projeto registrado, lê commits do dia e
detecta padrões via heurísticas de path. Anota uma linha em work-log.md
listando padrões tocados (apenas se ainda não existir entrada equivalente).

Mapeamento repo→projeto: arquivo opcional `_infrastructure/repo-map.yaml`.
Sem ele, tenta `<projects-root>/<slug>` como heurística.
"""

from __future__ import annotations

import argparse
import datetime as dt
import re
import subprocess
import sys
from pathlib import Path

VAULT_ROOT = Path(__file__).resolve().parents[3]


# Mapeamento de regex de path → conceito canônico (slug em _patterns/_features/)
PATH_TO_CONCEPT: list[tuple[re.Pattern[str], str, str]] = [
    (re.compile(r"[Oo]utbox", re.I), "patterns", "outbox-inbox"),
    (re.compile(r"[Ii]nbox(?!Handler)", re.I), "patterns", "outbox-inbox"),
    (re.compile(r"[Ss]aga(?!Manager)", re.I), "patterns", "saga-pattern"),
    (re.compile(r"SagaManager", re.I), "features", "orleans-saga-manager"),
    (re.compile(r"[Gg]rain(?!Tests)", re.I), "patterns", "orleans-virtual-actors"),
    (re.compile(r"CommandHandler|QueryHandler", re.I), "patterns", "cqrs"),
    (re.compile(r"EventSourc|EventStore|EventStream", re.I), "patterns", "event-sourcing"),
    (re.compile(r"\bMarten\b"), "features", "marten-event-store"),
    (re.compile(r"Hexagonal|Ports[A-Z]?Adapters", re.I), "patterns", "hexagonal-architecture"),
    (re.compile(r"\bKYC\b|\bAML\b"), "patterns", "kyc-aml-compliance"),
    (re.compile(r"OFAC|Sanctions", re.I), "features", "ofac-sanctions-check"),
    (re.compile(r"CTRReport|SARReport|CTR_SAR", re.I), "features", "ctr-sar-auto-reporting"),
    (re.compile(r"Idempotency|IdempotencyKey", re.I), "patterns", "idempotency"),
    (re.compile(r"MultiTenan|TenantId", re.I), "patterns", "multi-tenancy"),
    (re.compile(r"Ledger|JournalEntry|DoubleEntry", re.I), "patterns", "double-entry-ledger"),
    (re.compile(r"DistributedLock", re.I), "features", "redis-distributed-lock"),
    (re.compile(r"argocd|app-of-apps", re.I), "features", "argocd-app-of-apps"),
    (re.compile(r"\.github/workflows|\.gitlab-ci", re.I), "patterns", "gitops-argocd"),
    (re.compile(r"\bRabbitMQ\b|amqp", re.I), "features", "rabbitmq-event-bus"),
    (re.compile(r"\bKafka\b"), "features", "kafka-event-bus"),
    (re.compile(r"\bKong\b"), "features", "kong-dbless-gateway"),
    (re.compile(r"\bYARP\b|ReverseProxy"), "features", "yarp-api-gateway"),
    (re.compile(r"playwright", re.I), "features", "playwright-e2e-ephemeral"),
]


def load_repo_map() -> dict[str, Path]:
    """Carrega _infrastructure/repo-map.yaml (formato simples key: value)."""
    repo_map_file = VAULT_ROOT / "_infrastructure" / "repo-map.yaml"
    out: dict[str, Path] = {}
    if not repo_map_file.exists():
        return out
    for line in repo_map_file.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and value:
            out[key] = Path(value)
    return out


def detect_repo_for_project(slug: str, repo_map: dict[str, Path]) -> Path | None:
    if slug in repo_map:
        return repo_map[slug]
    candidate = Path(f"<projects-root>/{slug}")
    if candidate.exists() and (candidate / ".git").exists():
        return candidate
    return None


def list_projects() -> list[str]:
    base = VAULT_ROOT / "_knowledge" / "projects"
    if not base.exists():
        return []
    return sorted(d.name for d in base.iterdir() if d.is_dir())


def git_files_changed(repo: Path, since: dt.datetime) -> set[str]:
    """Retorna paths relativos de arquivos modificados desde `since`."""
    iso = since.strftime("%Y-%m-%d %H:%M:%S")
    try:
        result = subprocess.run(
            ["git", "log", f"--since={iso}", "--name-only", "--pretty=format:"],
            cwd=str(repo),
            capture_output=True,
            text=True,
            timeout=15,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return set()
    files = {line.strip() for line in result.stdout.splitlines() if line.strip()}
    return files


def detect_concepts(files: set[str]) -> set[tuple[str, str]]:
    found: set[tuple[str, str]] = set()
    for f in files:
        for pat, kind, slug in PATH_TO_CONCEPT:
            if pat.search(f):
                found.add((kind, slug))
    return found


def append_to_worklog(slug: str, today: str, concepts: set[tuple[str, str]], dry_run: bool) -> bool:
    work_log = VAULT_ROOT / "_knowledge" / "projects" / slug / "work-log.md"
    if not work_log.exists():
        return False
    if not concepts:
        return False
    text = work_log.read_text(encoding="utf-8")
    marker = f"<!-- harvester:{today} -->"
    if marker in text:
        return False
    links: list[str] = []
    for kind, c_slug in sorted(concepts):
        rel = f"../../../_{kind}/{c_slug}"
        links.append(f"[[{rel}|{c_slug}]]")
    addition = f"\n{marker}\n→ {today} — Padrões tocados (auto): {' · '.join(links)}\n"
    new_text = text.rstrip() + "\n" + addition
    if not dry_run:
        work_log.write_text(new_text, encoding="utf-8")
    return True


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--days", type=int, default=1)
    ap.add_argument("--quiet", action="store_true")
    args = ap.parse_args()

    repo_map = load_repo_map()
    today = dt.date.today().isoformat()
    since = dt.datetime.now() - dt.timedelta(days=args.days)

    touched_projects = 0
    skipped = 0
    no_repo = 0

    for slug in list_projects():
        repo = detect_repo_for_project(slug, repo_map)
        if repo is None:
            no_repo += 1
            continue
        files = git_files_changed(repo, since)
        if not files:
            skipped += 1
            continue
        concepts = detect_concepts(files)
        if not concepts:
            skipped += 1
            continue
        ok = append_to_worklog(slug, today, concepts, dry_run=not args.apply)
        if ok:
            touched_projects += 1
            if not args.quiet:
                conc = ", ".join(f"{k}/{s}" for k, s in sorted(concepts))
                print(f"  + {slug}: {conc}")

    mode = "APPLY" if args.apply else "DRY-RUN"
    print(
        f"[git-backlink-harvester] [{mode}] {touched_projects} work-log(s) atualizado(s); "
        f"{skipped} sem mudanças relevantes; {no_repo} sem repo mapeado",
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
