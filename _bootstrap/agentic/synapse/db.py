"""
db.py — estado sináptico canônico em SQLite.

O markdown continua sendo a fonte da verdade das memórias; este banco guarda o
estado DERIVADO das sinapses (nós, arestas com peso, ativações, co-ativações).
Reconstruível: `synapse build` refaz nodes/edges a partir dos arquivos; o log
de ativações é o único dado primário novo (event log append-only, da máquina).

Stdlib-only. Fail-soft: quem importa este módulo deve tolerar OperationalError.
"""
from __future__ import annotations

import os
import sqlite3
from datetime import UTC, datetime
from pathlib import Path

VAULT = Path(os.environ.get("VAULT_ROOT") or os.environ.get("VAULT") or Path(__file__).resolve().parents[3])
DB_DIR = VAULT / "_memory" / ".synapse"
DB_PATH = DB_DIR / "synapse.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS meta (
    key   TEXT PRIMARY KEY,
    value TEXT
);
CREATE TABLE IF NOT EXISTS nodes (
    id         INTEGER PRIMARY KEY,
    path       TEXT UNIQUE NOT NULL,   -- relativo ao vault, posix
    slug       TEXT NOT NULL,
    kind       TEXT NOT NULL,          -- mesmo vocabulário do chunker/Qdrant
    project    TEXT,
    title      TEXT,
    status     TEXT,
    created    TEXT,
    updated    TEXT,
    importance REAL NOT NULL DEFAULT 1.0,
    updated_at TEXT                    -- para sync incremental da projeção FalkorDB
);
CREATE INDEX IF NOT EXISTS idx_nodes_slug ON nodes(slug);
CREATE INDEX IF NOT EXISTS idx_nodes_kind ON nodes(kind);

CREATE TABLE IF NOT EXISTS edges (
    src            INTEGER NOT NULL,
    dst            INTEGER NOT NULL,
    kind           TEXT    NOT NULL,   -- WIKILINK|RELATED|REFERENCES|SUPERSEDES|TAG_SIBLING|STRUCTURAL|LEARNED
    weight_base    REAL    NOT NULL DEFAULT 0.0,  -- derivado dos arquivos (rebuild sobrescreve)
    boost          REAL    NOT NULL DEFAULT 0.0,  -- aprendido por uso (hebbiano; decai)
    source         TEXT    NOT NULL DEFAULT 'file',  -- file|learned
    mentions       INTEGER NOT NULL DEFAULT 1,
    last_activated TEXT,
    created        TEXT,
    updated_at     TEXT,               -- para sync incremental da projeção FalkorDB
    PRIMARY KEY (src, dst, kind)
);
CREATE INDEX IF NOT EXISTS idx_edges_src ON edges(src);
CREATE INDEX IF NOT EXISTS idx_edges_dst ON edges(dst);

-- deleções pendentes de propagação para a projeção FalkorDB
CREATE TABLE IF NOT EXISTS falkor_tombstones (
    kind   TEXT NOT NULL,              -- 'edge' | 'node'
    a_path TEXT NOT NULL,              -- edge: path do src · node: path do nó
    b_path TEXT,                       -- edge: path do dst
    e_kind TEXT,                       -- edge: tipo da aresta
    ts     TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS activations (
    ts         TEXT    NOT NULL,
    node       INTEGER NOT NULL,
    source     TEXT    NOT NULL,       -- recall|search|read|write|session|manual
    session    TEXT,
    query_hash TEXT
);
CREATE INDEX IF NOT EXISTS idx_act_node ON activations(node);
CREATE INDEX IF NOT EXISTS idx_act_ts   ON activations(ts);

CREATE TABLE IF NOT EXISTS coactivations (
    a       INTEGER NOT NULL,
    b       INTEGER NOT NULL,
    count   INTEGER NOT NULL DEFAULT 0,
    last_ts TEXT,
    PRIMARY KEY (a, b)
);
"""


def now_iso() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


def connect(readonly: bool = False) -> sqlite3.Connection:
    DB_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH), timeout=5.0)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=3000")
    conn.execute("PRAGMA synchronous=NORMAL")
    conn.row_factory = sqlite3.Row
    if not readonly:
        conn.executescript(SCHEMA)
        _migrate(conn)
    return conn


def _migrate(conn: sqlite3.Connection) -> None:
    """Migrações aditivas para bancos criados por versões anteriores."""
    for table in ("nodes", "edges"):
        cols = {r["name"] for r in conn.execute(f"PRAGMA table_info({table})")}
        if "updated_at" not in cols:
            conn.execute(f"ALTER TABLE {table} ADD COLUMN updated_at TEXT")


def add_edge_tombstone(conn: sqlite3.Connection, a_path: str, b_path: str, e_kind: str) -> None:
    conn.execute(
        "INSERT INTO falkor_tombstones(kind, a_path, b_path, e_kind, ts) VALUES('edge', ?, ?, ?, ?)",
        (a_path, b_path, e_kind, now_iso()),
    )


def add_node_tombstone(conn: sqlite3.Connection, path: str) -> None:
    conn.execute(
        "INSERT INTO falkor_tombstones(kind, a_path, ts) VALUES('node', ?, ?)",
        (path, now_iso()),
    )


def get_meta(conn: sqlite3.Connection, key: str) -> str | None:
    row = conn.execute("SELECT value FROM meta WHERE key = ?", (key,)).fetchone()
    return row["value"] if row else None


def set_meta(conn: sqlite3.Connection, key: str, value: str) -> None:
    conn.execute(
        "INSERT INTO meta(key, value) VALUES(?, ?) "
        "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
        (key, value),
    )


def upsert_node(conn: sqlite3.Connection, *, path: str, slug: str, kind: str,
                project: str | None, title: str, status: str | None,
                created: str | None, updated: str | None, importance: float) -> int:
    conn.execute(
        """
        INSERT INTO nodes(path, slug, kind, project, title, status, created, updated, importance, updated_at)
        VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(path) DO UPDATE SET
            slug = excluded.slug, kind = excluded.kind, project = excluded.project,
            title = excluded.title, status = excluded.status, created = excluded.created,
            updated = excluded.updated, importance = excluded.importance,
            updated_at = CASE WHEN nodes.slug IS NOT excluded.slug
                               OR nodes.kind IS NOT excluded.kind
                               OR nodes.project IS NOT excluded.project
                               OR nodes.title IS NOT excluded.title
                               OR nodes.status IS NOT excluded.status
                               OR nodes.updated IS NOT excluded.updated
                               OR nodes.importance IS NOT excluded.importance
                          THEN excluded.updated_at ELSE nodes.updated_at END
        """,
        (path, slug, kind, project, title, status, created, updated, importance, now_iso()),
    )
    row = conn.execute("SELECT id FROM nodes WHERE path = ?", (path,)).fetchone()
    return int(row["id"])


def node_by_path(conn: sqlite3.Connection, path: str) -> sqlite3.Row | None:
    return conn.execute("SELECT * FROM nodes WHERE path = ?", (path,)).fetchone()


def node_by_slug(conn: sqlite3.Connection, slug: str) -> sqlite3.Row | None:
    rows = conn.execute("SELECT * FROM nodes WHERE slug = ? ORDER BY path", (slug,)).fetchall()
    return rows[0] if rows else None


def upsert_file_edge(conn: sqlite3.Connection, src: int, dst: int, kind: str,
                     weight_base: float, mentions: int) -> None:
    ts = now_iso()
    conn.execute(
        """
        INSERT INTO edges(src, dst, kind, weight_base, source, mentions, created, updated_at)
        VALUES(?, ?, ?, ?, 'file', ?, ?, ?)
        ON CONFLICT(src, dst, kind) DO UPDATE SET
            weight_base = excluded.weight_base,
            mentions = excluded.mentions,
            source = 'file',
            updated_at = CASE WHEN edges.weight_base IS NOT excluded.weight_base
                               OR edges.mentions IS NOT excluded.mentions
                               OR edges.source IS NOT 'file'
                          THEN excluded.updated_at ELSE edges.updated_at END
        """,
        (src, dst, kind, weight_base, mentions, ts, ts),
    )


def effective_weight(row: sqlite3.Row) -> float:
    return min(1.0, float(row["weight_base"]) + float(row["boost"]))


def load_adjacency(conn: sqlite3.Connection) -> dict[int, list[tuple[int, float]]]:
    """Adjacência não-direcionada: propagação de ativação trata sinapses como
    bidirecionais (o link A→B também torna A alcançável a partir de B)."""
    adj: dict[int, list[tuple[int, float]]] = {}
    for row in conn.execute("SELECT src, dst, weight_base, boost FROM edges"):
        w = min(1.0, float(row["weight_base"]) + float(row["boost"]))
        if w <= 0.0:
            continue
        adj.setdefault(int(row["src"]), []).append((int(row["dst"]), w))
        adj.setdefault(int(row["dst"]), []).append((int(row["src"]), w))
    return adj


def log_activations(conn: sqlite3.Connection, node_ids: list[int], source: str,
                    session: str | None = None, query_hash: str | None = None) -> int:
    ts = now_iso()
    conn.executemany(
        "INSERT INTO activations(ts, node, source, session, query_hash) VALUES(?, ?, ?, ?, ?)",
        [(ts, nid, source, session, query_hash) for nid in node_ids],
    )
    return len(node_ids)


def stats(conn: sqlite3.Connection) -> dict:
    out: dict = {}
    out["nodes"] = conn.execute("SELECT COUNT(*) AS c FROM nodes").fetchone()["c"]
    out["edges"] = conn.execute("SELECT COUNT(*) AS c FROM edges").fetchone()["c"]
    out["activations"] = conn.execute("SELECT COUNT(*) AS c FROM activations").fetchone()["c"]
    out["coactivations_pending"] = conn.execute("SELECT COUNT(*) AS c FROM coactivations").fetchone()["c"]
    out["edges_by_kind"] = {
        r["kind"]: r["c"]
        for r in conn.execute("SELECT kind, COUNT(*) AS c FROM edges GROUP BY kind ORDER BY c DESC")
    }
    out["learned_edges"] = conn.execute(
        "SELECT COUNT(*) AS c FROM edges WHERE source = 'learned'"
    ).fetchone()["c"]
    out["last_build"] = get_meta(conn, "last_build")
    out["last_decay"] = get_meta(conn, "last_decay")
    out["last_consolidate"] = get_meta(conn, "last_consolidate")
    return out
