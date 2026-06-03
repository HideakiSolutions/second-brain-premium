#!/usr/bin/env python3
"""
style_validator.py — valida coerência estilística de um rascunho contra o
fingerprint empírico em _bootstrap/agentic/style/fingerprint.json.

Score 0-100. Violações duras (rejeitadas com nota ≤60). Alertas leves.

Uso:
  echo "<rascunho>" | python3 style_validator.py [--format json|md]
  python3 style_validator.py --file rascunho.md [--format json|md]
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

VAULT_ROOT = Path(__file__).resolve().parents[3]
FINGERPRINT_PATH = VAULT_ROOT / "_bootstrap" / "agentic" / "style" / "fingerprint.json"


# Tropos canônicos da persona (mesmas regex do profiler)
TROPE_PATTERNS = {
    "contraste_nao_e": re.compile(r"\bn[aã]o\s+[eé]\s+[A-Za-zÀ-ú0-9_\-]+,\s+[eé]\s", re.IGNORECASE),
    "inversao_problema": re.compile(r"\bo\s+problema\s+n[aã]o\s+[eé]\b", re.IGNORECASE),
    "inversao_curta": re.compile(r"\bn[aã]o\s+[eé]\s+[A-Za-zÀ-ú]+\b[,\.\s—-]+[eé]\s+[A-Za-zÀ-ú]+", re.IGNORECASE),
    "amplificacao": re.compile(r"\b(escala|n[aã]o)\s+(cria|resolve|aparece|gera).{0,30}(exp[oõ]e|amplifica|revela)", re.IGNORECASE),
    "tese_amplifica_expoe": re.compile(r"\b(amplifica|exp[oõ]e|revela|expoe)\b", re.IGNORECASE),
}

# Aberturas tipicamente "corporate" a evitar
CORPORATE_OPENINGS = [
    r"^neste\s+(post|artigo|texto)\b",
    r"^vou\s+(falar|explicar|abordar)\s+sobre\b",
    r"^espero\s+que\b",
    r"^[oó]tima\s+(pergunta|reflex[aã]o)\b",
    r"^bem-vindos?\b",
    r"^hoje\s+vamos\b",
]
CORPORATE_OPENING_RE = re.compile("|".join(CORPORATE_OPENINGS), re.IGNORECASE)


def load_fingerprint() -> dict:
    if not FINGERPRINT_PATH.exists():
        raise SystemExit(
            f"[style-validator] fingerprint ausente: {FINGERPRINT_PATH}\n"
            f"Rode primeiro: bash .claude/scripts/style-profile.sh"
        )
    return json.loads(FINGERPRINT_PATH.read_text(encoding="utf-8"))


def strip_frontmatter(text: str) -> str:
    if text.startswith("---\n"):
        end = text.find("\n---\n", 4)
        if end != -1:
            return text[end + 5 :]
    return text


def split_paragraphs(text: str) -> list[str]:
    paras = re.split(r"\n\n+", text.strip())
    return [p.strip() for p in paras if p.strip()]


def count_em_dashes(text: str) -> int:
    return text.count("—")


def has_closing_question(text: str) -> bool:
    paras = split_paragraphs(text)
    if not paras:
        return False
    return paras[-1].rstrip().endswith("?")


def has_corporate_opening(text: str) -> bool:
    paras = split_paragraphs(text)
    if not paras:
        return False
    first = paras[0].strip().splitlines()[0] if paras[0] else ""
    return bool(CORPORATE_OPENING_RE.search(first))


def count_tropes(text: str) -> dict[str, int]:
    return {name: len(pat.findall(text)) for name, pat in TROPE_PATTERNS.items()}


def words(text: str) -> list[str]:
    return re.findall(r"\b\w+\b", text)


def score_dimension(actual: float, fingerprint: dict, key: str) -> float:
    """Distância normalizada relativa ao fingerprint."""
    expected = fingerprint.get("mean", fingerprint.get(key + "_mean", 0))
    std = fingerprint.get("std", expected * 0.5 if expected else 1)
    if std == 0:
        std = 1
    z = abs(actual - expected) / std
    # Score: 100 quando z=0; cai para 50 quando z=2; ~0 quando z=4+
    return max(0.0, 100.0 - 25 * z)


def validate(text: str, fingerprint: dict) -> dict:
    body = strip_frontmatter(text)
    word_list = words(body)
    word_count = len(word_list)
    paras = split_paragraphs(body)
    para_count = len(paras)
    em_count = count_em_dashes(body)
    tropes = count_tropes(body)
    total_tropes = sum(tropes.values())
    closing_q = has_closing_question(body)
    corporate = has_corporate_opening(body)

    fp_word = fingerprint.get("word_count", {})
    fp_para = fingerprint.get("paragraph_stats", {})
    fp_em = fingerprint.get("em_dash", {})
    fp_tropes = fingerprint.get("tropes", {})

    # Sub-scores (cada um 0-100)
    score_words = score_dimension(word_count, fp_word, "word_count") if word_count > 0 else 0
    score_paras = score_dimension(para_count, {"mean": fp_para.get("mean_per_article", 4), "std": 2}, "paras") if para_count > 0 else 0

    # Em-dashes: penalty if > expected mean + std
    em_max = fp_em.get("mean", 4) + 5
    score_em = 100.0 if em_count <= em_max else max(0.0, 100 - (em_count - em_max) * 10)

    # Tropos: comparar total observado com total/artigo do fingerprint
    expected_total_tropes = sum(t.get("mean", 0) for t in fp_tropes.values()) if fp_tropes else 2
    if expected_total_tropes < 1:
        expected_total_tropes = 2
    tropes_ratio = min(2.0, total_tropes / expected_total_tropes) if expected_total_tropes else 0
    score_tropes = min(100.0, tropes_ratio * 100)

    score_closing = 100.0 if closing_q else 50.0
    score_opening = 0.0 if corporate else 100.0

    # Score global ponderado
    weights = {
        "words": 0.15,
        "paragraphs": 0.10,
        "em_dash": 0.15,
        "tropes": 0.30,
        "closing": 0.15,
        "opening": 0.15,
    }
    parts = {
        "words": score_words,
        "paragraphs": score_paras,
        "em_dash": score_em,
        "tropes": score_tropes,
        "closing": score_closing,
        "opening": score_opening,
    }
    score_global = sum(parts[k] * w for k, w in weights.items())

    # Violações duras (bloqueiam aprovação)
    hard_violations: list[str] = []
    if em_count > em_max + 5:
        hard_violations.append(f"em-dashes excessivos: {em_count} (limite: {int(em_max + 5)})")
    if total_tropes == 0:
        hard_violations.append("zero tropos da persona detectados (esperado ≥2 — contraste/inversão/amplificação)")
    if corporate:
        hard_violations.append(f"abertura corporate detectada na primeira frase: '{paras[0][:80] if paras else ''}'")
    if not closing_q and word_count > 200:
        hard_violations.append("artigo longo (>200 palavras) sem pergunta no fechamento")

    # Alertas leves
    soft_warnings: list[str] = []
    if word_count < fp_word.get("p25", 100) * 0.5:
        soft_warnings.append(f"texto curto: {word_count} palavras (mediana fingerprint: {fp_word.get('p50', 'N/A')})")
    if word_count > fp_word.get("p75", 300) * 1.8:
        soft_warnings.append(f"texto longo: {word_count} palavras (p75 fingerprint: {fp_word.get('p75', 'N/A')})")
    if 0 < em_count <= 2:
        pass  # OK
    elif em_count > em_max:
        soft_warnings.append(f"em-dashes acima da média: {em_count} (média fingerprint: {fp_em.get('mean', 'N/A')})")
    if total_tropes < expected_total_tropes * 0.5:
        soft_warnings.append(
            f"baixa densidade de tropos: {total_tropes} encontrados (esperado ~{expected_total_tropes:.1f})"
        )

    return {
        "score_global": round(score_global, 1),
        "breakdown": {k: round(v, 1) for k, v in parts.items()},
        "hard_violations": hard_violations,
        "soft_warnings": soft_warnings,
        "metrics": {
            "word_count": word_count,
            "paragraph_count": para_count,
            "em_dash_count": em_count,
            "tropes_detected": tropes,
            "total_tropes": total_tropes,
            "closing_question": closing_q,
            "corporate_opening": corporate,
        },
        "fingerprint_articles": fingerprint.get("articles_analyzed", 0),
    }


def render_md(report: dict) -> str:
    lines = [
        f"# Style Validation Report",
        "",
        f"**Score global:** {report['score_global']}/100  ·  fingerprint: {report['fingerprint_articles']} artigos",
        "",
        "## Breakdown",
        "",
        "| Dimensão | Score |",
        "|---|---|",
    ]
    for k, v in report["breakdown"].items():
        lines.append(f"| {k} | {v} |")
    lines.append("")

    m = report["metrics"]
    lines.append("## Métricas")
    lines.append("")
    lines.append(f"- Palavras: {m['word_count']}")
    lines.append(f"- Parágrafos: {m['paragraph_count']}")
    lines.append(f"- Em-dashes: {m['em_dash_count']}")
    lines.append(f"- Tropos detectados: {m['total_tropes']}")
    for tname, tcount in m["tropes_detected"].items():
        if tcount:
            lines.append(f"  - {tname}: {tcount}")
    lines.append(f"- Fechamento com pergunta: {'sim' if m['closing_question'] else 'NÃO'}")
    lines.append(f"- Abertura corporate: {'SIM (problema)' if m['corporate_opening'] else 'não'}")
    lines.append("")

    if report["hard_violations"]:
        lines.append("## ✗ Violações duras (bloqueiam aprovação)")
        lines.append("")
        for v in report["hard_violations"]:
            lines.append(f"- {v}")
        lines.append("")

    if report["soft_warnings"]:
        lines.append("## ⚠ Alertas leves")
        lines.append("")
        for w in report["soft_warnings"]:
            lines.append(f"- {w}")
        lines.append("")

    if not report["hard_violations"] and not report["soft_warnings"]:
        lines.append("## ✓ Coerente com a voz")
        lines.append("")

    if report["hard_violations"] or report["score_global"] < 60:
        lines.append("**Veredicto:** REJEITADO. Reescrever conforme persona antes de publicar.")
    elif report["score_global"] < 75:
        lines.append("**Veredicto:** ACEITÁVEL com ressalvas. Avaliar alertas leves.")
    else:
        lines.append("**Veredicto:** ALINHADO com a voz.")
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--file", help="caminho de arquivo .md (default: stdin)")
    ap.add_argument("--format", choices=["json", "md"], default="md")
    args = ap.parse_args()

    if args.file:
        text = Path(args.file).read_text(encoding="utf-8")
    else:
        text = sys.stdin.read()

    if not text.strip():
        print("[style-validator] sem texto para validar (stdin vazio?)", file=sys.stderr)
        return 1

    fingerprint = load_fingerprint()
    report = validate(text, fingerprint)

    if args.format == "json":
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(render_md(report))

    # Exit 0 sempre — o validador apenas REPORTA; quem decide bloquear é o caller
    return 0


if __name__ == "__main__":
    sys.exit(main())
