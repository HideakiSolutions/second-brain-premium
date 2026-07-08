"""
falkor_client.py — FalkorDB client via Redis protocol.

Tries to use the `redis` Python library first; falls back to raw socket RESP if unavailable.
FalkorDB exposes GRAPH.QUERY and GRAPH.RO_QUERY commands over the Redis protocol.
"""
from __future__ import annotations

import json
import socket
import sys
from typing import Any

FALKOR_HOST = "127.0.0.1"
FALKOR_PORT = 6379
GRAPH_NAME = "secondbrain"

# ---------------------------------------------------------------------------
# RESP2 raw socket fallback
# ---------------------------------------------------------------------------

def _encode_resp(*args) -> bytes:
    """Encode command args as RESP2 array."""
    parts = [f"*{len(args)}\r\n".encode()]
    for arg in args:
        s = str(arg).encode("utf-8")
        parts.append(f"${len(s)}\r\n".encode())
        parts.append(s)
        parts.append(b"\r\n")
    return b"".join(parts)


def _read_resp(sock) -> Any:
    """Read one RESP value from socket (simplified, no pipelining)."""
    line = b""
    while not line.endswith(b"\r\n"):
        ch = sock.recv(1)
        if not ch:
            raise ConnectionError("Socket closed unexpectedly")
        line += ch
    line = line.rstrip(b"\r\n")
    if not line:
        return None
    prefix = chr(line[0])

    if prefix == "+":
        return line[1:].decode()
    elif prefix == "-":
        raise RuntimeError(f"Redis error: {line[1:].decode()}")
    elif prefix == ":":
        return int(line[1:])
    elif prefix == "$":
        n = int(line[1:])
        if n == -1:
            return None
        data = b""
        while len(data) < n + 2:
            chunk = sock.recv(n + 2 - len(data))
            if not chunk:
                raise ConnectionError("Socket closed while reading bulk string")
            data += chunk
        return data[:-2].decode("utf-8", errors="replace")
    elif prefix == "*":
        count = int(line[1:])
        if count == -1:
            return None
        return [_read_resp(sock) for _ in range(count)]
    else:
        return line.decode()


class _RawSocketRedis:
    """Minimal Redis client using raw sockets (stdlib only)."""

    def __init__(self, host: str, port: int, timeout: float = 10.0):
        self.host = host
        self.port = port
        self.timeout = timeout
        self._sock: socket.socket | None = None

    def connect(self):
        self._sock = socket.create_connection((self.host, self.port), timeout=self.timeout)

    def close(self):
        if self._sock:
            self._sock.close()
            self._sock = None

    def execute_command(self, *args) -> Any:
        if not self._sock:
            self.connect()
        self._sock.sendall(_encode_resp(*args))
        return _read_resp(self._sock)

    def ping(self) -> bool:
        try:
            result = self.execute_command("PING")
            return result == "PONG"
        except Exception:
            return False


# ---------------------------------------------------------------------------
# Try redis-py; fallback to raw socket
# ---------------------------------------------------------------------------

_USE_REDIS_PY = False
try:
    import redis as _redis_py  # type: ignore
    _USE_REDIS_PY = True
except ImportError:
    pass


class FalkorClient:
    """
    FalkorDB client. Wraps either redis-py or raw socket backend.
    All graph operations target the GRAPH_NAME graph.
    Fail-soft: methods return None/empty list if FalkorDB is not running.
    """

    def __init__(self, host: str = FALKOR_HOST, port: int = FALKOR_PORT,
                 graph: str = GRAPH_NAME):
        self.host = host
        self.port = port
        self.graph = graph
        self._client = None

    def connect(self) -> bool:
        """Connect and return True if successful."""
        try:
            if _USE_REDIS_PY:
                self._client = _redis_py.Redis(
                    host=self.host, port=self.port,
                    socket_timeout=10, socket_connect_timeout=5,
                    decode_responses=True
                )
                self._client.ping()
            else:
                raw = _RawSocketRedis(self.host, self.port)
                raw.connect()
                self._client = raw
            return True
        except Exception as e:
            print(f"[falkor_client] FalkorDB not reachable at {self.host}:{self.port}: {e}",
                  file=sys.stderr)
            self._client = None
            return False

    def ping(self) -> bool:
        if self._client is None:
            return self.connect()
        try:
            if _USE_REDIS_PY:
                return self._client.ping()
            else:
                return self._client.ping()
        except Exception:
            return False

    def query(self, cypher: str, params: dict | None = None) -> list | None:
        """Execute a Cypher query and return parsed rows."""
        if self._client is None:
            if not self.connect():
                return None
        try:
            if _USE_REDIS_PY:
                result = self._client.execute_command(
                    "GRAPH.QUERY", self.graph, cypher, "--compact"
                )
            else:
                result = self._client.execute_command(
                    "GRAPH.QUERY", self.graph, cypher, "--compact"
                )
            return self._parse_result(result)
        except Exception as e:
            print(f"[falkor_client] Query error: {e}\nCypher: {cypher}", file=sys.stderr)
            return None

    def _parse_result(self, raw) -> list:
        """Parse FalkorDB GRAPH.QUERY result into list of row dicts."""
        if raw is None:
            return []
        # FalkorDB compact result: [header, rows, stats]
        # header = list of column names
        # rows = list of row (each row = list of typed cells)
        if not isinstance(raw, list) or len(raw) < 2:
            return []
        header_section = raw[0]
        data_section = raw[1]
        if not isinstance(header_section, list):
            return []

        # Extract column names from header (compact: [[id, alias], ...])
        col_names = []
        for col in header_section:
            if isinstance(col, list) and len(col) >= 2:
                col_names.append(col[1])
            elif isinstance(col, str):
                col_names.append(col)
            else:
                col_names.append(str(col))

        rows = []
        if isinstance(data_section, list):
            for row in data_section:
                if not isinstance(row, list):
                    rows.append(row)
                    continue
                row_dict = {}
                for i, cell in enumerate(row):
                    key = col_names[i] if i < len(col_names) else f"col{i}"
                    row_dict[key] = self._unwrap_cell(cell)
                rows.append(row_dict)
        return rows

    def _unwrap_cell(self, cell) -> Any:
        """Unwrap compact cell value: [type_id, value]."""
        if not isinstance(cell, list) or len(cell) < 2:
            return cell
        type_id = cell[0]
        val = cell[1]
        # FalkorDB types: 1=null, 2=string, 3=int, 4=double, 5=bool,
        #                 6=array, 7=edge, 8=node, 9=path, 10=map, 11=point
        if type_id == 1:
            return None
        elif type_id in (2,):
            return val
        elif type_id == 3:
            return int(val) if val is not None else 0
        elif type_id == 4:
            return float(val) if val is not None else 0.0
        elif type_id == 5:
            return bool(val)
        elif type_id == 6:
            return [self._unwrap_cell(v) for v in val] if isinstance(val, list) else val
        else:
            return val

    def upsert_entity(self, entity) -> bool:
        """Upsert a single entity node using MERGE."""
        etype = entity.type
        eid = entity.id.replace("'", "\\'")
        name = entity.name.replace("'", "\\'")
        props = entity.properties or {}

        # Build property string for MERGE key + SET for extra props
        cypher = (
            f"MERGE (n:{etype} {{id: '{eid}'}}) "
            f"SET n.name = '{name}'"
        )
        for k, v in props.items():
            if k == "tags" and isinstance(v, list):
                v_str = json.dumps(v).replace("'", "\\'")
                cypher += f", n.{k} = '{v_str}'"
            elif isinstance(v, str):
                v_safe = v.replace("'", "\\'").replace("\n", " ")[:500]
                cypher += f", n.{k} = '{v_safe}'"
            elif isinstance(v, (int, float)):
                cypher += f", n.{k} = {v}"
        cypher += " RETURN n.id"

        result = self.query(cypher)
        return result is not None

    def upsert_relation(self, rel) -> bool:
        """Upsert a relation edge using MERGE."""
        src = rel.source_id.replace("'", "\\'")
        tgt = rel.target_id.replace("'", "\\'")
        kind = rel.kind.value
        t_created = (rel.t_created or "").replace("'", "\\'")
        t_valid = (rel.t_valid_from or "").replace("'", "\\'")

        cypher = (
            f"MATCH (a {{id: '{src}'}}), (b {{id: '{tgt}'}}) "
            f"MERGE (a)-[r:{kind}]->(b) "
            f"SET r.t_created = '{t_created}', r.t_valid_from = '{t_valid}' "
            f"RETURN type(r)"
        )
        result = self.query(cypher)
        return result is not None

    def delete_graph(self) -> bool:
        """Apaga o graph inteiro (GRAPH.DELETE). Fail-soft: False se indisponível."""
        if self._client is None:
            if not self.connect():
                return False
        try:
            self._client.execute_command("GRAPH.DELETE", self.graph)
            return True
        except Exception as e:
            # graph inexistente também retorna erro — tratar como sucesso idempotente
            if "unknown graph" in str(e).lower() or "empty key" in str(e).lower():
                return True
            print(f"[falkor_client] delete_graph error: {e}", file=sys.stderr)
            return False

    def count_nodes(self) -> int:
        result = self.query("MATCH (n) RETURN count(n) AS cnt")
        if result:
            return result[0].get("cnt", 0)
        return 0

    def count_edges(self) -> int:
        result = self.query("MATCH ()-[r]->() RETURN count(r) AS cnt")
        if result:
            return result[0].get("cnt", 0)
        return 0

    def get_entity(self, entity_id: str) -> dict | None:
        safe_id = entity_id.replace("'", "\\'")
        result = self.query(
            f"MATCH (n {{id: '{safe_id}'}}) RETURN n.id, n.name, n.type, labels(n)"
        )
        return result[0] if result else None

    def get_neighbors(self, entity_id: str, depth: int = 1) -> list:
        safe_id = entity_id.replace("'", "\\'")
        result = self.query(
            f"MATCH (n {{id: '{safe_id}'}})-[r*1..{depth}]-(m) "
            f"RETURN m.id, m.name, labels(m), type(r) LIMIT 50"
        )
        return result or []

    def get_decisions_for_pattern(self, pattern_id: str) -> list:
        safe_id = pattern_id.replace("'", "\\'")
        result = self.query(
            f"MATCH (d:Decision)-[r:REFERENCES]->(p:Pattern {{id: '{safe_id}'}}) "
            f"RETURN d.id, d.name, d.date"
        )
        return result or []

    def find_similar_decisions(self, text: str) -> list:
        """
        Stub — keyword search in decision IDs/names via Cypher pattern matching.
        Full semantic search via Qdrant integration is a TODO for Onda 4-extension.
        """
        words = [w.lower() for w in text.split()[:5] if len(w) > 3]
        if not words:
            return self.query("MATCH (d:Decision) RETURN d.id, d.name LIMIT 10") or []

        conditions = " OR ".join(
            f"toLower(d.id) CONTAINS '{w}' OR toLower(d.name) CONTAINS '{w}'"
            for w in words
        )
        result = self.query(
            f"MATCH (d:Decision) WHERE {conditions} RETURN d.id, d.name LIMIT 10"
        )
        return result or []

    def get_stats(self) -> dict:
        stats = {}
        for etype in ["Project", "Pattern", "Feature", "Decision", "Learning", "Technology"]:
            result = self.query(f"MATCH (n:{etype}) RETURN count(n) AS cnt")
            stats[etype] = result[0].get("cnt", 0) if result else 0

        for kind in ["USES_PATTERN", "USES_FEATURE", "REFERENCES", "HAS_DECISION", "REFINES"]:
            result = self.query(f"MATCH ()-[r:{kind}]->() RETURN count(r) AS cnt")
            stats[kind] = result[0].get("cnt", 0) if result else 0

        return stats
