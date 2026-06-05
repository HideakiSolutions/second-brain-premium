#!/usr/bin/env python3
"""Queue and flush incremental semantic index updates for hook usage."""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any


VAULT = Path(os.environ.get("VAULT") or os.environ.get("VAULT_ROOT") or Path(__file__).resolve().parents[3]).resolve()
QUEUE = VAULT / "_memory" / ".semantic-index-queue"
REINDEX = VAULT / ".claude" / "scripts" / "sb-reindex.sh"

IGNORED_DIRS = {
    ".git",
    ".obsidian",
    ".trash",
    "node_modules",
    ".venv",
    "__pycache__",
    "_memory/.events",
}
IGNORED_FILES = {
    "_memory/.prompt-log.txt",
    "_memory/.semantic-index-queue",
}
ELIGIBLE_SUFFIXES = {
    ".md",
    ".txt",
    ".yaml",
    ".yml",
    ".json",
    ".py",
    ".sh",
    ".toml",
}


def _load_json() -> dict[str, Any]:
    raw = sys.stdin.read()
    if not raw.strip():
        return {}
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return {}
    return data if isinstance(data, dict) else {}


def _walk_values(value: Any) -> list[str]:
    found: list[str] = []
    if isinstance(value, str):
        found.append(value)
    elif isinstance(value, list):
        for item in value:
            found.extend(_walk_values(item))
    elif isinstance(value, dict):
        for item in value.values():
            found.extend(_walk_values(item))
    return found


def _candidate_values(payload: dict[str, Any]) -> list[str]:
    values: list[str] = []
    tool_input = payload.get("tool_input")
    if isinstance(tool_input, dict):
        for key in ("file_path", "path", "notebook_path"):
            value = tool_input.get(key)
            if isinstance(value, str):
                values.append(value)
        for key in ("file_paths", "paths"):
            value = tool_input.get(key)
            if isinstance(value, list):
                values.extend(str(item) for item in value if isinstance(item, str))
        edits = tool_input.get("edits")
        if isinstance(edits, list):
            values.extend(_walk_values(edits))
    for key in ("file_path", "path"):
        value = payload.get(key)
        if isinstance(value, str):
            values.append(value)
    return values


def _normalize(candidate: str) -> str | None:
    if not candidate or "\n" in candidate or "\0" in candidate:
        return None
    path = Path(candidate)
    if not path.is_absolute():
        path = VAULT / path
    try:
        resolved = path.resolve()
        rel = resolved.relative_to(VAULT)
    except (OSError, ValueError):
        return None
    rel_s = rel.as_posix()
    if rel_s in IGNORED_FILES:
        return None
    if any(rel_s == ignored or rel_s.startswith(f"{ignored}/") for ignored in IGNORED_DIRS):
        return None
    if resolved.is_dir() or not resolved.exists():
        return None
    if resolved.suffix.lower() not in ELIGIBLE_SUFFIXES:
        return None
    return rel_s


def _read_queue() -> list[str]:
    if not QUEUE.exists():
        return []
    return [line.strip() for line in QUEUE.read_text(encoding="utf-8").splitlines() if line.strip()]


def _write_queue(paths: list[str]) -> None:
    QUEUE.parent.mkdir(parents=True, exist_ok=True)
    unique = sorted(dict.fromkeys(paths))
    if unique:
        QUEUE.write_text("\n".join(unique) + "\n", encoding="utf-8")
    elif QUEUE.exists():
        QUEUE.unlink()


def cmd_queue(_: argparse.Namespace) -> int:
    payload = _load_json()
    candidates = [_normalize(value) for value in _candidate_values(payload)]
    paths = [path for path in candidates if path]
    if not paths:
        return 0
    current = _read_queue()
    _write_queue(current + paths)
    print(f"semantic_index_queued={len(set(paths))}")
    return 0


def cmd_flush(args: argparse.Namespace) -> int:
    queued = _read_queue()
    if not queued:
        print("semantic_index_queue_empty=true")
        return 0
    existing = [path for path in queued if (VAULT / path).exists()]
    if not existing:
        _write_queue([])
        print("semantic_index_queue_empty=true")
        return 0
    selected = existing[: args.max_files] if args.max_files else existing
    cmd = ["bash", str(REINDEX), "--paths", *selected]
    if args.dry_run:
        print(" ".join(cmd))
        return 0
    proc = subprocess.run(cmd, cwd=str(VAULT), check=False)
    if proc.returncode != 0:
        print(f"semantic_index_flush_failed={proc.returncode}", file=sys.stderr)
        return proc.returncode
    remaining = [path for path in queued if path not in selected]
    _write_queue(remaining)
    print(f"semantic_index_flushed={len(selected)}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("queue").set_defaults(func=cmd_queue)
    flush = sub.add_parser("flush")
    flush.add_argument("--max-files", type=int, default=0)
    flush.add_argument("--dry-run", action="store_true")
    flush.set_defaults(func=cmd_flush)
    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
