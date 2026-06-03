#!/usr/bin/env bash
# install.sh — instala git hooks compartilhados em ~/.config/git/hooks-shared/.
#
# Após rodar, configurar git para usar:
#   git config --global core.hooksPath ~/.config/git/hooks-shared
#
# Aplicação seletiva por repo (recomendado): definir core.hooksPath apenas nos
# repos onde você quer captura ativa.

set -euo pipefail
HOOKS_DIR="$HOME/.config/git/hooks-shared"
SOURCE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

mkdir -p "$HOOKS_DIR"
for hook in post-commit post-merge; do
  cp "$SOURCE_DIR/$hook" "$HOOKS_DIR/$hook"
  chmod +x "$HOOKS_DIR/$hook"
  echo "  installed: $HOOKS_DIR/$hook"
done

echo
echo "Para ATIVAR globalmente (todos os repos):"
echo "  git config --global core.hooksPath $HOOKS_DIR"
echo
echo "Para ATIVAR por repo (recomendado):"
echo "  cd <repo> && git config core.hooksPath $HOOKS_DIR"
echo
echo "Repos sugeridos para ativar (com state.md no vault):"
ls -d <projects-root>/*/.git 2>/dev/null | sed 's|/.git$||' | head -10
