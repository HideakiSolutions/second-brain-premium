"""
llm_analyst.py — análise via LLM (Claude) ou fallback determinístico.

Se ANTHROPIC_API_KEY estiver disponível, chama claude-sonnet-4-6 com um prompt
estruturado que recebe o contexto do projeto e retorna 3-5 tarefas plausíveis em JSON.
Caso contrário, usa fallback determinístico baseado em frequência de tipos + next_step.

Cache de respostas LLM por (projeto + hash work-log) por 1h em /tmp/sb-predict-cache/.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import time
from pathlib import Path
from typing import Any

try:
    import httpx  # type: ignore

    _HAS_HTTPX = True
except ImportError:
    _HAS_HTTPX = False

import urllib.error
import urllib.request

ANTHROPIC_API_URL = "https://api.anthropic.com/v1/messages"
MODEL = "claude-sonnet-4-6"
MAX_TOKENS = 1024
CACHE_DIR = Path("/tmp/sb-predict-cache")
CACHE_TTL_SECONDS = 3600  # 1 hora


# ---------------------------------------------------------------------------
# Cache helpers
# ---------------------------------------------------------------------------


def _cache_key(project: str, worklog_text: str) -> str:
    digest = hashlib.sha256(f"{project}:{worklog_text}".encode()).hexdigest()[:16]
    return f"{project}_{digest}.json"


def _read_cache(key: str) -> list[dict] | None:
    path = CACHE_DIR / key
    if not path.exists():
        return None
    age = time.time() - path.stat().st_mtime
    if age > CACHE_TTL_SECONDS:
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def _write_cache(key: str, predictions: list[dict]) -> None:
    try:
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        (CACHE_DIR / key).write_text(
            json.dumps(predictions, ensure_ascii=False, indent=2), encoding="utf-8"
        )
    except Exception:
        pass  # cache é opcional


# ---------------------------------------------------------------------------
# Fallback determinístico
# ---------------------------------------------------------------------------

# Tipos de tarefa em ordem de "produtividade esperada" por fase
_PHASE_TYPE_WEIGHTS: dict[str, list[tuple[str, float]]] = {
    "poc": [("feature", 0.55), ("spike", 0.20), ("fix", 0.15), ("chore", 0.10)],
    "mvp": [("feature", 0.50), ("fix", 0.25), ("chore", 0.15), ("task", 0.10)],
    "foundation": [("task", 0.40), ("chore", 0.30), ("spike", 0.20), ("fix", 0.10)],
    "broker": [("feature", 0.45), ("fix", 0.30), ("chore", 0.15), ("task", 0.10)],
    "banking": [("feature", 0.50), ("fix", 0.25), ("task", 0.15), ("chore", 0.10)],
    "default": [("feature", 0.45), ("fix", 0.25), ("chore", 0.15), ("task", 0.15)],
}

_CONFIDENCE_BY_RANK = [0.85, 0.70, 0.55, 0.40, 0.30]
_UNCERTAINTY_LABELS = {
    (0.8, 1.0): "alta",
    (0.6, 0.8): "média-alta",
    (0.4, 0.6): "média",
    (0.0, 0.4): "baixa",
}


def _uncertainty_label(confidence: float) -> str:
    for (lo, hi), label in _UNCERTAINTY_LABELS.items():
        if lo <= confidence < hi:
            return label
    return "baixa"


def _detect_phase_key(phase_name: str) -> str:
    name = phase_name.lower()
    for key in _PHASE_TYPE_WEIGHTS:
        if key in name:
            return key
    return "default"


def _type_distribution_from_history(
    entries: list[dict], n: int = 30
) -> dict[str, float]:
    """Frequência relativa dos tipos nas últimas N entradas."""
    recent = entries[:n]
    counts: dict[str, int] = {}
    for e in recent:
        t = e.get("type", "task")
        counts[t] = counts.get(t, 0) + 1
    total = sum(counts.values()) or 1
    return {k: v / total for k, v in counts.items()}


def _fallback_predict(
    project: str,
    entries: list[dict],
    roadmap: dict[str, Any],
    state: dict[str, Any],
    k: int = 5,
) -> list[dict]:
    """Gera predições determinísticas sem chamada LLM."""
    phase_name = state.get("phase") or roadmap.get("current_phase") or ""
    next_step = state.get("next_step", "")
    blockers = state.get("blockers", "")
    open_questions = state.get("open_questions", [])

    phase_key = _detect_phase_key(phase_name)
    phase_weights = dict(_PHASE_TYPE_WEIGHTS[phase_key])

    # Ajusta pesos com base no histórico real (Markov leve)
    hist_dist = _type_distribution_from_history(entries)
    if hist_dist:
        for t in phase_weights:
            if t in hist_dist:
                # Blend 60% histórico, 40% prior da fase
                phase_weights[t] = 0.6 * hist_dist[t] + 0.4 * phase_weights[t]

    # Ordena tipos por probabilidade
    sorted_types = sorted(phase_weights.items(), key=lambda x: x[1], reverse=True)

    # Identifica itens pendentes do roadmap na fase atual
    pending_items: list[str] = []
    for ph in roadmap.get("phases", []):
        if ph.get("status") == "current":
            pending_items = ph.get("items", [])
            break

    predictions: list[dict] = []

    # Predição 1: next_step declarado (alta confiança se existir)
    if next_step and next_step.lower() not in ("nenhuma", "n/a", ""):
        predictions.append(
            {
                "rank": 1,
                "type": "task",
                "description": next_step,
                "confidence": 0.92,
                "uncertainty": "baixa",
                "rationale": "Próximo passo declarado explicitamente no state.md",
                "source": "state",
            }
        )

    # Predições a partir de itens pendentes do roadmap
    for item in pending_items[:2]:
        if len(predictions) >= k:
            break
        rank = len(predictions) + 1
        task_type = sorted_types[0][0] if sorted_types else "feature"
        confidence = _CONFIDENCE_BY_RANK[min(rank - 1, len(_CONFIDENCE_BY_RANK) - 1)]
        predictions.append(
            {
                "rank": rank,
                "type": task_type,
                "description": item,
                "confidence": confidence,
                "uncertainty": _uncertainty_label(confidence),
                "rationale": f"Item pendente na fase atual do roadmap ({phase_name})",
                "source": "roadmap",
            }
        )

    # Preenche com tipos mais frequentes se ainda há espaço
    type_idx = 0
    while len(predictions) < k:
        rank = len(predictions) + 1
        if type_idx < len(sorted_types):
            task_type, prob = sorted_types[type_idx]
            type_idx += 1
        else:
            task_type, prob = "task", 0.2

        confidence = _CONFIDENCE_BY_RANK[min(rank - 1, len(_CONFIDENCE_BY_RANK) - 1)]

        # Tenta usar open question como gancho de descrição
        if open_questions and rank <= len(open_questions) + len(predictions):
            oq_idx = rank - len(predictions) - 1
            desc_base = open_questions[oq_idx] if oq_idx < len(open_questions) else ""
        else:
            desc_base = ""

        if desc_base:
            desc = f"Investigar/resolver: {desc_base}"
        elif task_type == "feature":
            desc = f"Implementar próxima feature da fase {phase_name}"
        elif task_type == "fix":
            desc = "Corrigir bugs identificados na fase atual"
        elif task_type == "chore":
            desc = "Limpeza técnica, refactor ou atualização de dependências"
        elif task_type == "spike":
            desc = f"Spike de exploração técnica para {project}"
        else:
            desc = f"Tarefa de configuração/infraestrutura para {project}"

        if blockers and rank == len(predictions) + 1:
            desc += f" (atenção ao bloqueador: {blockers[:80]})"

        predictions.append(
            {
                "rank": rank,
                "type": task_type,
                "description": desc,
                "confidence": round(confidence, 2),
                "uncertainty": _uncertainty_label(confidence),
                "rationale": f"Tipo '{task_type}' é dominante (prob {prob:.0%}) na fase '{phase_key}'",
                "source": "markov",
            }
        )

    return predictions[:k]


# ---------------------------------------------------------------------------
# LLM call
# ---------------------------------------------------------------------------

_SYSTEM_PROMPT = """\
Você é um assistente de planejamento de software. Com base no contexto fornecido
de um projeto, gere as 3 a 5 tarefas mais plausíveis para a próxima sessão de trabalho.

Responda SOMENTE com um array JSON válido. Cada item deve ter:
{
  "rank": <int, 1=mais provável>,
  "type": <"feature"|"fix"|"chore"|"spike"|"task">,
  "description": <string em PT-BR, máx 100 chars>,
  "confidence": <float 0.0-1.0>,
  "uncertainty": <"baixa"|"média"|"média-alta"|"alta">,
  "rationale": <string curta em PT-BR explicando por que esta tarefa é plausível>
}

Considere:
- O próximo passo declarado no state.md tem prioridade máxima.
- Itens pendentes na fase atual do roadmap são de alta prioridade.
- Open questions indicam investigações ou decisões técnicas pendentes.
- Bloqueadores reduzem a probabilidade de certas tarefas.
- O histórico do work-log indica a cadência e tipos de trabalho habituais.

NÃO inclua comentários, markdown ou texto fora do JSON.
"""


def _build_user_prompt(
    project: str,
    entries: list[dict],
    roadmap: dict[str, Any],
    state: dict[str, Any],
    k: int,
) -> str:
    phase_name = state.get("phase") or roadmap.get("current_phase") or "desconhecida"
    next_step = state.get("next_step", "não informado")
    blockers = state.get("blockers", "nenhum")
    open_qs = state.get("open_questions", [])
    open_qs_text = "\n".join(f"- {q}" for q in open_qs) if open_qs else "nenhuma"

    # Resumo do work-log (últimos 30)
    recent = entries[:30]
    wl_lines = "\n".join(
        f"- {e['date']} | {e['type']} | {e['description'][:80]}"
        for e in recent
    )

    # Resumo do roadmap
    current_items: list[str] = []
    for ph in roadmap.get("phases", []):
        if ph.get("status") == "current":
            current_items = ph.get("items", [])
            break
    roadmap_text = "\n".join(f"- {i}" for i in current_items[:10]) or "não disponível"

    return f"""Projeto: {project}
Fase atual: {phase_name}
Próximo passo declarado: {next_step}
Bloqueadores: {blockers}
Open questions:
{open_qs_text}

Itens pendentes na fase atual (roadmap):
{roadmap_text}

Histórico recente (work-log, últimas {len(recent)} entradas):
{wl_lines or "(vazio)"}

Gere as top {k} tarefas mais plausíveis para a próxima sessão de trabalho deste projeto.
"""


def _call_anthropic_urllib(api_key: str, user_prompt: str) -> list[dict]:
    payload = json.dumps(
        {
            "model": MODEL,
            "max_tokens": MAX_TOKENS,
            "system": _SYSTEM_PROMPT,
            "messages": [{"role": "user", "content": user_prompt}],
        }
    ).encode("utf-8")

    req = urllib.request.Request(
        ANTHROPIC_API_URL,
        data=payload,
        headers={
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        },
        method="POST",
    )

    with urllib.request.urlopen(req, timeout=30) as resp:
        body = json.loads(resp.read().decode("utf-8"))

    text = body["content"][0]["text"].strip()
    # Remove possível markdown code fence
    if text.startswith("```"):
        text = re.sub(r"^```[a-z]*\n?", "", text)
        text = re.sub(r"\n?```$", "", text)
    return json.loads(text)


def _call_anthropic_httpx(api_key: str, user_prompt: str) -> list[dict]:
    import httpx  # type: ignore

    payload = {
        "model": MODEL,
        "max_tokens": MAX_TOKENS,
        "system": _SYSTEM_PROMPT,
        "messages": [{"role": "user", "content": user_prompt}],
    }
    resp = httpx.post(
        ANTHROPIC_API_URL,
        json=payload,
        headers={
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
        },
        timeout=30,
    )
    resp.raise_for_status()
    text = resp.json()["content"][0]["text"].strip()
    if text.startswith("```"):
        import re

        text = re.sub(r"^```[a-z]*\n?", "", text)
        text = re.sub(r"\n?```$", "", text)
    return json.loads(text)


def predict(
    project: str,
    entries: list[dict],
    roadmap: dict[str, Any],
    state: dict[str, Any],
    k: int = 5,
) -> tuple[list[dict], str]:
    """Retorna (predictions, source) onde source é 'llm' ou 'fallback'."""

    api_key = os.environ.get("ANTHROPIC_API_KEY", "").strip()

    # Tenta LLM
    if api_key:
        wl_text = "\n".join(e["description"] for e in entries[:30])
        cache_key = _cache_key(project, wl_text)
        cached = _read_cache(cache_key)
        if cached:
            return cached, "llm-cache"

        user_prompt = _build_user_prompt(project, entries, roadmap, state, k)
        try:
            if _HAS_HTTPX:
                preds = _call_anthropic_httpx(api_key, user_prompt)
            else:
                preds = _call_anthropic_urllib(api_key, user_prompt)

            # Normaliza e valida mínimos
            valid: list[dict] = []
            for item in preds:
                if isinstance(item, dict) and "description" in item:
                    item.setdefault("rank", len(valid) + 1)
                    item.setdefault("confidence", 0.5)
                    item.setdefault("uncertainty", "média")
                    item.setdefault("type", "task")
                    item.setdefault("rationale", "gerado por LLM")
                    valid.append(item)

            if valid:
                _write_cache(cache_key, valid[:k])
                return valid[:k], "llm"

        except Exception as exc:
            # Falha soft — cai no fallback
            print(f"[predictor] Aviso: LLM indisponível ({exc}), usando fallback determinístico.")

    preds = _fallback_predict(project, entries, roadmap, state, k)
    return preds, "fallback"
