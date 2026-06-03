#!/usr/bin/env python3
"""
Style Profiler — analisa os artigos publicados do usuário e gera fingerprint estatístico.

Saída: _bootstrap/agentic/style/fingerprint.json

Uso:
    python3 _bootstrap/agentic/style/profiler.py
    python3 _bootstrap/agentic/style/profiler.py --articles-dir _content/articles --output _bootstrap/agentic/style/fingerprint.json
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from statistics import mean, quantiles, stdev

# ---------------------------------------------------------------------------
# Configuração
# ---------------------------------------------------------------------------

VAULT_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_ARTICLES_DIR = VAULT_ROOT / "_content" / "articles"
DEFAULT_OUTPUT = Path(__file__).parent / "fingerprint.json"

# Stopwords PT-BR comuns para filtrar nos n-gramas
STOPWORDS = {
    "a", "as", "o", "os", "e", "é", "em", "de", "da", "do", "das", "dos",
    "para", "por", "com", "um", "uma", "uns", "umas", "que", "se", "não",
    "mais", "ao", "aos", "à", "às", "no", "na", "nos", "nas", "como",
    "ou", "mas", "pelo", "pela", "pelos", "pelas", "este", "esta",
    "isso", "aqui", "ali", "já", "ainda", "também", "muito",
    "quando", "onde", "quem", "qual", "quais", "seu", "sua", "seus", "suas",
    "meu", "minha", "nosso", "nossa", "ser", "ter", "fazer", "estar",
    "foi", "são", "tem", "há", "vai", "vão", "ele", "ela", "eles", "elas",
    "eu", "você", "nós", "isto", "aquilo",
}

# Palavras de gancho de abertura (abertura observacional vs assertiva)
HOOK_WORDS = {
    "observacional": [
        "todo mundo", "todo o mundo", "a maioria", "todo time", "a indústria",
        "o mercado", "os times", "as empresas", "toda empresa", "você sabe",
        "quando", "enquanto", "se você", "parece", "sempre que",
    ],
    "assertiva": [
        "tecnologia", "ia", "agente", "spec", "arquitetura", "contexto",
        "o problema", "o erro", "a ilusão", "a falsa", "adotar", "crescimento",
        "IA-first", "spec-driven", "comece", "worktrees",
    ],
}

# ---------------------------------------------------------------------------
# Extração de texto
# ---------------------------------------------------------------------------

def strip_frontmatter(text: str) -> str:
    """Remove frontmatter YAML."""
    if text.startswith("---"):
        end = text.find("---", 3)
        if end != -1:
            return text[end + 3:].lstrip()
    return text


def strip_code_blocks(text: str) -> str:
    """Remove blocos de código delimitados por ``` ou indentação."""
    # Remove fenced code blocks
    text = re.sub(r"```.*?```", "", text, flags=re.DOTALL)
    return text


def strip_markdown(text: str) -> str:
    """Remove marcações markdown (headers, links, emphasis)."""
    # Remove headers
    text = re.sub(r"^#{1,6}\s+", "", text, flags=re.MULTILINE)
    # Remove WikiLinks [[...]]
    text = re.sub(r"\[\[([^\]]+)\]\]", r"\1", text)
    # Remove links [text](url)
    text = re.sub(r"\[([^\]]+)\]\([^\)]+\)", r"\1", text)
    # Remove emphasis
    text = re.sub(r"[*_]{1,2}([^*_]+)[*_]{1,2}", r"\1", text)
    # Remove YAML field lines (key: value) at start
    text = re.sub(r"^[a-z_]+:\s+.*$", "", text, flags=re.MULTILINE)
    # Remove bullet points
    text = re.sub(r"^\s*[-*→]\s+", "", text, flags=re.MULTILINE)
    # Remove numbered list markers
    text = re.sub(r"^\s*\d+\.\s+", "", text, flags=re.MULTILINE)
    # Remove table separators
    text = re.sub(r"^\|[-| ]+\|$", "", text, flags=re.MULTILINE)
    # Remove table rows
    text = re.sub(r"\|", " ", text)
    return text


def extract_text_sections(raw: str) -> dict[str, str]:
    """
    Extrai seções relevantes: Resumo, Argumento Central, Estrutura, Texto da Postagem.
    Retorna dict com section_name -> text.
    """
    sections: dict[str, str] = {}
    current_section = "_preamble"
    current_lines: list[str] = []

    for line in raw.split("\n"):
        m = re.match(r"^##\s+(.+)$", line)
        if m:
            sections[current_section] = "\n".join(current_lines)
            current_section = m.group(1).strip()
            current_lines = []
        else:
            current_lines.append(line)
    sections[current_section] = "\n".join(current_lines)
    return sections


def get_body_text(raw: str) -> str:
    """
    Retorna o texto limpo de um artigo, priorizando seções de corpo real.
    Usa: Texto da Postagem > Resumo + Argumento Central + Estrutura do Artigo.
    """
    no_front = strip_frontmatter(raw)
    no_code = strip_code_blocks(no_front)
    sections = extract_text_sections(no_code)

    # Postagens têm "Texto da Postagem"
    body_keys = [
        "Texto da Postagem",
        "Resumo",
        "Argumento Central",
        "Estrutura do Artigo",
        "Estrutura da Postagem",
        "Learnings Extraídos",
    ]
    parts = []
    for key in body_keys:
        if key in sections and sections[key].strip():
            parts.append(sections[key].strip())

    if not parts:
        # Fallback: tudo
        parts = [no_code]

    combined = "\n\n".join(parts)
    return strip_markdown(combined)


# ---------------------------------------------------------------------------
# Análise estatística
# ---------------------------------------------------------------------------

def count_words(text: str) -> int:
    return len(text.split())


def get_paragraphs(text: str) -> list[str]:
    """Retorna parágrafos não-vazios."""
    return [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]


def para_word_counts(paragraphs: list[str]) -> list[int]:
    return [count_words(p) for p in paragraphs]


def analyze_tropes(text: str) -> dict[str, int]:
    """Conta ocorrências de tropos de persona."""
    tropes: dict[str, int] = {}

    # Contraste: "não é X, é Y" / "não é X — é Y" / "não X, mas Y"
    tropes["contraste_nao_e"] = len(re.findall(
        r"não\s+(?:é|é\s+\w+,?\s+)?[^.?!]{3,40}[,—]\s*(?:é|mas)\s+",
        text, re.IGNORECASE
    ))

    # Inversão: "o problema não é A, é B"
    tropes["inversao_problema"] = len(re.findall(
        r"o\s+problema\s+não\s+é",
        text, re.IGNORECASE
    ))

    # Amplificação: "X não cria, expõe" / "X não resolve, amplifica"
    tropes["amplificacao"] = len(re.findall(
        r"\w+\s+não\s+\w+[,\.]\s+\w+",
        text, re.IGNORECASE
    ))

    # "tecnologia amplifica" / "IA amplifica" / "escala expõe" / "crescimento expõe"
    tropes["tese_amplifica_expoe"] = len(re.findall(
        r"(?:tecnologia|ia|escala|crescimento|agente)\s+(?:amplifica|expõe|não\s+resolve|não\s+cria)",
        text, re.IGNORECASE
    ))

    # "não é X. É Y." — frase curta de inversão
    tropes["inversao_curta"] = len(re.findall(
        r"não\s+é\s+\w[\w\s]{2,30}\.\s+[EÉ]",
        text, re.IGNORECASE
    ))

    return tropes


def has_closing_question(text: str) -> bool:
    """Verifica se o último parágrafo não-vazio termina com '?'."""
    paragraphs = get_paragraphs(text)
    if not paragraphs:
        return False
    last = paragraphs[-1].strip()
    return last.endswith("?")


def count_em_dashes(text: str) -> int:
    """Conta travessões '—' no texto."""
    return text.count("—")


def analyze_connectives(text: str) -> dict[str, float]:
    """Densidade de conectivos sobre total de palavras."""
    words = text.lower().split()
    total = len(words) if words else 1

    connectives = [
        "mas", "porém", "contudo", "entretanto", "todavia",
        "na prática", "isso é", "ou seja", "portanto", "logo",
        "no entanto", "assim", "então", "pois", "porque",
    ]

    count = 0
    text_lower = text.lower()
    for conn in connectives:
        count += len(re.findall(r"\b" + re.escape(conn) + r"\b", text_lower))

    return {
        "count": count,
        "density": round(count / total, 4),
    }


def get_ngrams(text: str, n: int) -> list[tuple[str, ...]]:
    """Gera n-gramas filtrados de stopwords."""
    words = re.findall(r"[a-záàâãéêíóôõúüç\-]+", text.lower())
    filtered = [w for w in words if w not in STOPWORDS and len(w) > 2]
    return [tuple(filtered[i:i+n]) for i in range(len(filtered) - n + 1)]


def detect_opening_type(text: str) -> str:
    """Heurística: primeira frase é observacional ou assertiva?"""
    first_para = get_paragraphs(text)
    if not first_para:
        return "unknown"
    first_sentence = first_para[0].split(".")[0].lower()

    for phrase in HOOK_WORDS["observacional"]:
        if phrase in first_sentence:
            return "observacional"
    return "assertiva"


def line_length_ratio(text: str) -> dict[str, float]:
    """Razão de linhas curtas (≤80 chars) vs longas."""
    lines = [ln for ln in text.split("\n") if ln.strip()]
    if not lines:
        return {"short_ratio": 0.0, "long_ratio": 0.0}
    short = sum(1 for ln in lines if len(ln.strip()) <= 80)
    return {
        "short_ratio": round(short / len(lines), 3),
        "long_ratio": round(1 - short / len(lines), 3),
        "total_lines": len(lines),
    }


# ---------------------------------------------------------------------------
# Profiler principal
# ---------------------------------------------------------------------------

def profile_article(path: Path) -> dict | None:
    try:
        raw = path.read_text(encoding="utf-8")
    except Exception as e:
        print(f"[WARN] Não foi possível ler {path}: {e}", file=sys.stderr)
        return None

    body = get_body_text(raw)
    if not body.strip() or count_words(body) < 50:
        print(f"[WARN] Conteúdo insuficiente em {path.name}, pulando.", file=sys.stderr)
        return None

    paragraphs = get_paragraphs(body)
    para_counts = para_word_counts(paragraphs)

    return {
        "file": path.name,
        "word_count": count_words(body),
        "paragraph_count": len(paragraphs),
        "para_word_counts": para_counts,
        "tropes": analyze_tropes(body),
        "has_closing_question": has_closing_question(body),
        "em_dash_count": count_em_dashes(raw),  # no raw para pegar o original
        "connectives": analyze_connectives(body),
        "opening_type": detect_opening_type(body),
        "line_lengths": line_length_ratio(body),
        "bigrams": get_ngrams(body, 2),
        "trigrams": get_ngrams(body, 3),
    }


def build_fingerprint(articles_dir: Path, output: Path) -> dict:
    files = sorted(articles_dir.glob("*.md"))
    print(f"[INFO] Encontrados {len(files)} arquivos em {articles_dir}", file=sys.stderr)

    profiles = []
    for f in files:
        p = profile_article(f)
        if p:
            profiles.append(p)
            print(f"[OK]   {f.name} — {p['word_count']} palavras, {p['paragraph_count']} parágrafos", file=sys.stderr)

    if not profiles:
        print("[ERROR] Nenhum artigo analisado com sucesso.", file=sys.stderr)
        sys.exit(1)

    n = len(profiles)

    # Distribuição de palavras por artigo
    word_counts = [p["word_count"] for p in profiles]
    # Distribuição de parágrafos
    all_para_counts = [c for p in profiles for c in p["para_word_counts"]]

    def safe_stdev(lst: list[float]) -> float:
        return round(stdev(lst), 2) if len(lst) > 1 else 0.0

    def qs(lst: list[float]) -> dict[str, float]:
        if not lst:
            return {"p25": 0, "p50": 0, "p75": 0}
        ql = quantiles(lst, n=4)
        return {"p25": round(ql[0], 2), "p50": round(ql[1], 2), "p75": round(ql[2], 2)}

    # N-gramas agregados
    bigram_counter: Counter = Counter()
    trigram_counter: Counter = Counter()
    for p in profiles:
        bigram_counter.update(p["bigrams"])
        trigram_counter.update(p["trigrams"])

    top_bigrams = [{"ngram": list(k), "count": v} for k, v in bigram_counter.most_common(30)]
    top_trigrams = [{"ngram": list(k), "count": v} for k, v in trigram_counter.most_common(30)]

    # Tropos agregados
    trope_keys = set()
    for p in profiles:
        trope_keys.update(p["tropes"].keys())

    tropes_agg: dict[str, dict] = {}
    for key in trope_keys:
        vals = [p["tropes"].get(key, 0) for p in profiles]
        tropes_agg[key] = {
            "mean": round(mean(vals), 3),
            "total": sum(vals),
            "articles_with_trope": sum(1 for v in vals if v > 0),
            "rate": round(sum(1 for v in vals if v > 0) / n, 3),
        }

    # Fechamento com pergunta
    closing_q_count = sum(1 for p in profiles if p["has_closing_question"])

    # Em-dashes
    em_dash_vals = [p["em_dash_count"] for p in profiles]

    # Conectivos
    conn_densities = [p["connectives"]["density"] for p in profiles]

    # Tipo de abertura
    opening_types = Counter(p["opening_type"] for p in profiles)

    # Razão de linhas curtas
    short_ratios = [p["line_lengths"]["short_ratio"] for p in profiles]

    fingerprint = {
        "generated_at": datetime.now(UTC).isoformat(),
        "articles_analyzed": n,
        "article_files": [p["file"] for p in profiles],
        "word_count": {
            "mean": round(mean(word_counts), 1),
            "std": safe_stdev(word_counts),
            **qs(word_counts),
        },
        "paragraph_stats": {
            "mean_per_article": round(mean([len(p["para_word_counts"]) for p in profiles]), 1),
            "words_per_para": {
                "mean": round(mean(all_para_counts), 1),
                "std": safe_stdev(all_para_counts),
                **qs(all_para_counts),
            },
        },
        "tropes": tropes_agg,
        "closing_question": {
            "count": closing_q_count,
            "rate": round(closing_q_count / n, 3),
        },
        "em_dash": {
            "mean": round(mean(em_dash_vals), 2),
            "max": max(em_dash_vals),
            "articles_over_2": sum(1 for v in em_dash_vals if v > 2),
            "target_max_per_article": 2,
        },
        "connectives": {
            "density_mean": round(mean(conn_densities), 4),
            "density_std": safe_stdev(conn_densities),
            **qs(conn_densities),
        },
        "opening_type": dict(opening_types),
        "line_length": {
            "short_ratio_mean": round(mean(short_ratios), 3),
            "short_ratio_std": safe_stdev(short_ratios),
        },
        "top_bigrams": top_bigrams,
        "top_trigrams": top_trigrams,
    }

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(fingerprint, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n[OK] Fingerprint gerado: {output} ({n} artigos analisados)", file=sys.stderr)
    return fingerprint


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="Style Profiler — second brain")
    parser.add_argument("--articles-dir", type=Path, default=DEFAULT_ARTICLES_DIR)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    fp = build_fingerprint(args.articles_dir, args.output)
    print(json.dumps(fp, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
