"""
heuristics.py — implementa as 7 heurísticas de curação do vault.

H1: Cluster de learnings -> sugerir novo pattern
H2: Notas órfãs (sem backlinks) -> propor merge/archive
H3: Tag livre frequente -> propor entrada na taxonomia
H4: Decisão active antiga -> verificar se ADR mais novo contradiz
H5: Pattern over-implementation -> padrão usado em 3+ projetos sem ADR
H6: Decision contradiction via graph -> dois ADRs referenciando mesmo pattern com gap >60d
H7: Cross-project pattern adoption gap -> padrão usado em N projetos fintech mas ausente em outro
"""

from __future__ import annotations

import os
import re
import sys
from pathlib import Path
from typing import Any

# Resolve vault root (3 levels up from this file: curator/ -> agentic/ -> _bootstrap/ -> vault)
VAULT_ROOT = Path(__file__).resolve().parents[3]

# ---- Taxonomia de tags válidas (sync com graph_metrics.py) -----
LAYER_TAGS = {
    "pattern", "feature", "decision", "learning", "project", "core",
    "infra", "content", "source", "index", "memory", "session", "wiki",
}
MATURITY_TAGS = {
    "production", "beta", "mvp", "spike", "candidate",
    "deprecated", "archived", "active", "wip",
}
DOMAIN_TAGS = {
    "fintech", "trading", "payments", "compliance", "ai-sdlc", "ai-agents",
    "infra-eng", "devtools", "knowledge-mgmt", "observability", "security",
    "data-platform", "messaging", "frontend", "backend", "mobile", "platform",
    "governance", "forex", "crypto", "events", "automation", "voice-text",
    "architecture", "mandatory",
}
STACK_TAGS = {
    "dotnet", "csharp", "java", "spring-boot", "php", "laravel", "python",
    "typescript", "react", "react-native", "flutter", "node", "bun", "go", "rust",
    "orleans", "mediatr", "marten", "entity-framework", "dapper",
    "kafka", "rabbitmq", "redis", "mongodb", "postgres", "mysql", "mssql",
    "sqlite", "clickhouse", "falkordb", "qdrant",
    "docker", "kubernetes", "argocd", "helm", "kustomize", "kong", "yarp",
    "obsidian", "notion", "claude-code", "mcp",
    "temporal", "hangfire", "n8n",
}
RISK_TAGS = {
    "regulated", "lgpd", "pci", "aml", "sox", "iso27001", "gdpr",
    "high-blast-radius", "irreversible", "multi-tenant", "cross-project",
}
PROJECT_FILE_TYPES = {
    "work-log", "decisions", "gotchas", "roadmap", "state", "modules",
    "integrations", "agents", "skills", "workflows", "servers", "policies",
    "structure", "index",
}
VALID_TAGS = LAYER_TAGS | MATURITY_TAGS | DOMAIN_TAGS | STACK_TAGS | RISK_TAGS | PROJECT_FILE_TYPES

WIKILINK_RE = re.compile(r"\[\[([^\]]+)\]\]")
CODE_FENCE_RE = re.compile(r"^(```|~~~)")


# ---------- helpers ----------

def parse_frontmatter(text: str) -> dict[str, str]:
    if not text.startswith("---\n"):
        return {}
    end = text.find("\n---\n", 4)
    if end == -1:
        return {}
    fm: dict[str, str] = {}
    for line in text[4:end].splitlines():
        if ":" not in line:
            continue
        k, v = line.split(":", 1)
        fm[k.strip()] = v.strip()
    return fm


def parse_tags(fm: dict[str, str]) -> list[str]:
    val = fm.get("tags", "").strip()
    if not val:
        return []
    if val.startswith("[") and val.endswith("]"):
        inner = val[1:-1]
        return [t.strip().strip('"').strip("'") for t in inner.split(",") if t.strip()]
    return [t.strip() for t in val.split(",") if t.strip()]


def strip_frontmatter(text: str) -> str:
    if text.startswith("---\n"):
        end = text.find("\n---\n", 4)
        if end != -1:
            return text[end + 5:]
    return text


def first_section_text(text: str, max_chars: int = 400) -> str:
    """Retorna título + primeira seção de prosa (sem frontmatter)."""
    body = strip_frontmatter(text)
    lines = []
    in_code = False
    for line in body.split("\n"):
        if CODE_FENCE_RE.match(line):
            in_code = not in_code
            continue
        if in_code:
            continue
        lines.append(line)
        if sum(len(ln) for ln in lines) >= max_chars:
            break
    return "\n".join(lines)[:max_chars]


def collect_md_files(directory: Path) -> list[Path]:
    return sorted(directory.glob("*.md"))


def parse_date(date_str: str) -> int | None:
    """Retorna date como int YYYYMMDD ou None se inválido."""
    try:
        clean = date_str.strip().strip('"')
        parts = clean.split("-")
        if len(parts) == 3:
            return int(clean.replace("-", ""))
    except (ValueError, AttributeError):
        pass
    return None


def slugify(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_]+", "-", text)
    return text[:60]


def pattern_names() -> set[str]:
    """Nomes de patterns existentes (stems dos arquivos)."""
    p = VAULT_ROOT / "_patterns"
    if not p.exists():
        return set()
    return {f.stem.lower() for f in p.glob("*.md") if not f.stem.startswith("_")}


def count_backlinks(slug: str, all_files: list[Path]) -> int:
    """Conta quantos arquivos linkam para [[slug]] ou [[filename]]."""
    count = 0
    pattern_re = re.compile(r"\[\[" + re.escape(slug) + r"(\|[^\]]+)?\]\]", re.IGNORECASE)
    for fpath in all_files:
        try:
            text = fpath.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        if pattern_re.search(text):
            count += 1
    return count


def all_vault_md_files() -> list[Path]:
    out = []
    skip = {".git", "node_modules", ".obsidian", ".second-brain", ".logs", "_references"}
    for root, dirs, files in os.walk(VAULT_ROOT):
        rel = Path(root).relative_to(VAULT_ROOT)
        if rel.parts and rel.parts[0] in skip:
            dirs[:] = []
            continue
        for f in files:
            if f.endswith(".md"):
                out.append(Path(root) / f)
    return out


# ---------- H1: cluster de learnings ----------

def h1_learning_clusters(store_module: Any) -> list[dict]:
    """
    Para cada learning, embeds titulo+1a secao, busca top-10 vizinhos.
    Se >=3 outros learnings tem score >0.65 e nenhum pattern similar existe,
    propoe criacao de novo pattern.
    """
    proposals = []
    learnings_dir = VAULT_ROOT / "_learnings"
    if not learnings_dir.exists():
        return proposals

    files = [f for f in collect_md_files(learnings_dir) if not f.stem.startswith(".")]
    existing_patterns = pattern_names()
    visited_clusters: set[frozenset] = set()

    for learning_file in files:
        try:
            text = learning_file.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue

        fm = parse_frontmatter(text)
        # Pular arquivos sem título claro
        title = fm.get("title", learning_file.stem)
        snippet = title + "\n" + first_section_text(text)

        try:
            vec = store_module.embed(snippet)
        except Exception as e:
            print(f"[curator/H1] embed failed for {learning_file.name}: {e}", file=sys.stderr)
            continue

        try:
            results = store_module.search(
                vec,
                k=15,
                filter_={"must": [{"key": "kind", "match": {"value": "learnings"}}]},
            )
        except Exception as e:
            print(f"[curator/H1] search failed: {e}", file=sys.stderr)
            continue

        # Filtra vizinhos com score alto, excluindo o próprio arquivo
        neighbors = [
            r for r in results
            if r.get("score", 0) > 0.65
            and r.get("payload", {}).get("source_file", "") != str(learning_file.relative_to(VAULT_ROOT))
        ]

        if len(neighbors) < 3:
            continue

        # Extrair slugs/nomes dos vizinhos para dedup
        neighbor_slugs = []
        for n in neighbors[:5]:
            src = n.get("payload", {}).get("source_file", "")
            slug = Path(src).stem if src else ""
            if slug:
                neighbor_slugs.append(slug)

        cluster_key = frozenset([learning_file.stem] + neighbor_slugs[:3])
        if cluster_key in visited_clusters:
            continue
        visited_clusters.add(cluster_key)

        # Verificar se ja existe pattern com nome similar
        base_slug = slugify(learning_file.stem.replace("-", " ").split("-")[0])
        if any(base_slug in p or p in base_slug for p in existing_patterns):
            continue

        # Gerar slug para pattern proposto
        # Usar palavras em comum entre o learning e vizinhos
        words = [w for w in re.split(r"[-_\s]+", learning_file.stem) if len(w) > 3]
        pattern_slug = "-".join(words[:4]) if words else learning_file.stem[:40]

        wiki_refs = [f"[[{learning_file.stem}]]"] + [f"[[{s}]]" for s in neighbor_slugs[:4]]
        proposals.append({
            "type": "H1",
            "title": f"Cluster de learnings sugere novo pattern: `{pattern_slug}`",
            "body": (
                f"Os learnings abaixo têm similaridade semantica alta (score >0.65) "
                f"e nenhum `_pattern/` existente cobre este tema.\n\n"
                f"Considerar criar `_patterns/{pattern_slug}.md` cobrindo:\n"
                + "\n".join(f"- {ref}" for ref in wiki_refs)
            ),
            "hash_key": f"H1:{pattern_slug}",
        })

    return proposals


# ---------- H2: notas orfas ----------

def h2_orphan_notes(store_module: Any) -> list[dict]:
    """
    Para cada decision/learning sem backlinks E updated < 60 dias,
    propoe adicionar como Related em top-3 candidatos ou marcar archived.
    """
    proposals = []

    all_files = all_vault_md_files()
    target_dirs = [VAULT_ROOT / "_decisions", VAULT_ROOT / "_learnings"]

    for target_dir in target_dirs:
        if not target_dir.exists():
            continue
        for fpath in collect_md_files(target_dir):
            if fpath.stem.startswith(".") or fpath.stem.startswith("_"):
                continue
            try:
                text = fpath.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue

            fm = parse_frontmatter(text)
            updated_str = fm.get("updated", fm.get("created", ""))
            updated_int = parse_date(updated_str)
            if updated_int is None:
                continue

            # Se updated < 60 dias do today
            try:
                import datetime as dt
                today = dt.date.today()
                upd = dt.date(int(str(updated_int)[:4]), int(str(updated_int)[4:6]), int(str(updated_int)[6:8]))
                days_diff = (today - upd).days
                if days_diff > 60:
                    continue
            except ValueError:
                continue

            # Contar backlinks
            slug = fpath.stem
            bl = count_backlinks(slug, all_files)
            if bl > 0:
                continue

            # Vector similarity para sugerir candidatos
            title = fm.get("title", slug)
            snippet = title + "\n" + first_section_text(text, 300)
            try:
                vec = store_module.embed(snippet)
                results = store_module.search(vec, k=5)
            except Exception as e:
                print(f"[curator/H2] search failed for {fpath.name}: {e}", file=sys.stderr)
                results = []

            candidates = []
            for r in results:
                src = r.get("payload", {}).get("source_file", "")
                cand_slug = Path(src).stem if src else ""
                if cand_slug and cand_slug != slug and cand_slug not in candidates:
                    candidates.append(cand_slug)
                if len(candidates) >= 3:
                    break

            cand_refs = [f"[[{c}]]" for c in candidates]
            proposals.append({
                "type": "H2",
                "title": f"Nota orfã sem backlinks: `{slug}`",
                "body": (
                    f"`{fpath.relative_to(VAULT_ROOT)}` tem 0 backlinks e foi atualizada recentemente ({updated_str}).\n\n"
                    f"Ações sugeridas:\n"
                    f"- Adicionar como `Related` em: {', '.join(cand_refs) if cand_refs else '_nenhum candidato detectado_'}\n"
                    f"- Ou marcar `status: archived` se não for mais relevante"
                ),
                "hash_key": f"H2:{slug}",
            })

    return proposals


# ---------- H3: tags livres frequentes ----------

def h3_free_tags() -> list[dict]:
    """
    Parse frontmatters de todos os .md, conta tags fora da taxonomia.
    Se uma tag aparece em >=4 arquivos, propoe adicionar a TAG-TAXONOMY.
    """
    proposals = []
    all_files = all_vault_md_files()
    from collections import Counter
    free_tag_counter: Counter = Counter()

    for fpath in all_files:
        try:
            text = fpath.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        fm = parse_frontmatter(text)
        tags = parse_tags(fm)
        for tag in tags:
            if tag not in VALID_TAGS and tag:
                free_tag_counter[tag] += 1

    for tag, count in free_tag_counter.most_common(20):
        if count >= 4:
            proposals.append({
                "type": "H3",
                "title": f"Tag livre frequente: `{tag}` ({count} arquivos)",
                "body": (
                    f"A tag `{tag}` aparece em {count} arquivos mas não está na taxonomia oficial.\n\n"
                    f"Sugestão: adicionar `{tag}` à seção apropriada de "
                    f"`[[TAG-TAXONOMY]]` (`_index/TAG-TAXONOMY.md`).\n\n"
                    f"Verificar se encaixa em: Domínio, Stack, Risco ou criar nova seção."
                ),
                "hash_key": f"H3:{tag}",
            })

    return proposals


# ---------- H4: decisões active antigas ----------

def h4_stale_decisions(store_module: Any) -> list[dict]:
    """
    Para cada decision com status active e created > 120 dias,
    busca ADRs mais recentes que possam contradizer.
    """
    import datetime
    proposals = []
    decisions_dir = VAULT_ROOT / "_decisions"
    if not decisions_dir.exists():
        return proposals

    today = datetime.date.today()
    revocation_words = {"revoga", "substitui", "atualiza", "supersede", "replace", "depreca"}

    for fpath in collect_md_files(decisions_dir):
        if fpath.stem.startswith(".") or fpath.stem.startswith("_"):
            continue
        try:
            text = fpath.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue

        fm = parse_frontmatter(text)
        status = fm.get("status", "").strip().strip('"')
        if status != "active":
            continue

        created_str = fm.get("created", "")
        created_int = parse_date(created_str)
        if created_int is None:
            continue

        try:
            created_date = datetime.date(
                int(str(created_int)[:4]),
                int(str(created_int)[4:6]),
                int(str(created_int)[6:8]),
            )
        except ValueError:
            continue

        age_days = (today - created_date).days
        if age_days <= 120:
            continue

        # Vector search para ADRs mais recentes
        title = fm.get("title", fpath.stem)
        # Pega primeiro H2 do corpo
        body = strip_frontmatter(text)
        h2_match = re.search(r"^##\s+(.+)$", body, re.MULTILINE)
        h2_title = h2_match.group(1) if h2_match else ""
        snippet = title + " " + h2_title

        try:
            vec = store_module.embed(snippet)
            results = store_module.search(
                vec,
                k=10,
                filter_={"must": [{"key": "kind", "match": {"value": "decisions"}}]},
            )
        except Exception as e:
            print(f"[curator/H4] search failed for {fpath.name}: {e}", file=sys.stderr)
            continue

        # Filtrar ADRs mais recentes com palavras de revogação
        contradicting = []
        for r in results:
            payload = r.get("payload", {})
            src = payload.get("source_file", "")
            score = r.get("score", 0)
            if score < 0.55:
                continue
            if src == str(fpath.relative_to(VAULT_ROOT)):
                continue

            cand_path = VAULT_ROOT / src
            cand_created_str = ""
            try:
                cand_text = cand_path.read_text(encoding="utf-8", errors="replace")
                cand_fm = parse_frontmatter(cand_text)
                cand_created_str = cand_fm.get("created", "")
                cand_created_int = parse_date(cand_created_str)
                if cand_created_int is None or cand_created_int <= created_int:
                    continue
                # Verificar palavras de revogação
                cand_body_lower = cand_text.lower()
                if any(w in cand_body_lower for w in revocation_words):
                    contradicting.append((Path(src).stem, score, cand_created_str))
            except OSError:
                continue

        if not contradicting:
            continue

        contra_refs = [f"[[{c[0]}]] (score={c[1]:.2f}, criado={c[2]})" for c in contradicting[:3]]
        proposals.append({
            "type": "H4",
            "title": f"Decisão `active` possivelmente obsoleta: `{fpath.stem}`",
            "body": (
                f"`{fpath.relative_to(VAULT_ROOT)}` está `active` há {age_days} dias.\n\n"
                f"ADRs mais recentes com similaridade semantica alta e termos de revogação:\n"
                + "\n".join(f"- {ref}" for ref in contra_refs)
                + "\n\nSugestão: revisar e atualizar status ou adicionar seção `## Revisão`."
            ),
            "hash_key": f"H4:{fpath.stem}",
        })

    return proposals


# ---------- Graph helpers ----------

def connect_falkor():
    """
    Retorna instância de FalkorClient conectada, ou None se FalkorDB offline.
    Fail-soft: nunca lança exceção.
    """
    try:
        graph_path = Path(__file__).resolve().parents[1] / "graph"
        if str(graph_path) not in sys.path:
            sys.path.insert(0, str(graph_path))
        from falkor_client import FalkorClient  # type: ignore
        client = FalkorClient()
        if client.connect():
            return client
        print("[curator/graph] FalkorDB offline — heurísticas H5/H6/H7 desativadas.", file=sys.stderr)
        return None
    except Exception as e:
        print(f"[curator/graph] Falha ao conectar FalkorDB: {e} — H5/H6/H7 desativadas.", file=sys.stderr)
        return None


# ---------- H5: pattern over-implementation ----------

def h5_pattern_over_implementation() -> list[dict]:
    """
    Patterns usados em >= 3 projetos (via USES_PATTERN) mas com < 3 backlinks de
    Decisions/Learnings via REFERENCES. Indica padrão amplamente adotado mas sem
    documentação formal em ADR.
    """
    proposals = []
    client = connect_falkor()
    if client is None:
        return proposals

    try:
        # Patterns com >= 3 projetos usando-os
        rows = client.query(
            "MATCH (proj:Project)-[:USES_PATTERN]->(p:Pattern) "
            "WITH p, count(proj) AS proj_count "
            "WHERE proj_count >= 3 "
            "RETURN p.id AS slug, p.name AS name, proj_count "
            "ORDER BY proj_count DESC"
        )
        if not rows:
            return proposals

        for row in rows:
            slug = row.get("slug") or row.get("p.id", "")
            proj_count = row.get("proj_count", 0)
            if not slug:
                continue

            # Contar Decisions/Learnings que REFERENCES este pattern
            ref_rows = client.query(
                f"MATCH (d)-[:REFERENCES]->(p:Pattern {{id: '{slug}'}}) "
                f"WHERE d:Decision OR d:Learning "
                f"RETURN count(d) AS ref_count"
            )
            ref_count = ref_rows[0].get("ref_count", 0) if ref_rows else 0

            if ref_count >= 3:
                continue

            # Coletar nomes dos projetos que usam o pattern
            proj_rows = client.query(
                f"MATCH (proj:Project)-[:USES_PATTERN]->(p:Pattern {{id: '{slug}'}}) "
                f"RETURN proj.id AS pid LIMIT 5"
            )
            proj_refs = []
            if proj_rows:
                for pr in proj_rows:
                    pid = pr.get("pid") or pr.get("proj.id", "")
                    if pid:
                        proj_refs.append(f"[[{pid}]]")

            proposals.append({
                "type": "H5",
                "title": f"Pattern amplamente usado sem ADR: `{slug}` ({proj_count} projetos)",
                "body": (
                    f"O pattern `[[{slug}]]` é usado por {proj_count} projetos mas tem apenas "
                    f"{ref_count} referência(s) em Decisions/Learnings.\n\n"
                    f"Projetos que o usam: {', '.join(proj_refs) if proj_refs else '_ver grafo_'}\n\n"
                    f"Sugestão: criar ADR em `_decisions/` documentando a adoção de "
                    f"`_patterns/{slug}.md` e as decisões de design relacionadas."
                ),
                "hash_key": f"H5:{slug}",
            })
    except Exception as e:
        print(f"[curator/H5] Erro ao executar heurística: {e}", file=sys.stderr)

    return proposals


# ---------- H6: decision contradiction via graph ----------

def h6_decision_contradiction() -> list[dict]:
    """
    Pares de ADRs que ambos REFERENCES o mesmo Pattern, com gap de created > 60 dias.
    Sugere possível contradição ou necessidade de revisão.
    Heurística leve — false positives aceitáveis.
    """
    proposals = []
    client = connect_falkor()
    if client is None:
        return proposals

    try:
        rows = client.query(
            "MATCH (d1:Decision)-[:REFERENCES]->(p:Pattern)<-[:REFERENCES]-(d2:Decision) "
            "WHERE d1.id < d2.id "
            "RETURN d1.id AS d1_id, d1.name AS d1_name, d1.created AS d1_created, "
            "       d2.id AS d2_id, d2.name AS d2_name, d2.created AS d2_created, "
            "       p.id AS pattern_slug "
            "LIMIT 30"
        )
        if not rows:
            return proposals

        import datetime as dt

        seen_pairs: set[frozenset] = set()
        for row in rows:
            d1_id = row.get("d1_id") or row.get("d1.id", "")
            d2_id = row.get("d2_id") or row.get("d2.id", "")
            d1_created = row.get("d1_created") or row.get("d1.created", "")
            d2_created = row.get("d2_created") or row.get("d2.created", "")
            pattern_slug = row.get("pattern_slug") or row.get("p.id", "")

            if not d1_id or not d2_id or not pattern_slug:
                continue

            pair_key = frozenset([d1_id, d2_id])
            if pair_key in seen_pairs:
                continue
            seen_pairs.add(pair_key)

            # Calcular gap entre as datas
            d1_int = parse_date(d1_created)
            d2_int = parse_date(d2_created)
            if d1_int is None or d2_int is None:
                continue

            try:
                date1 = dt.date(int(str(d1_int)[:4]), int(str(d1_int)[4:6]), int(str(d1_int)[6:8]))
                date2 = dt.date(int(str(d2_int)[:4]), int(str(d2_int)[4:6]), int(str(d2_int)[6:8]))
                gap_days = abs((date2 - date1).days)
            except ValueError:
                continue

            if gap_days <= 60:
                continue

            d1_name = row.get("d1_name") or row.get("d1.name", d1_id)
            d2_name = row.get("d2_name") or row.get("d2.name", d2_id)

            proposals.append({
                "type": "H6",
                "title": f"Possível contradição entre ADRs via `{pattern_slug}` (gap {gap_days}d)",
                "body": (
                    f"Dois ADRs referenciam o mesmo pattern `[[{pattern_slug}]]` com gap de {gap_days} dias:\n\n"
                    f"- `[[{d1_id}]]` — {d1_name} (criado: {d1_created})\n"
                    f"- `[[{d2_id}]]` — {d2_name} (criado: {d2_created})\n\n"
                    f"Sugestão: verificar se os dois ADRs são compatíveis ou se o mais recente "
                    f"revoga/atualiza o anterior. Se sim, adicionar seção `## Supersede` no ADR mais antigo."
                ),
                "hash_key": f"H6:{d1_id}:{d2_id}",
            })
    except Exception as e:
        print(f"[curator/H6] Erro ao executar heurística: {e}", file=sys.stderr)

    return proposals


# ---------- H7: cross-project pattern adoption gap ----------

def h7_cross_project_adoption_gap() -> list[dict]:
    """
    Para cada Pattern usado por >= 4 projetos de um domínio (fintech, ai-sdlc, etc.),
    identifica projetos do mesmo domínio que NÃO adotaram o pattern.
    Propõe adoção do pattern nesses projetos.
    """
    proposals = []
    client = connect_falkor()
    if client is None:
        return proposals

    # Domínios relevantes para cruzamento
    DOMAIN_GROUPS = [
        "fintech", "trading", "payments", "compliance", "forex", "crypto",
        "ai-sdlc", "ai-agents", "knowledge-mgmt", "automation",
        "backend", "frontend", "platform", "infra-eng",
    ]

    try:
        # Buscar todos os projetos com suas tags de domínio
        proj_rows = client.query(
            "MATCH (proj:Project) RETURN proj.id AS pid, proj.tags AS tags"
        )
        if not proj_rows:
            return proposals

        # Mapear projeto -> set de domínios
        proj_domains: dict[str, set[str]] = {}
        for row in proj_rows:
            pid = row.get("pid") or row.get("proj.id", "")
            tags_raw = row.get("tags") or row.get("proj.tags", "")
            if not pid:
                continue
            # Tags podem vir como string JSON ou string simples
            tags: list[str] = []
            if isinstance(tags_raw, str) and tags_raw:
                import json as _json
                try:
                    parsed = _json.loads(tags_raw)
                    tags = parsed if isinstance(parsed, list) else [tags_raw]
                except (ValueError, TypeError):
                    tags = [t.strip() for t in tags_raw.replace("[", "").replace("]", "").split(",") if t.strip()]
            elif isinstance(tags_raw, list):
                tags = tags_raw
            domains = {t for t in tags if t in DOMAIN_GROUPS}
            if domains:
                proj_domains[pid] = domains

        if not proj_domains:
            return proposals

        # Buscar quais projetos USES_PATTERN para cada pattern
        pattern_rows = client.query(
            "MATCH (proj:Project)-[:USES_PATTERN]->(p:Pattern) "
            "RETURN p.id AS slug, p.name AS pname, collect(proj.id) AS adopters"
        )
        if not pattern_rows:
            return proposals

        seen: set[str] = set()
        for row in pattern_rows:
            slug = row.get("slug") or row.get("p.id", "")
            row.get("pname") or row.get("p.name", slug)
            adopters_raw = row.get("adopters") or row.get("collect(proj.id)", [])

            if isinstance(adopters_raw, list):
                adopters = [a for a in adopters_raw if a]
            else:
                adopters = []

            if not slug or len(adopters) < 4:
                continue

            # Domínios dos projetos adotantes
            adopter_domains: set[str] = set()
            for a in adopters:
                adopter_domains |= proj_domains.get(a, set())

            if not adopter_domains:
                continue

            # Projetos que compartilham domínio mas NÃO adotaram
            non_adopters = []
            for pid, domains in proj_domains.items():
                if pid in adopters:
                    continue
                if domains & adopter_domains:
                    non_adopters.append((pid, domains & adopter_domains))

            if not non_adopters:
                continue

            for pid, shared_domains in non_adopters[:2]:  # max 2 por pattern para não explodir cap
                hash_key = f"H7:{slug}:{pid}"
                if hash_key in seen:
                    continue
                seen.add(hash_key)

                domain_str = ", ".join(sorted(shared_domains))
                adopter_refs = [f"[[{a}]]" for a in adopters[:4]]
                proposals.append({
                    "type": "H7",
                    "title": f"Gap de adoção: `{slug}` ausente em `{pid}` (domínio: {domain_str})",
                    "body": (
                        f"O pattern `[[{slug}]]` é usado por {len(adopters)} projetos do domínio `{domain_str}`, "
                        f"mas `[[{pid}]]` ainda não o adota.\n\n"
                        f"Projetos que já usam: {', '.join(adopter_refs)}\n\n"
                        f"Sugestão: avaliar se `[[{pid}]]` se beneficiaria de adotar "
                        f"`_patterns/{slug}.md`. Se decidir adotar, adicionar edge "
                        f"`USES_PATTERN` no grafo e registrar decisão em `_decisions/`."
                    ),
                    "hash_key": hash_key,
                })

    except Exception as e:
        print(f"[curator/H7] Erro ao executar heurística: {e}", file=sys.stderr)

    return proposals
