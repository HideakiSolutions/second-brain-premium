#!/usr/bin/env python3
"""
event_router — processa fila de eventos JSONL em _memory/.events/in/,
classifica, deduplica, e escreve no vault via vault_writer.

Modos por tipo de evento (lidos de _infrastructure/capture-modes.yaml,
fallback para 'assisted' se ausente):
  auto      → escrita direta no destino canônico
  assisted  → escrita em _pipeline/inbox/auto-captures-YYYY-MM-DD.md (batch)
  guided    → notification + aguarda /review-captures (mesma pasta inbox)

Pode rodar em três modos:
  --watch   → daemon, processa novos arquivos em loop (5s polling)
  --once    → processa fila e sai (default — bom para cron 5min)
  --replay  → reprocessa eventos do dia (útil em desenvolvimento)

Eventos pré-definidos:
  commit, pr-merged, release, deploy, degraded, adr-created, file-touched
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

VAULT_ROOT = Path(__file__).resolve().parents[3]
EVENTS_IN = VAULT_ROOT / "_memory" / ".events" / "in"
EVENTS_RAW = VAULT_ROOT / "_memory" / ".events" / "raw"
EVENTS_PROCESSED = VAULT_ROOT / "_memory" / ".events" / "processed"
EVENTS_DLQ = VAULT_ROOT / "_memory" / ".events" / "dlq"
PIPELINE_INBOX = VAULT_ROOT / "_pipeline" / "inbox"
INFRA = VAULT_ROOT / "_infrastructure"

VAULT_WRITER = VAULT_ROOT / ".claude" / "scripts" / "vault-writer.sh"

DEFAULT_MODE = "assisted"


def load_yaml_simple(path: Path) -> dict:
    """Mini-parser YAML (key: value flat ou key:\n  k1: v1)."""
    if not path.exists():
        return {}
    out: dict = {}
    current_section = None
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip() or line.strip().startswith("#"):
            continue
        if not line.startswith(" ") and ":" in line:
            key, value = line.split(":", 1)
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            if value:
                out[key] = value
                current_section = None
            else:
                out[key] = {}
                current_section = key
        elif line.startswith("  ") and current_section and ":" in line:
            sub_key, sub_value = line.split(":", 1)
            out[current_section][sub_key.strip()] = sub_value.strip().strip('"').strip("'")
    return out


def load_capture_modes() -> dict:
    cfg = load_yaml_simple(INFRA / "capture-modes.yaml")
    overrides = cfg.get("overrides", {}) if isinstance(cfg.get("overrides"), dict) else {}
    return {
        "default": cfg.get("defaults", DEFAULT_MODE),
        "overrides": overrides,
    }


def load_repo_map() -> dict[str, str]:
    return load_yaml_simple(INFRA / "repo-map.yaml") or {}


def load_filters() -> dict:
    return load_yaml_simple(INFRA / "event-filters.yaml") or {}


def hash_event(event: dict) -> str:
    canonical = json.dumps(event, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:16]


def project_for_repo(repo_path: str, repo_map: dict[str, str]) -> str | None:
    norm = repo_path.rstrip("/")
    for key, value in repo_map.items():
        if value.rstrip("/") == norm:
            return key
        if key in norm:
            return key
    return None


def call_vault_writer(args: list[str]) -> int:
    try:
        result = subprocess.run(
            [str(VAULT_WRITER), *args],
            capture_output=True,
            text=True,
            timeout=15,
            check=False,
        )
        if result.returncode != 0:
            print(f"[router] vault-writer falhou: {result.stderr.strip()}", file=sys.stderr)
        return result.returncode
    except (OSError, subprocess.TimeoutExpired) as exc:
        print(f"[router] vault-writer erro: {exc}", file=sys.stderr)
        return 1


def write_to_inbox(event: dict, decision: str) -> Path:
    today = dt.date.today().isoformat()
    PIPELINE_INBOX.mkdir(parents=True, exist_ok=True)
    inbox_file = PIPELINE_INBOX / f"auto-captures-{today}.md"
    if not inbox_file.exists():
        header = f"---\ntags: [pipeline, knowledge-mgmt, active]\nstatus: active\ncreated: {today}\nupdated: {today}\n---\n\n# Auto-Captures — {today}\n\n> Eventos auto-capturados aguardando promoção via `/review-captures` ou `/end-session`.\n\n"
        inbox_file.write_text(header, encoding="utf-8")
    block = (
        f"## [{event.get('timestamp', dt.datetime.now().isoformat())}] "
        f"{event.get('type', 'event')} | {event.get('project', '—')} ({decision})\n\n"
        f"```json\n{json.dumps(event, indent=2, ensure_ascii=False)}\n```\n\n"
    )
    with inbox_file.open("a", encoding="utf-8") as fh:
        fh.write(block)
    return inbox_file


def classify_commit(event: dict, filters: dict) -> str | None:
    """Retorna o tipo conventional-commit ou None se filtrado."""
    msg = event.get("message", "")
    head = msg.splitlines()[0] if msg else ""
    m = re.match(r"^(\w+)(?:\([^)]+\))?(!)?:\s", head)
    if not m:
        return None
    ctype = m.group(1).lower()
    branch = event.get("branch", "")
    allowed_branches = (filters.get("allowed_branches") or "main,master,develop").split(",")
    if branch and not any(b.strip() == branch for b in allowed_branches):
        return None
    return ctype


def handle_commit(event: dict, mode: str, filters: dict) -> tuple[bool, str]:
    """Retorna (escrito_diretamente, motivo)."""
    ctype = classify_commit(event, filters)
    if ctype is None:
        return (False, "filtered")
    if ctype in {"chore", "docs", "test", "style"}:
        # Não-críticos sempre vão pra inbox (batch) — não escreve no work-log direto.
        write_to_inbox(event, "batch")
        return (False, "non-critical-type")

    project = event.get("project")
    if not project:
        return (False, "no-project")

    description = event.get("message", "")[:120]
    sha = event.get("sha", "")
    event_id = f"commit-{sha[:12]}" if sha else hash_event(event)

    if mode == "auto":
        rc = call_vault_writer([
            "append-work-log",
            "--project", project,
            "--type", ctype if ctype in {"feat", "fix", "chore", "task", "spike"} else "task",
            "--description", description,
            "--status", "concluído",
            "--suffix", "[auto]",
            "--event-id", event_id,
        ])
        if rc == 0:
            call_vault_writer([
                "append-activity",
                "--op", "auto-commit",
                "--project", project,
                "--description", description,
                "--auto",
                "--event-id", event_id,
            ])
            return (True, "written")
        return (False, "writer-failed")

    write_to_inbox(event, mode)
    return (False, "queued")


def handle_pr_merged(event: dict, mode: str, _filters: dict) -> tuple[bool, str]:
    project = event.get("project")
    pr_number = event.get("pr_number")
    title = event.get("title", "")
    if not project or not pr_number:
        return (False, "missing-fields")
    event_id = f"pr-{project}-{pr_number}"
    desc = f'PR #{pr_number} "{title}"'

    if mode == "auto":
        call_vault_writer([
            "append-work-log",
            "--project", project,
            "--type", "feat",
            "--description", desc,
            "--status", "merged",
            "--suffix", "[auto]",
            "--event-id", event_id,
        ])
        call_vault_writer([
            "append-activity",
            "--op", "auto-pr-merge",
            "--project", project,
            "--description", desc,
            "--auto",
            "--event-id", event_id,
        ])
        return (True, "written")
    write_to_inbox(event, mode)
    return (False, "queued")


def handle_deploy(event: dict, mode: str, _filters: dict) -> tuple[bool, str]:
    project = event.get("project") or "—"
    env = event.get("env", "unknown")
    if env != "prod" and mode == "auto":
        mode = "assisted"  # dev/hmg = não-auto
    desc = f"Deploy {env}: {event.get('message', '')[:100]}"
    event_id = hash_event(event)

    if mode == "auto":
        call_vault_writer([
            "append-activity",
            "--op", "auto-deploy",
            "--project", project,
            "--description", desc,
            "--auto",
            "--event-id", event_id,
        ])
        return (True, "written")
    write_to_inbox(event, mode)
    return (False, "queued")


def handle_adr_created(event: dict, mode: str, _filters: dict) -> tuple[bool, str]:
    project = event.get("project")
    title = event.get("title") or "decisão"
    body = event.get("body", "")
    source_url = event.get("source_url", "")
    event_id = hash_event(event)

    if mode == "auto":
        call_vault_writer([
            "create-decision",
            "--title", title,
            "--body", body[:1000],
            "--project", project or "",
            "--source-url", source_url,
            "--domain-tags", "governance",
            "--event-id", event_id,
        ])
        return (True, "written")
    write_to_inbox(event, mode)
    return (False, "queued")


def handle_degraded(event: dict, mode: str, _filters: dict) -> tuple[bool, str]:
    project = event.get("project") or "—"
    desc = f"ArgoCD degraded: {event.get('app', 'unknown')} — {event.get('message', '')[:100]}"
    event_id = hash_event(event)

    if project != "—" and mode == "auto":
        call_vault_writer([
            "append-gotcha",
            "--project", project,
            "--description", desc,
            "--severity", "high",
            "--event-id", event_id,
        ])
    call_vault_writer([
        "append-activity",
        "--op", "auto-degraded",
        "--project", project,
        "--description", desc,
        "--auto",
        "--event-id", event_id,
    ])
    return (True, "written")


HANDLERS = {
    "commit": handle_commit,
    "pr-merged": handle_pr_merged,
    "deploy": handle_deploy,
    "adr-created": handle_adr_created,
    "degraded": handle_degraded,
}


def process_event(event: dict, modes: dict, filters: dict) -> tuple[str, str]:
    """Retorna (decision, reason)."""
    etype = event.get("type")
    handler = HANDLERS.get(etype)
    if handler is None:
        return ("skipped", "unknown-type")
    mode = modes["overrides"].get(etype, modes["default"])
    written, reason = handler(event, mode, filters)
    decision = "written" if written else "queued"
    return (decision, reason)


def append_processed(event_id: str, decision: str, reason: str, latency_ms: int) -> None:
    today = dt.date.today().isoformat()
    out = EVENTS_PROCESSED / f"{today}.jsonl"
    out.parent.mkdir(parents=True, exist_ok=True)
    record = {
        "event_id": event_id,
        "decision": decision,
        "reason": reason,
        "latency_ms": latency_ms,
        "ts": dt.datetime.now().isoformat(),
    }
    with out.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(record) + "\n")


def archive_raw(payload: str, event_id: str) -> None:
    today = dt.date.today().isoformat()
    out = EVENTS_RAW / f"{today}.jsonl"
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("a", encoding="utf-8") as fh:
        fh.write(payload.rstrip() + "\n")


def process_queue(verbose: bool = False) -> tuple[int, int, int]:
    """Processa todos os arquivos em EVENTS_IN. Retorna (total, written, errors)."""
    EVENTS_IN.mkdir(parents=True, exist_ok=True)
    files = sorted(EVENTS_IN.glob("*.jsonl"))
    if not files:
        return (0, 0, 0)

    modes = load_capture_modes()
    filters = load_filters()
    repo_map = load_repo_map()

    total = 0
    written = 0
    errors = 0

    for fpath in files:
        try:
            content = fpath.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        for line in content.splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                shutil.move(str(fpath), EVENTS_DLQ / fpath.name)
                errors += 1
                continue
            total += 1
            archive_raw(line, hash_event(event))

            # Resolve project from repo_path se disponível
            if "repo_path" in event and "project" not in event:
                proj = project_for_repo(event["repo_path"], repo_map)
                if proj:
                    event["project"] = proj

            event_id = event.get("event_id") or hash_event(event)
            event["event_id"] = event_id
            t0 = time.monotonic()
            decision, reason = process_event(event, modes, filters)
            latency = int((time.monotonic() - t0) * 1000)
            append_processed(event_id, decision, reason, latency)
            if decision == "written":
                written += 1
            if verbose:
                print(f"  {decision} ({reason}): {event.get('type')} {event_id}")
        # Remove arquivo processado
        fpath.unlink()

    return (total, written, errors)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--watch", action="store_true")
    ap.add_argument("--once", action="store_true", default=True)
    ap.add_argument("--verbose", action="store_true")
    ap.add_argument("--interval", type=int, default=5)
    args = ap.parse_args()

    if args.watch:
        print("[router] watching events…", file=sys.stderr)
        try:
            while True:
                total, written, errors = process_queue(verbose=args.verbose)
                if total > 0:
                    print(f"[router] processed {total} (written={written} errors={errors})", file=sys.stderr)
                time.sleep(args.interval)
        except KeyboardInterrupt:
            return 0
    else:
        total, written, errors = process_queue(verbose=args.verbose)
        print(f"[router] {total} eventos processados (escritos={written}, erros={errors})", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
