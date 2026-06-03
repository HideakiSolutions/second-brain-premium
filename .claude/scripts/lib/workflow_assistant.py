#!/usr/bin/env python3
"""Assisted workflow hooks for the second-brain Claude runtime.

All actions are advisory except secret detection on sensitive writes.
"""

from __future__ import annotations

import argparse
import json
import re
import os
import sys
from datetime import datetime
from pathlib import Path

VAULT = Path(os.environ.get("VAULT", "$VAULT"))

NOISE_RE = re.compile(
    r"(Chunk ID:|Wall time:|Process exited|Original token count:|^Output:|"
    r"<environment_context>|</environment_context>|<summary>|</summary>|"
    r"tool_use|tool result|stdout|stderr|session_id|task notification|"
    r"compact(ed|acao)|subagent prompt|spawn agent)",
    re.IGNORECASE,
)

SECRET_PATTERNS = [
    re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    re.compile(r"\bgh[pousr]_[A-Za-z0-9_]{30,}\b"),
    re.compile(r"\bsk-[A-Za-z0-9]{20,}\b"),
    re.compile(
        r"(?i)\b(api[_-]?key|secret|token|password|passwd|pwd)\b\s*[:=]\s*['\"]?"
        r"([A-Za-z0-9_./+=-]{16,})"
    ),
]

ALLOWLIST_RE = re.compile(
    r"(?i)(example|dummy|placeholder|redacted|changeme|test-only|fake|fixture)"
)

CATEGORY_PATTERNS = {
    "git": r"\b(commit|push|merge|branch|branche|pr\b|pull request|tag|release)\b",
    "validation": r"\b(valid|test|verif|revalid|funcion|status|limpo|higien|smoke)\b",
    "environment": r"\b(global|projeto|ambiente|codex|claude|hseos|axon|rtk|mcp)\b",
    "second_brain": r"\b(second[ -]?brain|vault|mem[oó]ria|skills?|commands?|comandos?|hooks?|agents?|agentes?)\b",
    "deploy": r"\b(k3s|k8s|kubernetes|argocd|gitops|rollout|deploy|image|ingress)\b",
    "frontend": r"\b(frontend|ux|ui|playwright|axe|mobile|desktop|produto|scaffold)\b",
    "continue": r"\b(pode prosseguir|prossiga|continue|implement the plan|implemente o plano)\b",
}


def load_payload() -> dict:
    raw = sys.stdin.read()
    if not raw.strip():
        return {}
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {"prompt": raw}


def prompt_from_payload(payload: dict) -> str:
    return str(payload.get("prompt") or payload.get("text") or payload.get("message") or "")


def cwd_from_payload(payload: dict) -> str:
    return str(payload.get("cwd") or payload.get("project_dir") or "")


def extract_timestamp(line: str) -> str:
    m = re.match(r"^\[([^]|]+)(?:\|[^\]]*)?\]", line)
    if m:
        return m.group(1).strip()
    return "unknown"


def command_from_text(text: str) -> str | None:
    m = re.search(r"(?<!\w)/([a-z0-9][a-z0-9-]*)", text, re.IGNORECASE)
    return f"/{m.group(1).lower()}" if m else None


def categories_for_text(text: str) -> list[str]:
    out: list[str] = []
    for name, pattern in CATEGORY_PATTERNS.items():
        if re.search(pattern, text, re.IGNORECASE):
            out.append(name)
    if has_secret(text):
        out.append("secret_candidate")
    return out


def has_secret(text: str) -> bool:
    if not text:
        return False
    for pattern in SECRET_PATTERNS:
        for match in pattern.finditer(text):
            start = max(0, match.start() - 40)
            end = min(len(text), match.end() + 40)
            if not ALLOWLIST_RE.search(text[start:end]):
                return True
    return False


def sanitize_file(path: Path) -> int:
    if not path.exists():
        return 0
    for raw_line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = raw_line.strip()
        if not line or NOISE_RE.search(line):
            continue
        ts = extract_timestamp(line)
        cmd = command_from_text(line)
        categories = categories_for_text(line)
        fields = [f"ts:{ts}"]
        if cmd:
            fields.append(f"command:{cmd}")
        fields.extend(f"category:{name}" for name in categories)
        if not cmd and not categories:
            fields.append("category:other")
        print(" ".join(fields))
    return 0


def continue_contract(payload: dict) -> int:
    prompt = prompt_from_payload(payload)
    if re.search(CATEGORY_PATTERNS["continue"], prompt, re.IGNORECASE):
        print(
            "[WORKFLOW] Contrato de continuidade: continue executando o plano ativo "
            "ate concluir, validar ou encontrar bloqueio real. Nao pare apenas para "
            "pedir confirmacao se o proximo passo ja estiver claro."
        )
    return 0


def validation_tier(payload: dict) -> int:
    prompt = prompt_from_payload(payload)
    lower = prompt.lower()
    if not re.search(r"valid|test|merge|pr\b|deploy|gitops|release|tag|ux|frontend|closeout", lower):
        return 0
    if re.search(CATEGORY_PATTERNS["deploy"], lower) or re.search(r"\b(live|url publica|publica|rollout)\b", lower):
        tier = "live"
        detail = "GitOps/k3s/ArgoCD, imagem, rollout, health, URL publica e smoke."
    elif re.search(r"\b(merge|pr\b|pull request|release|tag|security|auth|migration|delivery-closeout)\b", lower):
        tier = "full"
        detail = "testes relevantes, git status, scan de secrets e evidencia antes de PR/merge/tag."
    else:
        tier = "quick"
        detail = "checks focados nos arquivos tocados e smoke local suficiente."
    print(f"[WORKFLOW] Gate sugerido: {tier} — {detail}")
    return 0


def sensitive_target(path: str) -> bool:
    if not path:
        return True
    rel = path.replace("\\", "/")
    suffix = Path(rel).suffix.lower()
    if suffix in {".md", ".txt", ".json", ".yaml", ".yml", ".env"}:
        return True
    return any(part in rel for part in ["/_memory/", "/_prompts/", "/.claude/", "/.codex/"])


def secret_guard(payload: dict, mode: str) -> int:
    if mode == "prompt":
        prompt = prompt_from_payload(payload)
        if has_secret(prompt):
            print(
                "[SECRET] Possivel credencial no prompt. Nao grave este valor em logs, "
                "markdown, rules ou prompts; use referencia redigida.",
                file=sys.stderr,
            )
        return 0

    tool_input = payload.get("tool_input") or payload.get("input") or {}
    file_path = str(tool_input.get("file_path") or tool_input.get("path") or "")
    fragments = [
        str(tool_input.get("content") or ""),
        str(tool_input.get("new_string") or ""),
        str(tool_input.get("newText") or ""),
        str(tool_input.get("old_string") or ""),
    ]
    text = "\n".join(part for part in fragments if part)
    if sensitive_target(file_path) and has_secret(text):
        print(
            f"[SECRET] Escrita bloqueada: possivel credencial detectada em alvo sensivel ({file_path or 'sem path'}).",
            file=sys.stderr,
        )
        return 2
    return 0


def post_merge_recorder(payload: dict) -> int:
    prompt = prompt_from_payload(payload)
    if not re.search(r"\b(merge(d)?|pull request|pr\s*#?\d+|tag\s+v?\d|release)\b", prompt, re.IGNORECASE):
        return 0
    inbox = VAULT / "_pipeline" / "inbox"
    inbox.mkdir(parents=True, exist_ok=True)
    now = datetime.now()
    target = inbox / f"auto-captures-{now:%Y-%m-%d}.md"
    cwd = Path(cwd_from_payload(payload)).name or "unknown"
    categories = ", ".join(categories_for_text(prompt) or ["git"])
    entry = (
        f"\n## [{now:%Y-%m-%d %H:%M}] post-merge-recorder | assisted\n"
        f"- Projeto/CWD: {cwd}\n"
        f"- Categorias: {categories}\n"
        "- Evidencia: prompt indicou PR/merge/tag/release; revisar antes de promover ao vault.\n"
        "- Status: pendente-revisao\n"
    )
    with target.open("a", encoding="utf-8") as fh:
        fh.write(entry)
    print(f"[WORKFLOW] Captura assistida criada em {target.relative_to(VAULT)}. Revise com /review-captures.")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="cmd", required=True)
    p_sanitize = sub.add_parser("sanitize-log")
    p_sanitize.add_argument("path")
    p_secret = sub.add_parser("secret-guard")
    p_secret.add_argument("--mode", choices=["prompt", "tool"], required=True)
    sub.add_parser("continue-contract")
    sub.add_parser("validation-tier")
    sub.add_parser("post-merge-recorder")
    args = parser.parse_args()

    if args.cmd == "sanitize-log":
        return sanitize_file(Path(args.path))

    payload = load_payload()
    if args.cmd == "secret-guard":
        return secret_guard(payload, args.mode)
    if args.cmd == "continue-contract":
        return continue_contract(payload)
    if args.cmd == "validation-tier":
        return validation_tier(payload)
    if args.cmd == "post-merge-recorder":
        return post_merge_recorder(payload)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
