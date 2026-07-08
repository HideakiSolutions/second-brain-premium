"""
falkor_sync.py — projeção near-online do grafo sináptico no FalkorDB (graph `synapse`).

Modos:
  incremental (default) — envia só o delta desde `falkor_last_sync` (nós/arestas
      com `updated_at` mais novo) e processa tombstones de deleção. Disparado
      automaticamente após build/reinforce/decay (desative com SB_SYNAPSE_AUTOSYNC=0).
  full — reconciliação: apaga o graph e reprojeta tudo (roda no consolidate semanal).

Fail-soft: FalkorDB offline → skip sem tocar em `falkor_last_sync` nem nos
tombstones; o próximo sync (ou o full semanal) recupera o atraso. O SQLite
continua canônico; a projeção existe para consultas Cypher/MCP.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import db  # noqa: E402

GRAPH_NAME = "synapse"
META_KEY = "falkor_last_sync"


def _esc(v: str | None) -> str:
    return (v or "").replace("\\", "/").replace("'", "\\'")[:300]


def _client():
    try:
        from graph.falkor_client import FalkorClient  # noqa: PLC0415
    except ImportError:
        return None
    client = FalkorClient(graph=GRAPH_NAME)
    if not client.connect():
        return None
    return client


def _push_node(client, r) -> bool:
    ok = client.query(
        f"MERGE (n:Note {{id: '{_esc(r['path'])}'}}) "
        f"SET n.slug = '{_esc(r['slug'])}', n.kind = '{_esc(r['kind'])}', "
        f"n.project = '{_esc(r['project'] or '')}', n.title = '{_esc(r['title'] or '')}', "
        f"n.importance = {float(r['importance'])} RETURN n.id"
    )
    return ok is not None


def _push_edge(client, src_path: str, dst_path: str, e) -> bool:
    w = min(1.0, float(e["weight_base"]) + float(e["boost"]))
    ok = client.query(
        f"MATCH (a:Note {{id: '{_esc(src_path)}'}}), (b:Note {{id: '{_esc(dst_path)}'}}) "
        f"MERGE (a)-[r:{e['kind']}]->(b) "
        f"SET r.weight = {round(w, 4)}, r.source = '{e['source']}' RETURN type(r)"
    )
    return ok is not None


def _process_tombstones(client, conn) -> int:
    rows = conn.execute("SELECT rowid, kind, a_path, b_path, e_kind FROM falkor_tombstones").fetchall()
    done = 0
    for t in rows:
        if t["kind"] == "edge":
            ok = client.query(
                f"MATCH (a:Note {{id: '{_esc(t['a_path'])}'}})-[r:{t['e_kind']}]->"
                f"(b:Note {{id: '{_esc(t['b_path'])}'}}) DELETE r RETURN 1"
            )
        else:
            ok = client.query(
                f"MATCH (n:Note {{id: '{_esc(t['a_path'])}'}}) DETACH DELETE n RETURN 1"
            )
        if ok is not None:
            conn.execute("DELETE FROM falkor_tombstones WHERE rowid = ?", (t["rowid"],))
            done += 1
    return done


def sync(full: bool = False) -> dict:
    client = _client()
    if client is None:
        return {"skipped": "FalkorDB offline", "mode": "full" if full else "incremental"}

    conn = db.connect()
    cutoff = db.get_meta(conn, META_KEY)
    started = db.now_iso()

    if full:
        # reconciliação: reprojeta do zero (remove qualquer resíduo divergente)
        client.delete_graph()
        conn.execute("DELETE FROM falkor_tombstones")
        nodes = conn.execute(
            "SELECT id, path, slug, kind, project, title, importance FROM nodes"
        ).fetchall()
        edges = conn.execute(
            "SELECT src, dst, kind, weight_base, boost, source FROM edges WHERE weight_base + boost > 0"
        ).fetchall()
        tombstoned = 0
    else:
        tombstoned = _process_tombstones(client, conn)
        if cutoff:
            nodes = conn.execute(
                "SELECT id, path, slug, kind, project, title, importance FROM nodes "
                "WHERE updated_at IS NULL OR updated_at > ?", (cutoff,),
            ).fetchall()
            edges = conn.execute(
                "SELECT src, dst, kind, weight_base, boost, source FROM edges "
                "WHERE (updated_at IS NULL OR updated_at > ?) AND weight_base + boost > 0",
                (cutoff,),
            ).fetchall()
        else:
            nodes = conn.execute(
                "SELECT id, path, slug, kind, project, title, importance FROM nodes"
            ).fetchall()
            edges = conn.execute(
                "SELECT src, dst, kind, weight_base, boost, source FROM edges "
                "WHERE weight_base + boost > 0"
            ).fetchall()

    path_of = {int(r["id"]): r["path"] for r in conn.execute("SELECT id, path FROM nodes")}

    n_nodes = sum(1 for r in nodes if _push_node(client, r))

    # arestas dependem de ambos os nós existirem na projeção; num delta, o outro
    # endpoint pode não ter mudado — garante os endpoints antes
    endpoint_ids = {int(e["src"]) for e in edges} | {int(e["dst"]) for e in edges}
    pushed_ids = {int(r["id"]) for r in nodes}
    missing = endpoint_ids - pushed_ids
    if missing and not full:
        qmarks = ",".join("?" for _ in missing)
        for r in conn.execute(
            f"SELECT id, path, slug, kind, project, title, importance FROM nodes WHERE id IN ({qmarks})",
            tuple(missing),
        ):
            _push_node(client, r)

    n_edges = 0
    for e in edges:
        src, dst = path_of.get(int(e["src"])), path_of.get(int(e["dst"]))
        if src and dst and _push_edge(client, src, dst, e):
            n_edges += 1

    db.set_meta(conn, META_KEY, started)
    conn.commit()
    conn.close()
    return {"mode": "full" if full else "incremental", "graph": GRAPH_NAME,
            "nodes": n_nodes, "edges": n_edges, "tombstones": tombstoned}


def autosync() -> dict | None:
    """Sync incremental automático pós-operação. Desativável via SB_SYNAPSE_AUTOSYNC=0."""
    if os.environ.get("SB_SYNAPSE_AUTOSYNC", "1") == "0":
        return None
    try:
        return sync(full=False)
    except Exception as exc:  # nunca quebrar a operação principal por causa da projeção
        return {"skipped": f"erro no sync: {exc}"}
