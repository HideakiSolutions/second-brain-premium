#!/bin/bash
# Cron: weekly-vault-lint
# Execução recomendada: toda segunda-feira às 09:00
# Registrado pelo install.sh:
#   0 9 * * 1 bash {VAULT}/_bootstrap/scripts/weekly-vault-lint.sh >> {VAULT}/.logs/weekly-vault-lint.log 2>&1
#
# Lint estrutural do vault — não requer LLM.
# Verifica consistência de índices e frontmatter.

# Auto-detectar vault: script está em _bootstrap/scripts/, vault é 2 níveis acima
VAULT="${VAULT:-$(cd "$(dirname "$0")"/../.. && pwd)}"

LINT_REPORT="$VAULT/_memory/lint-latest.md"
HEARTBEAT="$VAULT/_memory/heartbeat-latest.md"
LOG="$VAULT/_memory/activity-log.md"
TIMESTAMP=$(date '+%Y-%m-%d %H:%M')
TODAY=$(date '+%Y-%m-%d')

# Garantir que _memory/ existe
mkdir -p "$VAULT/_memory"

CRITICAL=0
WARNINGS=0
REPORT_BODY=""

# --- 1. Sincronismo MASTER-INDEX vs pastas de projeto (se existir) ---
if [ -f "$VAULT/_index/MASTER-INDEX.md" ] && [ -d "$VAULT/_knowledge/projects" ]; then
  PROJECTS_IN_INDEX=$(grep -o 'projects/[^/]*' "$VAULT/_index/MASTER-INDEX.md" 2>/dev/null | sed 's|projects/||' | sort -u)
  PROJECTS_ON_DISK=$(find "$VAULT/_knowledge/projects" -mindepth 1 -maxdepth 1 -type d -printf '%f\n' 2>/dev/null | sort -u)

  for proj in $PROJECTS_ON_DISK; do
    # Ignorar pasta de exemplo
    [ "$proj" = "_exemplo" ] && continue
    if ! echo "$PROJECTS_IN_INDEX" | grep -qw "$proj"; then
      REPORT_BODY+="- MASTER-INDEX: pasta '$proj' existe mas nao esta no indice\n"
      CRITICAL=$((CRITICAL + 1))
    fi
  done

  for proj in $PROJECTS_IN_INDEX; do
    if [ ! -d "$VAULT/_knowledge/projects/$proj" ]; then
      REPORT_BODY+="- MASTER-INDEX: entrada '$proj' sem pasta correspondente\n"
      CRITICAL=$((CRITICAL + 1))
    fi
  done
fi

# --- 2. Frontmatter obrigatório em _patterns/ e _features/ (se existirem) ---
MISSING_FRONTMATTER=0
for dir in "$VAULT/_patterns" "$VAULT/_features"; do
  [ -d "$dir" ] || continue
  for f in "$dir"/*.md; do
    [ -f "$f" ] || continue
    [ "$(basename "$f")" = "_exemplo.md" ] && continue
    missing_fields=""
    grep -q "^tags:" "$f"    || missing_fields="tags "
    grep -q "^status:" "$f"  || missing_fields="${missing_fields}status "
    grep -q "^created:" "$f" || missing_fields="${missing_fields}created"
    if [ -n "$missing_fields" ]; then
      REPORT_BODY+="- Frontmatter: $(basename "$f") — campos ausentes: ${missing_fields}\n"
      MISSING_FRONTMATTER=$((MISSING_FRONTMATTER + 1))
      CRITICAL=$((CRITICAL + 1))
    fi
  done
done

# Frontmatter em projetos (se existir)
if [ -d "$VAULT/_knowledge/projects" ]; then
  for proj_dir in "$VAULT/_knowledge/projects"/*/; do
    [ "$(basename "$proj_dir")" = "_exemplo" ] && continue
    for f in "$proj_dir"*.md; do
      [ -f "$f" ] || continue
      [ "$(basename "$f")" = "_exemplo.md" ] && continue
      missing_fields=""
      grep -q "^tags:" "$f"    || missing_fields="tags "
      grep -q "^status:" "$f"  || missing_fields="${missing_fields}status "
      grep -q "^created:" "$f" || missing_fields="${missing_fields}created"
      if [ -n "$missing_fields" ]; then
        REPORT_BODY+="- Frontmatter: projects/$(basename "$proj_dir")/$(basename "$f") — campos: ${missing_fields}\n"
        MISSING_FRONTMATTER=$((MISSING_FRONTMATTER + 1))
        CRITICAL=$((CRITICAL + 1))
      fi
    done
  done
fi

# --- 3. Notas obsoletas (status active, updated > 30 dias) ---
STALE_NOTES=0
# Compatível com GNU date (Linux) e BSD date (macOS)
THIRTY_DAYS_AGO=$(date -d "30 days ago" '+%Y-%m-%d' 2>/dev/null || date -v-30d '+%Y-%m-%d' 2>/dev/null || echo "1970-01-01")
for dir in "$VAULT/_patterns" "$VAULT/_features"; do
  [ -d "$dir" ] || continue
  for f in "$dir"/*.md; do
    [ -f "$f" ] || continue
    [ "$(basename "$f")" = "_exemplo.md" ] && continue
    updated=$(grep "^updated:" "$f" 2>/dev/null | sed 's/updated: //' | tr -d ' ')
    status=$(grep "^status:" "$f" 2>/dev/null | sed 's/status: //' | tr -d ' ')
    if [ "$status" = "active" ] && [ -n "$updated" ] && [ "$updated" \< "$THIRTY_DAYS_AGO" ]; then
      REPORT_BODY+="- Obsoleto: $(basename "$f") — ultimo update: $updated\n"
      STALE_NOTES=$((STALE_NOTES + 1))
      WARNINGS=$((WARNINGS + 1))
    fi
  done
done

# --- 4. Escrever relatório ---
TOTAL=$((CRITICAL + WARNINGS))
SCORE=10
[ "$CRITICAL" -gt 0 ] && SCORE=$((10 - CRITICAL))
[ "$SCORE" -lt 0 ] && SCORE=0

cat > "$LINT_REPORT" <<EOF
---
tags: [memory, lint]
updated: $TODAY
---

# Vault Lint — $TIMESTAMP

**Score:** $SCORE/10 | **Defeitos críticos:** $CRITICAL | **Avisos:** $WARNINGS

| Verificação | Defeitos | Status |
|-------------|---------|--------|
| Sincronismo de índices | — | $([ "$CRITICAL" -eq 0 ] && echo "OK" || echo "REVISAR") |
| Frontmatter obrigatório | $MISSING_FRONTMATTER | $([ "$MISSING_FRONTMATTER" -eq 0 ] && echo "OK" || echo "FALHOU") |
| Notas obsoletas | $STALE_NOTES | $([ "$STALE_NOTES" -eq 0 ] && echo "OK" || echo "ATENCAO") |

$([ "$TOTAL" -gt 0 ] && printf '## Defeitos\n\n%b' "$REPORT_BODY")
$([ "$TOTAL" -eq 0 ] && echo "Vault em boa saude — nenhum defeito encontrado.")

EOF

# Alerta no heartbeat se crítico
if [ "$CRITICAL" -gt 5 ] && [ -f "$HEARTBEAT" ]; then
  printf '\n## Lint Alert (%s)\n%d defeitos críticos. Execute /lint para detalhes.\n' \
    "$TODAY" "$CRITICAL" >> "$HEARTBEAT"
fi

# Activity log — sempre append
printf '\n## [%s] lint | %d defeitos criticos, %d avisos (score %d/10)\n' \
  "$TIMESTAMP" "$CRITICAL" "$WARNINGS" "$SCORE" >> "$LOG"

exit 0
