#!/bin/bash
# Todo .md em pastas curadas precisa abrir com frontmatter YAML (---).
# Excecoes: README.md, CLAUDE.md, RTK.md (top-level docs).
set -u
cd "$(dirname "$0")/.." || exit 2

CURATED_DIRS=(
  "_decisions"
  "_learnings"
  "_patterns"
  "_features"
  "_cores"
  "_knowledge/projects"
  "_content"
)

EXCLUDE_PATTERN='/(README|CLAUDE|RTK|MASTER-INDEX|TAG-TAXONOMY|CONCEPT-INDEX|PATTERN-MATRIX|FEATURE-CATALOG|SNAPSHOT)\.md$'

FAIL=0
CHECKED=0

for d in "${CURATED_DIRS[@]}"; do
  [ -d "$d" ] || continue
  while IFS= read -r f; do
    if echo "$f" | grep -qE "$EXCLUDE_PATTERN"; then continue; fi
    CHECKED=$((CHECKED + 1))
    first_line=$(head -n 1 "$f" 2>/dev/null)
    if [ "$first_line" != "---" ]; then
      echo "FAIL: $f (sem frontmatter na linha 1)"
      FAIL=$((FAIL + 1))
    fi
  done < <(find "$d" -name "*.md" -type f 2>/dev/null)
done

if [ $FAIL -eq 0 ]; then
  echo "OK: $CHECKED arquivo(s) com frontmatter valido"
  exit 0
fi
echo "FAIL: $FAIL de $CHECKED arquivo(s) sem frontmatter"
exit 1
