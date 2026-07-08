#!/bin/bash
# Valida a camada sinaptica: build, arestas tipadas, recall associativo offline,
# reforco hebbiano (sinaptogenese), decay/poda e compactacao do current-state.
set -u
cd "$(dirname "$0")/.." || exit 2

REAL_VAULT="$(pwd)"
TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT
# fixture NUNCA projeta no FalkorDB real
export SB_SYNAPSE_AUTOSYNC=0

FAIL=0
check() {
  local desc="$1"; shift
  if "$@" >/dev/null 2>&1; then
    echo "  ok: $desc"
  else
    echo "  FAIL: $desc"
    FAIL=1
  fi
}
check_contains() {
  local desc="$1" haystack="$2" needle="$3"
  if [ "${haystack#*"$needle"}" != "$haystack" ]; then
    echo "  ok: $desc"
  else
    echo "  FAIL: $desc"
    FAIL=1
  fi
}

# ---------- fixture vault ----------
mkdir -p "$TMP/_memory" "$TMP/_patterns" "$TMP/_decisions" "$TMP/_learnings" \
  "$TMP/_knowledge/projects/sample"

cat > "$TMP/_patterns/idempotency.md" <<'EOF'
---
tags: [pattern, messaging, reliability]
status: active
created: 2026-01-01
---
# Idempotency

Padrao de idempotencia. Ver [[outbox-inbox]] duas vezes: [[outbox-inbox]].
EOF

cat > "$TMP/_patterns/outbox-inbox.md" <<'EOF'
---
tags: [pattern, messaging, reliability]
status: active
created: 2026-01-01
---
# Outbox/Inbox

## Related
- [[idempotency]]
EOF

cat > "$TMP/_decisions/2026-01-02-decisao-nova.md" <<'EOF'
---
tags: [decision, messaging]
status: active
created: 2026-01-02
---
# Decisao nova

Evolui: [[2026-01-01-decisao-velha]]

Contexto usa [[idempotency]].
EOF

cat > "$TMP/_decisions/2026-01-01-decisao-velha.md" <<'EOF'
---
tags: [decision, messaging]
status: superseded
created: 2026-01-01
---
# Decisao velha

Texto.
EOF

cat > "$TMP/_knowledge/projects/sample/sample.md" <<'EOF'
---
tags: [project, fintech-sample]
status: active
created: 2026-01-03
---
# Sample

Hub do projeto. Usa [[idempotency]].
EOF

cat > "$TMP/_knowledge/projects/sample/gotchas.md" <<'EOF'
---
tags: [project, gotchas-sample]
status: active
created: 2026-01-03
---
# Sample — Gotchas

Gotcha sem link em prosa.
EOF

cat > "$TMP/_learnings/aprendizado-solto.md" <<'EOF'
---
tags: [learning, messaging]
status: active
created: 2026-01-04
---
# Aprendizado solto

Sem links.
EOF

SYN="python3 $REAL_VAULT/_bootstrap/agentic/synapse/main.py"

echo "== build =="
BUILD_OUT="$(VAULT_ROOT="$TMP" $SYN build 2>&1)"
echo "$BUILD_OUT" | sed 's/^/    /'
check_contains "build roda e reporta nos" "$BUILD_OUT" "nos"

STATUS_JSON="$(VAULT_ROOT="$TMP" $SYN status --json 2>/dev/null)"
check "7 nos criados"            python3 -c "import json,sys; d=json.loads('''$STATUS_JSON'''); sys.exit(0 if d['nodes']==7 else 1)"
check "aresta WIKILINK existe"   python3 -c "import json,sys; d=json.loads('''$STATUS_JSON'''); sys.exit(0 if d['edges_by_kind'].get('WIKILINK',0)>=2 else 1)"
check "aresta RELATED existe"    python3 -c "import json,sys; d=json.loads('''$STATUS_JSON'''); sys.exit(0 if d['edges_by_kind'].get('RELATED',0)>=1 else 1)"
check "aresta SUPERSEDES existe" python3 -c "import json,sys; d=json.loads('''$STATUS_JSON'''); sys.exit(0 if d['edges_by_kind'].get('SUPERSEDES',0)>=1 else 1)"
check "aresta STRUCTURAL existe" python3 -c "import json,sys; d=json.loads('''$STATUS_JSON'''); sys.exit(0 if d['edges_by_kind'].get('STRUCTURAL',0)>=1 else 1)"

echo "== recall associativo offline (--seed) =="
RECALL_JSON="$(VAULT_ROOT="$TMP" $SYN recall --seed idempotency --k 5 --json --no-log 2>/dev/null)"
check "seed retorna resultados" python3 -c "
import json, sys
d = json.loads('''$RECALL_JSON''')
paths = [r['path'] for r in d['results']]
sys.exit(0 if '_patterns/outbox-inbox.md' in paths else 1)"
check "resultado carrega cadeia" python3 -c "
import json, sys
d = json.loads('''$RECALL_JSON''')
chains = [r for r in d['results'] if not r['seed'] and len(r.get('chain', [])) >= 2]
sys.exit(0 if chains else 1)"

echo "== recall semantico fail-soft com stack offline =="
VAULT_ROOT="$TMP" SB_QDRANT_URL="http://127.0.0.1:1" SB_OLLAMA_URL="http://127.0.0.1:1" \
  $SYN recall "qualquer coisa" >/dev/null 2>&1
RC=$?
check "recall query offline retorna erro acionavel (exit 2)" test "$RC" -eq 2

echo "== fisiologia: ativacao + reforco + sinaptogenese =="
VAULT_ROOT="$TMP" $SYN activate --paths "$TMP/_learnings/aprendizado-solto.md" "$TMP/_knowledge/projects/sample/gotchas.md" --source read --session s1 >/dev/null 2>&1
VAULT_ROOT="$TMP" $SYN reinforce --session s1 >/dev/null 2>&1
VAULT_ROOT="$TMP" $SYN reinforce --session s1 >/dev/null 2>&1
R3="$(VAULT_ROOT="$TMP" $SYN reinforce --session s1 2>&1)"
echo "    $R3"
check_contains "3a co-ativacao cria sinapse LEARNED" "$R3" "1 aprendidas"

STATUS2="$(VAULT_ROOT="$TMP" $SYN status --json 2>/dev/null)"
check "learned_edges = 1" python3 -c "import json,sys; d=json.loads('''$STATUS2'''); sys.exit(0 if d['learned_edges']==1 else 1)"

echo "== decay + poda =="
# forca last_decay para 400 dias atras -> boost 0.4 decai abaixo do piso 0.15
VAULT_ROOT="$TMP" python3 - <<PYEOF
import sys
sys.path.insert(0, "$REAL_VAULT/_bootstrap/agentic/synapse")
import db
conn = db.connect()
db.set_meta(conn, "last_decay", "2025-06-01T00:00:00+00:00")
conn.commit(); conn.close()
PYEOF
DECAY_OUT="$(VAULT_ROOT="$TMP" $SYN decay 2>&1)"
echo "    $DECAY_OUT"
check_contains "LEARNED fraca e podada" "$DECAY_OUT" "1 aprendidas podadas"

echo "== consolidacao: compactacao do current-state =="
{
  printf -- '---\ntags: [memory, state, current]\nstatus: active\n---\n# Current State\n\n'
  for i in $(seq 1 15); do
    printf '## Last Update: 2026-01-%02d (task)\n\nRollup %d.\n\n' "$i" "$i"
  done
} > "$TMP/_memory/current-state.md"
CONS_OUT="$(VAULT_ROOT="$TMP" $SYN consolidate --keep 10 --no-dedup --no-falkor 2>&1)"
echo "$CONS_OUT" | sed 's/^/    /'
check_contains "compact move 5 secoes" "$CONS_OUT" "'moved': 5"
check "historico criado"             ls "$TMP/_memory/current-state-history/"
check "conteudo movido preservado"   grep -q "Rollup 15" "$TMP"/_memory/current-state-history/*.md
check "conteudo recente mantido"     grep -q "Rollup 10" "$TMP/_memory/current-state.md"
check "relatorio synapse-report escrito" test -f "$TMP/_memory/synapse-report.md"

echo ""
if [ "$FAIL" -eq 0 ]; then
  echo "test-synapse: OK"
  exit 0
else
  echo "test-synapse: FALHAS"
  exit 1
fi
