#!/usr/bin/env python3
"""Common memory reviewer surface for agent runtimes.

Commands:
  preflight: return short contextual hints before execution/decision/question turns.
  sync: persist an idempotent operational capture under _pipeline/_memory only.
  learn: run the observational learn-loop and summarize candidate freshness.

This module is intentionally deterministic. It never edits skills, commands,
hooks, accepted ADRs, canonical learnings, or raw prompt logs.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

VAULT = Path(os.environ.get("VAULT") or os.environ.get("VAULT_ROOT") or Path(__file__).resolve().parents[3])

EXECUTION_RE = re.compile(
    r"\b(implement\w*|corrigir|corrija|fix|build|criar|create|adicionar|"
    r"add|alterar|update|atualizar|rodar|run|test|validar|deploy|merge|commit|"
    r"decision|decisao|decidir|pergunta|question|como|why|por que)\b",
    re.IGNORECASE,
)

CATEGORY_PATTERNS = {
    "git": r"\b(commit|push|merge|branch|pr\b|pull request|tag|release)\b",
    "validation": r"\b(valid|test|verify|verif|smoke|suite|lint|typecheck)\b",
    "deploy": r"\b(k3s|k8s|kubernetes|argocd|gitops|rollout|deploy|ingress)\b",
    "memory": r"\b(memory|memoria|vault|second[ -]?brain|learnings?|decisions?|adr)\b",
    "workflow": r"\b(skill|command|hook|agent|cli|runtime|preflight|sync|learn)\b",
    "frontend": r"\b(frontend|ui|ux|playwright|mobile|desktop)\b",
}

ALLOWLIST_PREFIXES = (
    "_pipeline/inbox/",
    "_pipeline/self-improvement-candidates.md",
    "_memory/activity-log.md",
    "_memory/.pre-compact-notes.md",
    "_memory/.needs-end-session",
    "_memory/.compacted-without-end-session",
)


@dataclass
class Payload:
    runtime: str
    cwd: str
    intent: str
    project: str
    mode: str
    trigger: str
    summary: str
    event_id: str


def read_stdin_payload() -> dict[str, Any]:
    raw = sys.stdin.read()
    if not raw.strip():
        return {}
    try:
        loaded = json.loads(raw)
        return loaded if isinstance(loaded, dict) else {"intent": raw}
    except json.JSONDecodeError:
        return {"intent": raw}


def payload_from_args(args: argparse.Namespace) -> Payload:
    data = read_stdin_payload()
    runtime = args.runtime or data.get("runtime") or data.get("agent") or "agent"
    cwd = args.cwd or data.get("cwd") or data.get("project_dir") or os.getcwd()
    intent = args.intent or data.get("intent") or data.get("prompt") or data.get("message") or ""
    project = args.project or data.get("project") or ""
    mode = args.mode or data.get("mode") or ""
    trigger = args.trigger or data.get("trigger") or data.get("hook_event_name") or ""
    summary = args.summary or data.get("summary") or data.get("transcript_summary") or ""
    event_id = args.event_id or data.get("event_id") or data.get("session_id") or data.get("transcript_path") or ""
    if not summary and intent:
        summary = summarize_intent(str(intent))
    return Payload(str(runtime), str(cwd), str(intent), str(project), str(mode), str(trigger), str(summary), str(event_id))


def rel(path: Path) -> str:
    try:
        return path.relative_to(VAULT).as_posix()
    except ValueError:
        return path.as_posix()


def ensure_allowed(path: Path) -> None:
    relative = rel(path)
    if any(relative == prefix or relative.startswith(prefix) for prefix in ALLOWLIST_PREFIXES):
        return
    raise PermissionError(f"write target denied by memory reviewer allowlist: {relative}")


def write_text(path: Path, text: str, append: bool = False) -> None:
    ensure_allowed(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    mode = "a" if append else "w"
    with path.open(mode, encoding="utf-8") as handle:
        handle.write(text)


def summarize_intent(text: str) -> str:
    text = re.sub(r"\s+", " ", text).strip()
    if not text:
        return ""
    categories = categories_for(text)
    if categories:
        return "intent categories: " + ", ".join(categories)
    return "intent captured for operational review"


def categories_for(text: str) -> list[str]:
    found: list[str] = []
    for name, pattern in CATEGORY_PATTERNS.items():
        if re.search(pattern, text, re.IGNORECASE):
            found.append(name)
    return found


def resolve_project(payload: Payload) -> str:
    if payload.project:
        return slug(payload.project)
    cwd = Path(payload.cwd)
    name = cwd.name if str(cwd) not in {"", "."} else ""
    if not name and payload.intent:
        name = payload.intent.split()[0]
    return slug(name or "unknown")


def slug(value: str) -> str:
    value = value.strip().lower()
    value = re.sub(r"[^a-z0-9._-]+", "-", value)
    value = value.strip("-._")
    return value or "unknown"


def should_preflight(payload: Payload) -> bool:
    haystack = " ".join(part for part in [payload.intent, payload.mode, payload.trigger] if part)
    return bool(EXECUTION_RE.search(haystack))


def run_synapse_recall(query: str) -> list[str]:
    """Recall associativo (sinapses): uma memoria puxa as vizinhas relevantes.

    Ambient (preflight) usa --no-log para nao reforcar sinapses por injecao
    automatica — so recalls deliberados geram sinal hebbiano.
    """
    if os.environ.get("SB_AGENT_OFFLINE") == "1":
        return []
    script = VAULT / ".claude" / "scripts" / "sb-synapse.sh"
    if not script.exists():
        return []
    try:
        proc = subprocess.run(
            ["bash", str(script), "recall", query, "--k", "4", "--brief", "--no-log"],
            cwd=str(VAULT),
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            timeout=4,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return []
    if proc.returncode != 0:
        return []
    lines = compact_lines(proc.stdout, limit=5)
    return [line[2:] if line.startswith("- ") else line for line in lines]


def run_sb_search(query: str) -> list[str]:
    if os.environ.get("SB_AGENT_OFFLINE") == "1":
        return []
    script = VAULT / ".claude" / "scripts" / "sb-search.sh"
    if not script.exists():
        return []
    try:
        proc = subprocess.run(
            ["bash", str(script), query, "--k", "3"],
            cwd=str(VAULT),
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            timeout=4,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return []
    if proc.returncode != 0:
        return []
    return compact_lines(proc.stdout, limit=5)


def compact_lines(text: str, limit: int = 5) -> list[str]:
    lines: list[str] = []
    for line in text.splitlines():
        clean = re.sub(r"\s+", " ", line).strip()
        if not clean or clean.startswith("{"):
            continue
        if len(clean) > 180:
            clean = clean[:177] + "..."
        lines.append(clean)
        if len(lines) >= limit:
            break
    return lines


def fallback_context(project: str, intent: str) -> list[str]:
    candidates = [
        VAULT / "_knowledge" / "projects" / project / "state.md",
        VAULT / "_knowledge" / "projects" / project / "decisions.md",
        VAULT / "_knowledge" / "projects" / project / "gotchas.md",
        VAULT / "_memory" / "current-state.md",
        VAULT / "_memory" / "activity-log.md",
    ]
    terms = [term for term in re.findall(r"[a-zA-Z0-9_-]{4,}", intent.lower())[:8]]
    out: list[str] = []
    for path in candidates:
        if not path.exists():
            continue
        try:
            lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
        except OSError:
            continue
        selected = select_relevant_lines(lines, terms)
        for line in selected:
            out.append(f"{rel(path)}: {line}")
            if len(out) >= 5:
                return out
    return out


def select_relevant_lines(lines: list[str], terms: list[str]) -> list[str]:
    selected: list[str] = []
    for line in lines:
        clean = re.sub(r"\s+", " ", line).strip()
        if not clean or clean in {"---"}:
            continue
        low = clean.lower()
        if clean.startswith(("#", "-", "*")) or any(term in low for term in terms):
            if len(clean) > 180:
                clean = clean[:177] + "..."
            selected.append(clean)
        if len(selected) >= 3:
            break
    return selected


def preflight(args: argparse.Namespace) -> int:
    payload = payload_from_args(args)
    if not should_preflight(payload):
        return 0
    project = resolve_project(payload)
    query = " ".join(part for part in [project, payload.intent] if part).strip()
    context = (
        run_synapse_recall(query)
        or run_sb_search(query)
        or fallback_context(project, payload.intent)
    )
    if not context:
        return 0
    print("[MEMORY] Contexto relevante antes de executar:")
    for item in context[:5]:
        print(f"- {item}")
    print("[MEMORY] Use como precedente; nao altere memoria canonica sem comando explicito.")
    return 0


def capture_id(payload: Payload, project: str, event_key: str) -> str:
    basis = "|".join(
        [
            datetime.now(timezone.utc).strftime("%Y-%m-%d"),
            payload.trigger,
            project,
            event_key,
            summarize_intent(payload.summary or payload.intent),
        ]
    )
    return hashlib.sha256(basis.encode("utf-8")).hexdigest()[:16]


def sync(args: argparse.Namespace) -> int:
    payload = payload_from_args(args)
    now = datetime.now()
    today = now.strftime("%Y-%m-%d")
    timestamp = now.strftime("%Y-%m-%d %H:%M")
    project = resolve_project(payload)
    trigger = slug(payload.trigger or "manual")
    categories = categories_for(" ".join([payload.summary, payload.intent, trigger]))
    categories_text = ", ".join(categories or ["operational"])
    event_key = slug(payload.event_id or timestamp)
    cid = capture_id(payload, project, event_key)

    inbox = VAULT / "_pipeline" / "inbox" / f"auto-captures-{today}.md"
    existing = inbox.read_text(encoding="utf-8", errors="replace") if inbox.exists() else ""
    if f"capture-id: {cid}" not in existing:
        entry = (
            f"\n## [{timestamp}] memory-reviewer | {trigger}\n"
            f"- capture-id: {cid}\n"
            f"- runtime: {payload.runtime}\n"
            f"- project: {project}\n"
            f"- event-key: {event_key}\n"
            f"- categories: {categories_text}\n"
            f"- summary: {summarize_intent(payload.summary or payload.intent)}\n"
            "- status: pending-review\n"
        )
        write_text(inbox, entry, append=True)

    activity = VAULT / "_memory" / "activity-log.md"
    write_text(activity, f"\n## [{timestamp}] memory-reviewer | {trigger} - capture {cid}\n", append=True)

    if trigger in {"pre-compact", "precompact"}:
        write_text(VAULT / "_memory" / ".compacted-without-end-session", f"{today}\n")
    if trigger in {"session-end", "sessionend"}:
        write_text(VAULT / "_memory" / ".needs-end-session", f"{today}\n")

    print(f"memory-reviewer: sync {trigger} registrado ({cid})")
    return 0


def learn(args: argparse.Namespace) -> int:
    payload = payload_from_args(args)
    script = VAULT / ".claude" / "scripts" / "learn-loop.sh"
    if not script.exists():
        script = Path(__file__).resolve().parents[1] / "learn-loop.sh"
    if not script.exists():
        print("memory-reviewer: learn-loop ausente; patches_applied=0")
        return 0
    proc = subprocess.run(["bash", str(script)], cwd=str(VAULT), check=False)
    candidates = VAULT / "_pipeline" / "self-improvement-candidates.md"
    count = 0
    stale = "unknown"
    if candidates.exists():
        text = candidates.read_text(encoding="utf-8", errors="replace")
        count = len(re.findall(r"^### (?!Sem dados suficientes)", text, re.MULTILINE))
        age_seconds = datetime.now().timestamp() - candidates.stat().st_mtime
        stale = "yes" if age_seconds > 14 * 86400 else "no"
    trigger = payload.trigger or "manual"
    if proc.returncode != 0:
        print(
            f"memory-reviewer: learn trigger={trigger} learn_failed=true "
            f"exit_code={proc.returncode}; patches_applied=0"
        )
        return proc.returncode
    print(f"memory-reviewer: learn trigger={trigger} candidates={count} stale={stale}; patches_applied=0")
    return 0


def self_check(_: argparse.Namespace) -> int:
    print("allowlist:")
    for prefix in ALLOWLIST_PREFIXES:
        print(f"- {prefix}")
    return 0


def add_common(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--runtime", default="")
    parser.add_argument("--cwd", default="")
    parser.add_argument("--intent", default="")
    parser.add_argument("--project", default="")
    parser.add_argument("--mode", default="")
    parser.add_argument("--trigger", default="")
    parser.add_argument("--summary", default="")
    parser.add_argument("--event-id", default="")


def main() -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="cmd", required=True)
    for name in ["preflight", "sync", "learn"]:
        child = sub.add_parser(name)
        add_common(child)
    sub.add_parser("self-check")
    args = parser.parse_args()
    if args.cmd == "preflight":
        return preflight(args)
    if args.cmd == "sync":
        return sync(args)
    if args.cmd == "learn":
        return learn(args)
    if args.cmd == "self-check":
        return self_check(args)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
