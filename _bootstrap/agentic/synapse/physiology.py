"""
physiology.py — fisiologia das sinapses: ativação, reforço hebbiano, decay e poda.

  activate   — registra que memórias foram tocadas (read/write/search/recall/session)
  reinforce  — "quem dispara junto, conecta": co-ativação fortalece arestas (boost);
               co-ativação repetida entre nós não-ligados cria aresta LEARNED
               (sinaptogênese), que a curadoria pode promover a WikiLink real
  decay      — o componente aprendido (boost) decai exponencialmente; arestas
               LEARNED abaixo do piso são podadas. Arestas derivadas de arquivo
               NUNCA são removidas pelo decay (o arquivo é a verdade).

Determinístico e barato: seguro para rodar de hooks.
"""
from __future__ import annotations

import math
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import db  # noqa: E402

ETA = 0.10                 # taxa de aprendizado hebbiano
LEARNED_INITIAL = 0.40     # boost inicial de uma aresta LEARNED recém-criada
LEARNED_THRESHOLD = 3      # co-ativações necessárias para sinaptogênese
PRUNE_FLOOR = 0.15         # LEARNED abaixo disso é podada
HALF_LIFE_DAYS = 90.0      # meia-vida do boost
MAX_SESSION_NODES = 40     # teto de nós por rodada de reforço (evita O(n²) explosivo)


def activate(paths: list[str], source: str, session: str | None = None) -> int:
    """Registra ativações para caminhos do vault (ignora o que não é nó conhecido)."""
    conn = db.connect()
    ids: list[int] = []
    for p in paths:
        rel = p
        try:
            rel = Path(p).resolve().relative_to(db.VAULT).as_posix()
        except (ValueError, OSError):
            rel = p.replace("\\", "/").lstrip("./")
        row = db.node_by_path(conn, rel)
        if row is None:
            row = db.node_by_slug(conn, Path(rel).stem)
        if row is not None:
            ids.append(int(row["id"]))
    n = 0
    if ids:
        n = db.log_activations(conn, sorted(set(ids)), source, session=session)
        conn.commit()
    conn.close()
    return n


def reinforce(session: str | None = None, window_minutes: int = 240) -> dict:
    """Reforço hebbiano sobre o conjunto co-ativado (sessão ou janela recente)."""
    conn = db.connect()
    now = datetime.now(UTC)
    if session:
        rows = conn.execute(
            "SELECT node, COUNT(*) AS c FROM activations WHERE session = ? "
            "GROUP BY node ORDER BY c DESC LIMIT ?",
            (session, MAX_SESSION_NODES),
        ).fetchall()
    else:
        since = (now - timedelta(minutes=window_minutes)).isoformat(timespec="seconds")
        rows = conn.execute(
            "SELECT node, COUNT(*) AS c FROM activations WHERE ts >= ? "
            "GROUP BY node ORDER BY c DESC LIMIT ?",
            (since, MAX_SESSION_NODES),
        ).fetchall()
    nodes = sorted(int(r["node"]) for r in rows)
    if len(nodes) < 2:
        conn.close()
        return {"nodes": len(nodes), "strengthened": 0, "learned_created": 0}

    ts = db.now_iso()
    strengthened = 0
    learned = 0
    for i, a in enumerate(nodes):
        for b in nodes[i + 1:]:
            edge = conn.execute(
                "SELECT src, dst, kind, weight_base, boost FROM edges "
                "WHERE (src = ? AND dst = ?) OR (src = ? AND dst = ?) "
                "ORDER BY weight_base + boost DESC LIMIT 1",
                (a, b, b, a),
            ).fetchone()
            if edge is not None:
                w = min(1.0, float(edge["weight_base"]) + float(edge["boost"]))
                new_boost = float(edge["boost"]) + ETA * (1.0 - w)
                conn.execute(
                    "UPDATE edges SET boost = ?, last_activated = ?, updated_at = ? "
                    "WHERE src = ? AND dst = ? AND kind = ?",
                    (round(new_boost, 5), ts, ts, edge["src"], edge["dst"], edge["kind"]),
                )
                strengthened += 1
            else:
                row = conn.execute(
                    "SELECT count FROM coactivations WHERE a = ? AND b = ?", (a, b)
                ).fetchone()
                count = (int(row["count"]) if row else 0) + 1
                if count >= LEARNED_THRESHOLD:
                    conn.execute(
                        "INSERT INTO edges(src, dst, kind, weight_base, boost, source, mentions, "
                        "last_activated, created, updated_at) VALUES(?, ?, 'LEARNED', 0.0, ?, 'learned', ?, ?, ?, ?) "
                        "ON CONFLICT(src, dst, kind) DO UPDATE SET boost = excluded.boost, "
                        "updated_at = excluded.updated_at",
                        (a, b, LEARNED_INITIAL, count, ts, ts, ts),
                    )
                    conn.execute("DELETE FROM coactivations WHERE a = ? AND b = ?", (a, b))
                    learned += 1
                else:
                    conn.execute(
                        "INSERT INTO coactivations(a, b, count, last_ts) VALUES(?, ?, ?, ?) "
                        "ON CONFLICT(a, b) DO UPDATE SET count = ?, last_ts = ?",
                        (a, b, count, ts, count, ts),
                    )
    conn.commit()
    conn.close()
    return {"nodes": len(nodes), "strengthened": strengthened, "learned_created": learned}


def decay(half_life_days: float = HALF_LIFE_DAYS) -> dict:
    """Decaimento exponencial do boost desde o último decay; poda LEARNED fracas."""
    conn = db.connect()
    now = datetime.now(UTC)
    last = db.get_meta(conn, "last_decay")
    if last:
        try:
            days = max((now - datetime.fromisoformat(last)).total_seconds() / 86400.0, 0.0)
        except ValueError:
            days = 1.0
    else:
        days = 1.0
    factor = math.exp(-math.log(2) / half_life_days * days)

    ts = db.now_iso()
    conn.execute(
        "UPDATE edges SET boost = ROUND(boost * ?, 5), updated_at = ? WHERE boost > 0",
        (factor, ts),
    )
    conn.execute("UPDATE edges SET boost = 0 WHERE boost < 0.005")
    pruned = conn.execute(
        "DELETE FROM edges WHERE source = 'learned' AND weight_base + boost < ? "
        "RETURNING src, dst, kind",
        (PRUNE_FLOOR,),
    ).fetchall()
    if pruned:
        path_of = {int(r["id"]): r["path"] for r in conn.execute("SELECT id, path FROM nodes")}
        for e in pruned:
            db.add_edge_tombstone(conn, path_of.get(int(e["src"]), "?"),
                                  path_of.get(int(e["dst"]), "?"), e["kind"])
    # co-ativações antigas (>60 dias) também esvaem
    cutoff = (now - timedelta(days=60)).isoformat(timespec="seconds")
    stale = conn.execute(
        "DELETE FROM coactivations WHERE last_ts < ? RETURNING a", (cutoff,)
    ).fetchall()

    db.set_meta(conn, "last_decay", db.now_iso())
    conn.commit()
    conn.close()
    return {"elapsed_days": round(days, 2), "factor": round(factor, 4),
            "pruned_learned": len(pruned), "stale_coactivations": len(stale)}
