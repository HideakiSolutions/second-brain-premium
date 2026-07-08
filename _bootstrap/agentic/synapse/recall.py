"""
recall.py — recall associativo: uma memória puxa a outra.

Pipeline determinístico, sem LLM no hot path:
  1. Sementes: top-K semântico no Qdrant (query) OU uma nota específica (--seed).
  2. Spreading activation 1..N hops sobre as sinapses (peso efetivo, amortecido
     e normalizado por grau — hubs não inundam o resultado).
  3. Score final = alpha·semântico + beta·ativação propagada + gamma·força da
     memória (frequência × recência de ativações, estilo ACT-R, × importância).

Cada resultado carrega a CADEIA que o trouxe (seed → ... → nota): a resposta
explica por que lembrou.
"""
from __future__ import annotations

import hashlib
import heapq
import math
import sys
from datetime import UTC, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import db  # noqa: E402

ALPHA_SEM = 0.55      # similaridade semântica (semente)
BETA_ACT = 0.30       # ativação propagada pelo grafo
GAMMA_STRENGTH = 0.15 # força da memória (uso + importância)
DAMPING = 0.60        # amortecimento por hop
DEFAULT_HOPS = 2
SEED_CHUNKS = 12      # chunks do Qdrant para formar sementes
ACT_DECAY_D = 0.5     # expoente de decaimento ACT-R para força de uso


def _semantic_seeds(query: str, k_chunks: int = SEED_CHUNKS,
                    kind: str | None = None, project: str | None = None) -> dict[str, float]:
    """Consulta o Qdrant e agrega chunk→nota (max score). Lança RuntimeError se offline."""
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "indexer"))
    from store import embed, ollama_ready, qdrant_ready, search  # noqa: PLC0415

    if not (qdrant_ready() and ollama_ready()):
        raise RuntimeError("stack semantica offline (Qdrant/Ollama)")
    qvec = embed(query)
    must: list[dict] = []
    if kind:
        must.append({"key": "kind", "match": {"value": kind}})
    if project:
        must.append({"key": "project", "match": {"value": project}})
    results = search(qvec, k=k_chunks, filter_={"must": must} if must else None)
    seeds: dict[str, float] = {}
    for r in results:
        payload = r.get("payload", {})
        src = payload.get("source_file")
        if not src:
            continue
        seeds[src] = max(seeds.get(src, 0.0), float(r.get("score", 0.0)))
    return seeds


def _strength(conn, node_id: int, now: datetime) -> float:
    """Ativação-base estilo ACT-R: soma de (dias desde cada ativação)^-d, saturada."""
    rows = conn.execute(
        "SELECT ts FROM activations WHERE node = ? ORDER BY ts DESC LIMIT 20",
        (node_id,),
    ).fetchall()
    if not rows:
        return 0.0
    total = 0.0
    for r in rows:
        try:
            ts = datetime.fromisoformat(r["ts"])
        except ValueError:
            continue
        days = max((now - ts).total_seconds() / 86400.0, 0.0)
        total += (days + 0.1) ** (-ACT_DECAY_D)
    b = math.log1p(total)
    return b / (1.0 + b)   # satura em [0, 1)


def spread(adj: dict[int, list[tuple[int, float]]], seeds: dict[int, float],
           hops: int = DEFAULT_HOPS, damping: float = DAMPING
           ) -> tuple[dict[int, float], dict[int, int]]:
    """Propagação de ativação. Retorna (ativação por nó, melhor predecessor)."""
    act: dict[int, float] = dict(seeds)
    pred: dict[int, int] = {}
    best_contrib: dict[int, float] = {}
    frontier = dict(seeds)
    for _hop in range(hops):
        nxt: dict[int, float] = {}
        for n, a in frontier.items():
            neigh = adj.get(n, [])
            if not neigh:
                continue
            norm = sum(w for _, w in neigh)
            if norm <= 0:
                continue
            for m, w in neigh:
                delta = a * damping * (w / norm)
                if delta < 1e-6:
                    continue
                nxt[m] = nxt.get(m, 0.0) + delta
                if m not in seeds and delta > best_contrib.get(m, 0.0):
                    best_contrib[m] = delta
                    pred[m] = n
        for m, a in nxt.items():
            act[m] = act.get(m, 0.0) + a
        frontier = nxt
    return act, pred


def _chain(pred: dict[int, int], node: int, seeds: set[int], titles: dict[int, str],
           max_len: int = 4) -> list[str]:
    chain: list[int] = [node]
    cur = node
    while cur in pred and len(chain) < max_len:
        cur = pred[cur]
        chain.append(cur)
        if cur in seeds:
            break
    return [titles.get(i, str(i)) for i in reversed(chain)]


def recall(query: str | None = None, seed_slug: str | None = None, k: int = 8,
           hops: int = DEFAULT_HOPS, kind: str | None = None, project: str | None = None,
           session: str | None = None, log: bool = True) -> dict:
    """Recall associativo. `query` usa sementes semânticas; `seed_slug` parte de uma nota."""
    conn = db.connect()
    now = datetime.now(UTC)

    node_rows = {int(r["id"]): r for r in conn.execute("SELECT * FROM nodes")}
    by_path = {r["path"]: nid for nid, r in node_rows.items()}
    titles = {nid: (r["title"] or r["slug"]) for nid, r in node_rows.items()}

    seeds: dict[int, float] = {}
    mode = "semantic"
    if seed_slug:
        mode = "associative"
        row = db.node_by_slug(conn, seed_slug) or db.node_by_path(conn, seed_slug)
        if row is None:
            conn.close()
            return {"error": f"nota nao encontrada no grafo sinaptico: {seed_slug}", "results": []}
        seeds[int(row["id"])] = 1.0
    elif query:
        sem = _semantic_seeds(query, kind=kind, project=project)
        for path, score in sem.items():
            nid = by_path.get(path)
            if nid is not None:
                seeds[nid] = score
        if not seeds:
            conn.close()
            return {"query": query, "results": [], "note": "sem sementes semanticas"}
    else:
        conn.close()
        return {"error": "informe query ou seed", "results": []}

    adj = db.load_adjacency(conn)
    act, pred = spread(adj, seeds, hops=hops)

    max_act = max(act.values()) if act else 1.0
    seed_set = set(seeds)

    # pré-ranking barato (semântico + ativação) para limitar as consultas de força
    prelim: list[tuple[float, int]] = []
    for nid, a in act.items():
        row = node_rows.get(nid)
        if row is None:
            continue
        if kind and row["kind"] != kind and nid not in seed_set:
            continue
        if project and row["project"] != project and nid not in seed_set:
            continue
        act_score = a / max_act if max_act > 0 else 0.0
        prelim.append((ALPHA_SEM * seeds.get(nid, 0.0) + BETA_ACT * act_score, nid))
    prelim.sort(key=lambda t: -t[0])
    candidates = [nid for _, nid in prelim[: max(k * 5, 50)]]

    scored: list[tuple[float, int, dict]] = []
    for nid in candidates:
        row = node_rows[nid]
        a = act[nid]
        sem_score = seeds.get(nid, 0.0)
        act_score = a / max_act if max_act > 0 else 0.0
        strength = _strength(conn, nid, now) * (float(row["importance"]) / 1.3)
        if mode == "associative":
            score = 0.60 * act_score + 0.25 * strength + 0.15 * (1.0 if nid in seed_set else 0.0)
        else:
            score = ALPHA_SEM * sem_score + BETA_ACT * act_score + GAMMA_STRENGTH * strength
        scored.append((score, nid, {
            "path": row["path"], "title": titles[nid], "kind": row["kind"],
            "project": row["project"], "score": round(score, 4),
            "semantic": round(sem_score, 4), "activation": round(act_score, 4),
            "strength": round(strength, 4), "seed": nid in seed_set,
            "chain": _chain(pred, nid, seed_set, titles) if nid not in seed_set else [titles[nid]],
        }))

    scored.sort(key=lambda t: (-t[0], t[2]["path"]))
    top = [item for _, _, item in scored[:k]]

    # sugestões de próximo salto: vizinhos fortes do topo, fora do resultado
    shown = {t["path"] for t in top}
    hop_suggestions: list[dict] = []
    for _, nid, item in scored[: min(3, len(scored))]:
        for m, w in sorted(adj.get(nid, []), key=lambda t: -t[1])[:4]:
            r = node_rows.get(m)
            if r is None or r["path"] in shown:
                continue
            hop_suggestions.append({"from": item["title"], "path": r["path"],
                                    "title": titles[m], "weight": round(w, 2)})
            shown.add(r["path"])
            if len(hop_suggestions) >= 5:
                break
        if len(hop_suggestions) >= 5:
            break

    if log and top:
        qh = hashlib.sha256((query or seed_slug or "").encode()).hexdigest()[:12]
        ids = [by_path[t["path"]] for t in top if t["path"] in by_path]
        db.log_activations(conn, ids, "recall", session=session, query_hash=qh)
        conn.commit()

    conn.close()
    return {"query": query, "seed": seed_slug, "mode": mode, "hops": hops,
            "results": top, "next_hops": hop_suggestions}


def explain(slug_a: str, slug_b: str, max_hops: int = 6) -> dict:
    """Caminho sináptico mais forte entre duas memórias (Dijkstra sobre -ln(w))."""
    conn = db.connect()
    ra = db.node_by_slug(conn, slug_a) or db.node_by_path(conn, slug_a)
    rb = db.node_by_slug(conn, slug_b) or db.node_by_path(conn, slug_b)
    if ra is None or rb is None:
        conn.close()
        missing = slug_a if ra is None else slug_b
        return {"error": f"nota nao encontrada no grafo sinaptico: {missing}"}
    a, b = int(ra["id"]), int(rb["id"])
    adj = db.load_adjacency(conn)

    dist: dict[int, float] = {a: 0.0}
    prev: dict[int, int] = {}
    heap: list[tuple[float, int, int]] = [(0.0, 0, a)]
    while heap:
        d, hops, n = heapq.heappop(heap)
        if n == b:
            break
        if d > dist.get(n, math.inf) or hops >= max_hops:
            continue
        for m, w in adj.get(n, []):
            nd = d + (-math.log(max(w, 1e-3)))
            if nd < dist.get(m, math.inf):
                dist[m] = nd
                prev[m] = n
                heapq.heappush(heap, (nd, hops + 1, m))

    if b not in dist:
        conn.close()
        return {"from": slug_a, "to": slug_b, "path": None,
                "note": f"sem caminho em ate {max_hops} hops"}

    path_ids = [b]
    while path_ids[-1] != a:
        path_ids.append(prev[path_ids[-1]])
    path_ids.reverse()

    steps: list[dict] = []
    for i, nid in enumerate(path_ids):
        row = conn.execute("SELECT path, title, kind FROM nodes WHERE id = ?", (nid,)).fetchone()
        step = {"path": row["path"], "title": row["title"], "kind": row["kind"]}
        if i > 0:
            e = conn.execute(
                "SELECT kind, weight_base, boost FROM edges WHERE (src=? AND dst=?) OR (src=? AND dst=?) "
                "ORDER BY weight_base + boost DESC LIMIT 1",
                (path_ids[i - 1], nid, nid, path_ids[i - 1]),
            ).fetchone()
            if e:
                step["via"] = e["kind"]
                step["weight"] = round(min(1.0, e["weight_base"] + e["boost"]), 2)
        steps.append(step)
    conn.close()
    return {"from": slug_a, "to": slug_b, "hops": len(steps) - 1,
            "strength": round(math.exp(-dist[b]), 4), "path": steps}
