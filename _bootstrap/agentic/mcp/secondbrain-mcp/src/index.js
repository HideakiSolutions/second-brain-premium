/**
 * secondbrain-mcp — Second Brain Knowledge Graph MCP Server
 *
 * Exposes FalkorDB (graph over vault) as MCP tools for Claude Code.
 * Transport: stdio (standard MCP stdio server).
 *
 * Tools:
 *   query_graph          — raw Cypher query
 *   multi_hop            — graph traversal from entity_id
 *   entity_neighbors     — alias for multi_hop depth=1
 *   why_decision         — REFERENCES + affected projects for an ADR
 *   find_similar_decisions — keyword search in Decision nodes
 *   get_project_state    — graph info + reads state.md file
 *   graph_stats          — entity/relation counts
 */

import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import { createClient } from "redis";
import { execFile } from "child_process";
import { readFileSync, existsSync } from "fs";
import { join, resolve, dirname } from "path";
import { fileURLToPath } from "url";
import { z } from "zod";

// Raiz do vault: env SECONDBRAIN_VAULT ou derivada da posicao deste script
// (_bootstrap/agentic/mcp/secondbrain-mcp/src -> 5 niveis acima).
const __dirname_ = dirname(fileURLToPath(import.meta.url));
const VAULT = process.env.SECONDBRAIN_VAULT || resolve(__dirname_, "..", "..", "..", "..", "..");
const FALKOR_HOST = "127.0.0.1";
const FALKOR_PORT = 6379;
const GRAPH = "secondbrain";
const SYNAPSE_CLI = join(VAULT, "_bootstrap", "agentic", "synapse", "main.py");

/**
 * Run the synapse CLI and return parsed JSON (or {error}).
 * Fail-soft: the caller surfaces the error text to the agent.
 */
function synapse(args, timeoutMs = 15000) {
  return new Promise((resolve) => {
    execFile(
      "python3",
      [SYNAPSE_CLI, ...args],
      { cwd: VAULT, timeout: timeoutMs, env: { ...process.env, VAULT_ROOT: VAULT, PYTHONUTF8: "1" } },
      (err, stdout, stderr) => {
        if (err && !stdout) {
          resolve({ error: String(stderr || err.message || err).trim() });
          return;
        }
        try {
          resolve(JSON.parse(stdout));
        } catch {
          resolve({ error: `synapse output nao-JSON: ${String(stdout).slice(0, 400)}` });
        }
      }
    );
  });
}

// ---------------------------------------------------------------------------
// FalkorDB client (via Redis)
// ---------------------------------------------------------------------------

let redisClient = null;

async function getRedis() {
  if (redisClient && redisClient.isReady) return redisClient;
  redisClient = createClient({
    socket: { host: FALKOR_HOST, port: FALKOR_PORT, connectTimeout: 5000 },
  });
  redisClient.on("error", () => {}); // suppress unhandled errors
  await redisClient.connect();
  return redisClient;
}

/**
 * Execute a FalkorDB GRAPH.QUERY and return parsed rows.
 * Returns { rows: [...], error: null } or { rows: [], error: "message" }.
 */
async function graphQuery(cypher) {
  try {
    const r = await getRedis();
    const raw = await r.sendCommand(["GRAPH.QUERY", GRAPH, cypher, "--compact"]);
    return { rows: parseFalkorResult(raw), error: null };
  } catch (err) {
    return { rows: [], error: String(err.message || err) };
  }
}

function parseFalkorResult(raw) {
  if (!Array.isArray(raw) || raw.length < 2) return [];
  const headers = raw[0];
  const dataRows = raw[1];
  if (!Array.isArray(headers) || !Array.isArray(dataRows)) return [];

  const colNames = headers.map((col) => {
    if (Array.isArray(col) && col.length >= 2) return col[1];
    return String(col);
  });

  return dataRows.map((row) => {
    if (!Array.isArray(row)) return row;
    const obj = {};
    row.forEach((cell, i) => {
      const key = colNames[i] ?? `col${i}`;
      obj[key] = unwrapCell(cell);
    });
    return obj;
  });
}

function unwrapCell(cell) {
  if (!Array.isArray(cell) || cell.length < 2) return cell;
  const [typeId, val] = cell;
  switch (typeId) {
    case 1: return null;
    case 2: return val;
    case 3: return Number(val);
    case 4: return parseFloat(val);
    case 5: return Boolean(val);
    case 6: return Array.isArray(val) ? val.map(unwrapCell) : val;
    default: return val;
  }
}

function safeId(id) {
  return String(id).replace(/'/g, "\\'");
}

// ---------------------------------------------------------------------------
// MCP Server setup
// ---------------------------------------------------------------------------

const server = new McpServer({
  name: "secondbrain-mcp",
  version: "1.0.0",
});

// ---------------------------------------------------------------------------
// Tool: query_graph
// ---------------------------------------------------------------------------

server.tool(
  "query_graph",
  "Execute an arbitrary Cypher query against the second-brain knowledge graph (FalkorDB). Returns result rows.",
  { cypher: z.string().describe("Cypher query string") },
  async ({ cypher }) => {
    const { rows, error } = await graphQuery(cypher);
    if (error) {
      return { content: [{ type: "text", text: `Error: ${error}` }], isError: true };
    }
    return {
      content: [{ type: "text", text: JSON.stringify(rows, null, 2) }],
    };
  }
);

// ---------------------------------------------------------------------------
// Tool: multi_hop
// ---------------------------------------------------------------------------

server.tool(
  "multi_hop",
  "Graph traversal from an entity (by id). Returns all neighbors up to given depth.",
  {
    entity_id: z.string().describe("Entity slug/id (e.g. 'meu-projeto', 'cqrs', 'outbox-inbox')"),
    depth: z.number().int().min(1).max(4).default(2).describe("Traversal depth (default 2)"),
  },
  async ({ entity_id, depth }) => {
    const id = safeId(entity_id);
    const cypher = `MATCH (n {id: '${id}'})-[r*1..${depth}]-(m) RETURN m.id, m.name, labels(m), type(r) LIMIT 100`;
    const { rows, error } = await graphQuery(cypher);
    if (error) {
      return { content: [{ type: "text", text: `Error: ${error}` }], isError: true };
    }
    return { content: [{ type: "text", text: JSON.stringify(rows, null, 2) }] };
  }
);

// ---------------------------------------------------------------------------
// Tool: entity_neighbors
// ---------------------------------------------------------------------------

server.tool(
  "entity_neighbors",
  "Returns direct neighbors (depth=1) of an entity. Alias for multi_hop with depth=1.",
  {
    entity_id: z.string().describe("Entity slug/id"),
  },
  async ({ entity_id }) => {
    const id = safeId(entity_id);
    const cypher = `MATCH (n {id: '${id}'})-[r]-(m) RETURN m.id, m.name, labels(m), type(r) LIMIT 50`;
    const { rows, error } = await graphQuery(cypher);
    if (error) {
      return { content: [{ type: "text", text: `Error: ${error}` }], isError: true };
    }
    return { content: [{ type: "text", text: JSON.stringify(rows, null, 2) }] };
  }
);

// ---------------------------------------------------------------------------
// Tool: why_decision
// ---------------------------------------------------------------------------

server.tool(
  "why_decision",
  "Returns entities referenced by an ADR and projects affected. Explains why a decision was made.",
  {
    adr_slug: z.string().describe("Decision/ADR slug (e.g. '2026-04-11-cqrs-source-of-truth')"),
  },
  async ({ adr_slug }) => {
    const id = safeId(adr_slug);

    const [refResult, projResult] = await Promise.all([
      graphQuery(
        `MATCH (d:Decision {id: '${id}'})-[r:REFERENCES]->(e) RETURN e.id, e.name, labels(e), type(r)`
      ),
      graphQuery(
        `MATCH (p:Project)-[r:HAS_DECISION]->(d:Decision {id: '${id}'}) RETURN p.id, p.name`
      ),
    ]);

    const output = {
      decision: adr_slug,
      references: refResult.rows,
      affected_projects: projResult.rows,
      errors: [refResult.error, projResult.error].filter(Boolean),
    };
    return { content: [{ type: "text", text: JSON.stringify(output, null, 2) }] };
  }
);

// ---------------------------------------------------------------------------
// Tool: recall — recall associativo (semantico + sinapses + forca de uso)
// ---------------------------------------------------------------------------

server.tool(
  "recall",
  "Associative recall over the second-brain: semantic seeds (Qdrant) + spreading activation over weighted synapses + memory strength. Each result carries the chain of memories that led to it. Use `seed` instead of `query` to expand associatively from a specific note slug.",
  {
    query: z.string().optional().describe("Natural-language query (semantic seeding)"),
    seed: z.string().optional().describe("Note slug/path to expand from (pure associative mode)"),
    k: z.number().int().min(1).max(20).default(8),
    kind: z.string().optional().describe("Filter: decisions|learnings|patterns|features|projects|..."),
    project: z.string().optional().describe("Filter by project slug"),
  },
  async ({ query, seed, k, kind, project }) => {
    const args = ["recall", "--json", "--k", String(k)];
    if (seed) args.push("--seed", seed);
    else if (query) args.push(query);
    else return { content: [{ type: "text", text: "Error: informe query ou seed" }], isError: true };
    if (kind) args.push("--kind", kind);
    if (project) args.push("--project", project);
    const out = await synapse(args);
    if (out.error) {
      return { content: [{ type: "text", text: `Error: ${out.error}` }], isError: true };
    }
    return { content: [{ type: "text", text: JSON.stringify(out, null, 2) }] };
  }
);

// ---------------------------------------------------------------------------
// Tool: memory_chain — caminho sinaptico entre duas memorias
// ---------------------------------------------------------------------------

server.tool(
  "memory_chain",
  "Explains how two memories connect: strongest synaptic path between two notes (slugs), with edge kinds and weights.",
  {
    from: z.string().describe("Note slug/path of the starting memory"),
    to: z.string().describe("Note slug/path of the target memory"),
    max_hops: z.number().int().min(1).max(8).default(6),
  },
  async ({ from, to, max_hops }) => {
    const out = await synapse(["explain", from, to, "--max-hops", String(max_hops), "--json"]);
    if (out.error) {
      return { content: [{ type: "text", text: `Error: ${out.error}` }], isError: true };
    }
    return { content: [{ type: "text", text: JSON.stringify(out, null, 2) }] };
  }
);

// ---------------------------------------------------------------------------
// Tool: reinforce — reforco hebbiano explicito
// ---------------------------------------------------------------------------

server.tool(
  "reinforce",
  "Hebbian reinforcement: strengthens synapses between memories co-activated in the recent window (or a given session id). Call after a productive work block so what was used together wires together.",
  {
    session: z.string().optional().describe("Session id to reinforce (default: recent window)"),
    window_minutes: z.number().int().min(5).max(1440).default(240),
  },
  async ({ session, window_minutes }) => {
    const args = ["reinforce", "--window", String(window_minutes)];
    if (session) args.push("--session", session);
    // saida texto, nao JSON — captura direta
    const out = await new Promise((resolve) => {
      execFile("python3", [SYNAPSE_CLI, ...args],
        { cwd: VAULT, timeout: 15000, env: { ...process.env, VAULT_ROOT: VAULT, PYTHONUTF8: "1" } },
        (_err, stdout, stderr) => resolve(String(stdout || stderr).trim()));
    });
    return { content: [{ type: "text", text: out }] };
  }
);

// ---------------------------------------------------------------------------
// Tool: find_similar_decisions
// ---------------------------------------------------------------------------

server.tool(
  "find_similar_decisions",
  "Find decisions similar to the given text. Uses associative recall (semantic + synapses) when the local stack is online; falls back to keyword search in Decision nodes.",
  {
    text: z.string().describe("Search keywords"),
  },
  async ({ text }) => {
    // caminho preferido: recall associativo restrito a decisoes
    const out = await synapse(["recall", text, "--json", "--k", "8", "--kind", "decisions"]);
    if (!out.error && Array.isArray(out.results) && out.results.length > 0) {
      const rows = out.results.map((r) => ({
        path: r.path, title: r.title, score: r.score, chain: r.chain,
      }));
      return { content: [{ type: "text", text: JSON.stringify(rows, null, 2) }] };
    }
    // fallback keyword (stack offline)
    const words = text
      .toLowerCase()
      .split(/\s+/)
      .filter((w) => w.length > 3)
      .slice(0, 5);

    if (words.length === 0) {
      const { rows, error } = await graphQuery(
        "MATCH (d:Decision) RETURN d.id, d.name, d.date LIMIT 10"
      );
      if (error) return { content: [{ type: "text", text: `Error: ${error}` }], isError: true };
      return { content: [{ type: "text", text: JSON.stringify(rows, null, 2) }] };
    }

    const conditions = words
      .map((w) => `toLower(d.id) CONTAINS '${w}' OR toLower(d.name) CONTAINS '${w}'`)
      .join(" OR ");
    const cypher = `MATCH (d:Decision) WHERE ${conditions} RETURN d.id, d.name, d.date LIMIT 10`;
    const { rows, error } = await graphQuery(cypher);
    if (error) return { content: [{ type: "text", text: `Error: ${error}` }], isError: true };
    return { content: [{ type: "text", text: JSON.stringify(rows, null, 2) }] };
  }
);

// ---------------------------------------------------------------------------
// Tool: get_project_state
// ---------------------------------------------------------------------------

server.tool(
  "get_project_state",
  "Returns graph information for a project (neighbors, patterns used, decisions) plus the raw state.md file.",
  {
    slug: z.string().describe("Project slug (e.g. 'meu-projeto')"),
  },
  async ({ slug }) => {
    const id = safeId(slug);
    const [neighborsResult, patternsResult, decisionsResult] = await Promise.all([
      graphQuery(`MATCH (p:Project {id: '${id}'})-[r]-(m) RETURN m.id, m.name, labels(m), type(r) LIMIT 50`),
      graphQuery(`MATCH (p:Project {id: '${id}'})-[:USES_PATTERN]->(pat:Pattern) RETURN pat.id, pat.name`),
      graphQuery(`MATCH (p:Project {id: '${id}'})-[:HAS_DECISION]->(d:Decision) RETURN d.id, d.name, d.date`),
    ]);

    // Read state.md if available
    let stateMd = null;
    const statePath = join(VAULT, "_knowledge", "projects", slug, "state.md");
    if (existsSync(statePath)) {
      try {
        stateMd = readFileSync(statePath, "utf-8");
      } catch {
        stateMd = "(could not read state.md)";
      }
    }

    const output = {
      project: slug,
      neighbors: neighborsResult.rows,
      patterns_used: patternsResult.rows,
      decisions: decisionsResult.rows,
      state_md: stateMd,
      errors: [neighborsResult.error, patternsResult.error, decisionsResult.error].filter(Boolean),
    };
    return { content: [{ type: "text", text: JSON.stringify(output, null, 2) }] };
  }
);

// ---------------------------------------------------------------------------
// Tool: graph_stats
// ---------------------------------------------------------------------------

server.tool(
  "graph_stats",
  "Returns entity counts per type and relation counts per kind in the knowledge graph.",
  {},
  async () => {
    const entityTypes = ["Project", "Pattern", "Feature", "Decision", "Learning", "Technology"];
    const edgeKinds = ["USES_PATTERN", "USES_FEATURE", "REFERENCES", "HAS_DECISION", "REFINES"];

    const results = await Promise.all([
      ...entityTypes.map((t) =>
        graphQuery(`MATCH (n:${t}) RETURN count(n) AS cnt`).then((r) => ({
          key: t,
          value: r.rows[0]?.cnt ?? 0,
          error: r.error,
        }))
      ),
      ...edgeKinds.map((k) =>
        graphQuery(`MATCH ()-[r:${k}]->() RETURN count(r) AS cnt`).then((r) => ({
          key: k,
          value: r.rows[0]?.cnt ?? 0,
          error: r.error,
        }))
      ),
      graphQuery("MATCH (n) RETURN count(n) AS cnt").then((r) => ({
        key: "total_nodes",
        value: r.rows[0]?.cnt ?? 0,
        error: r.error,
      })),
      graphQuery("MATCH ()-[r]->() RETURN count(r) AS cnt").then((r) => ({
        key: "total_edges",
        value: r.rows[0]?.cnt ?? 0,
        error: r.error,
      })),
    ]);

    const stats = {};
    const errors = [];
    for (const { key, value, error } of results) {
      stats[key] = value;
      if (error) errors.push(`${key}: ${error}`);
    }

    const output = { stats, errors: errors.length > 0 ? errors : undefined };
    return { content: [{ type: "text", text: JSON.stringify(output, null, 2) }] };
  }
);

// ---------------------------------------------------------------------------
// Start server
// ---------------------------------------------------------------------------

const transport = new StdioServerTransport();
await server.connect(transport);
