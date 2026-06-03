#!/usr/bin/env bash
# install.sh — installer agnostico e interativo do second-brain-premium.
#
# Sem paths fixos: descobre raiz do scaffold via $BASH_SOURCE e pergunta cada
# destino ao usuario. Idempotente. Faz backup de qualquer arquivo externo
# antes de modificar. Nao requer sudo.
#
# Uso:
#   ./install.sh                  # interativo (padrao)
#   ./install.sh --yes            # nao-interativo, usa defaults
#   ./install.sh --dry-run        # nao executa nada, so mostra o plano
#   ./install.sh --uninstall      # reverte instalacao
#   ./install.sh --minimal        # so commands; sem hooks, skills Codex, CLAUDE.md
#   ./install.sh --debug          # log verboso
#   ./install.sh --help           # esta mensagem
#
# Componentes que o installer pode integrar:
#   1. Slash commands  -> ~/.claude/commands/  (Claude Code)
#   2. Skills Codex     -> ~/.codex/skills/    (Codex CLI)
#   3. Hooks            -> ~/.claude/settings.json (merge idempotente)
#   4. CLAUDE.md global -> ~/.claude/CLAUDE.md (append seção Second Brain)
#   5. Crons            -> linhas para colar manualmente no crontab
#   6. Stack semantico  -> instrucoes para subir Qdrant + Ollama (opcional)
#
# Cada componente e opt-in: usuario aprova individualmente.

set -uo pipefail

# ============================================================================
# Constants & defaults
# ============================================================================

VAULT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SCRIPT_NAME="$(basename "${BASH_SOURCE[0]}")"
TIMESTAMP="$(date +%Y%m%d-%H%M%S)"

INTERACTIVE=1
DRY_RUN=0
UNINSTALL=0
MINIMAL=0
DEBUG=0

# Cores ANSI (fallback vazio em terminais que nao suportam)
if [ -t 1 ] && [ "${TERM:-dumb}" != "dumb" ]; then
  C_RESET=$'\033[0m'
  C_BOLD=$'\033[1m'
  C_DIM=$'\033[2m'
  C_RED=$'\033[31m'
  C_GREEN=$'\033[32m'
  C_YELLOW=$'\033[33m'
  C_BLUE=$'\033[34m'
  C_CYAN=$'\033[36m'
else
  C_RESET=""; C_BOLD=""; C_DIM=""
  C_RED=""; C_GREEN=""; C_YELLOW=""; C_BLUE=""; C_CYAN=""
fi

# ============================================================================
# Helpers
# ============================================================================

usage() {
  sed -n '2,25p' "$0" | sed 's/^# \?//'
  exit 0
}

log()    { printf "%s\n" "$*"; }
info()   { printf "%s[info]%s %s\n" "$C_BLUE" "$C_RESET" "$*"; }
ok()     { printf "%s[ok]%s   %s\n" "$C_GREEN" "$C_RESET" "$*"; }
warn()   { printf "%s[warn]%s %s\n" "$C_YELLOW" "$C_RESET" "$*"; }
err()    { printf "%s[err]%s  %s\n" "$C_RED" "$C_RESET" "$*" >&2; }
debug()  { [ "$DEBUG" -eq 1 ] && printf "%s[dbg]%s  %s\n" "$C_DIM" "$C_RESET" "$*" >&2 || true; }
hr()     { printf -- "%s---------------------------------------------------------------%s\n" "$C_DIM" "$C_RESET"; }
title()  { printf "\n%s%s== %s ==%s\n" "$C_BOLD" "$C_CYAN" "$*" "$C_RESET"; }

# Confirma com [Y/n] ou [y/N]. Em modo --yes, usa o default.
# Uso: confirm "Continuar?" Y    -> default Y (Enter = sim)
#      confirm "Continuar?" N    -> default N (Enter = nao)
confirm() {
  local prompt="$1"
  local default="${2:-Y}"
  local hint reply
  if [ "$default" = "Y" ]; then hint="[Y/n]"; else hint="[y/N]"; fi
  if [ "$INTERACTIVE" -eq 0 ]; then
    [ "$default" = "Y" ] && return 0 || return 1
  fi
  while :; do
    printf "%s %s " "$prompt" "$hint" >&2
    read -r reply </dev/tty || reply=""
    reply="${reply:-$default}"
    case "$reply" in
      [Yy]|[Yy][Ee][Ss]|[Ss]|[Ss][Ii][Mm]) return 0 ;;
      [Nn]|[Nn][Oo]|[Nn][Aa][Oo]|[Nn][AÃ][Oo]) return 1 ;;
      *) printf "%sResponda Y ou N.%s\n" "$C_YELLOW" "$C_RESET" >&2 ;;
    esac
  done
}

# Pergunta path com default. Expande ~.
# Uso: path=$(ask_path "Diretorio destino?" "$HOME/.claude/commands")
ask_path() {
  local prompt="$1"
  local default="$2"
  local reply
  if [ "$INTERACTIVE" -eq 0 ]; then
    printf "%s\n" "$default"
    return 0
  fi
  printf "%s %s[%s]%s " "$prompt" "$C_DIM" "$default" "$C_RESET" >&2
  read -r reply </dev/tty || reply=""
  reply="${reply:-$default}"
  # expande ~ no inicio
  case "$reply" in
    "~/"*) reply="${HOME}/${reply#~/}" ;;
    "~") reply="${HOME}" ;;
  esac
  printf "%s\n" "$reply"
}

# Backup de arquivo antes de modificar
backup_file() {
  local f="$1"
  if [ -f "$f" ]; then
    local b="${f}.bak.${TIMESTAMP}"
    [ "$DRY_RUN" -eq 1 ] && info "(dry-run) backup $f -> $b" && return 0
    cp "$f" "$b" && debug "backup criado: $b"
  fi
}

# Detecta plataforma
detect_platform() {
  case "$(uname -s)" in
    Linux*)
      if grep -qiE "microsoft|wsl" /proc/version 2>/dev/null; then
        echo "wsl"
      else
        echo "linux"
      fi
      ;;
    Darwin*) echo "macos" ;;
    MINGW*|MSYS*|CYGWIN*) echo "git-bash" ;;
    *) echo "unknown" ;;
  esac
}

# Cria link simbolico (com fallback para copia em Windows sem perm de symlink)
link_or_copy() {
  local src="$1"
  local dst="$2"
  if [ "$DRY_RUN" -eq 1 ]; then
    info "(dry-run) link $dst -> $src"
    return 0
  fi
  if ln -sf "$src" "$dst" 2>/dev/null; then
    debug "symlink: $dst -> $src"
  else
    cp -f "$src" "$dst" 2>/dev/null && debug "copy: $src -> $dst" || {
      err "falha ao linkar/copiar $src para $dst"
      return 1
    }
  fi
}

# Conta items para summary
declare -A SUMMARY
inc() { SUMMARY[$1]=$((${SUMMARY[$1]:-0} + 1)); }

# ============================================================================
# Parse args
# ============================================================================

while [ $# -gt 0 ]; do
  case "$1" in
    --yes|-y)         INTERACTIVE=0; shift ;;
    --dry-run)        DRY_RUN=1; shift ;;
    --uninstall)      UNINSTALL=1; shift ;;
    --minimal)        MINIMAL=1; shift ;;
    --debug)          DEBUG=1; shift ;;
    --help|-h)        usage ;;
    *) err "argumento desconhecido: $1"; usage ;;
  esac
done

# ============================================================================
# Banner
# ============================================================================

PLATFORM="$(detect_platform)"

cat <<EOF
${C_BOLD}${C_CYAN}second-brain-premium installer${C_RESET}

  Scaffold root: ${C_DIM}${VAULT_ROOT}${C_RESET}
  Platform:      ${C_DIM}${PLATFORM}${C_RESET}
  Mode:          ${C_DIM}$([ "$INTERACTIVE" -eq 1 ] && echo "interativo" || echo "nao-interativo (--yes)")$([ "$DRY_RUN" -eq 1 ] && echo " + dry-run")$([ "$MINIMAL" -eq 1 ] && echo " + minimal")$([ "$UNINSTALL" -eq 1 ] && echo " + uninstall")${C_RESET}

EOF

# ============================================================================
# Prereqs
# ============================================================================

title "Pre-requisitos"

REQUIRED=("bash" "git")
OPTIONAL=("node" "npm" "claude" "codex" "docker" "jq" "python3" "crontab")

MISSING_REQ=()
for cmd in "${REQUIRED[@]}"; do
  if command -v "$cmd" >/dev/null 2>&1; then
    ok "$cmd: $(command -v "$cmd")"
  else
    err "$cmd: NAO INSTALADO (obrigatorio)"
    MISSING_REQ+=("$cmd")
  fi
done

for cmd in "${OPTIONAL[@]}"; do
  if command -v "$cmd" >/dev/null 2>&1; then
    info "$cmd (opcional): $(command -v "$cmd")"
  else
    warn "$cmd (opcional): nao encontrado"
  fi
done

if [ ${#MISSING_REQ[@]} -gt 0 ]; then
  err "instale os obrigatorios e tente novamente: ${MISSING_REQ[*]}"
  exit 1
fi

# ============================================================================
# Uninstall mode
# ============================================================================

if [ "$UNINSTALL" -eq 1 ]; then
  title "Modo uninstall"
  warn "este modo remove os symlinks criados pelo installer, mas NAO toca:"
  warn "  - o conteudo do scaffold (VAULT_ROOT)"
  warn "  - arquivos pessoais que voce criou"
  warn "  - backups criados (.bak.*)"
  warn "  - linhas no crontab (remova manualmente)"
  confirm "Continuar?" N || { info "cancelado pelo usuario"; exit 0; }

  CLAUDE_CMDS_DIR=$(ask_path "Diretorio dos commands Claude" "$HOME/.claude/commands")
  CODEX_SKILLS_DIR=$(ask_path "Diretorio das skills Codex" "$HOME/.codex/skills")

  # Remove symlinks que apontam para nosso VAULT_ROOT
  for f in "$CLAUDE_CMDS_DIR"/*.md; do
    [ -L "$f" ] || continue
    target=$(readlink "$f" 2>/dev/null || true)
    case "$target" in
      "$VAULT_ROOT"/*)
        [ "$DRY_RUN" -eq 1 ] && info "(dry-run) rm $f" || rm -f "$f"
        inc "commands_removed"
        ;;
    esac
  done

  for d in "$CODEX_SKILLS_DIR"/sb-*; do
    [ -L "$d" ] || continue
    target=$(readlink "$d" 2>/dev/null || true)
    case "$target" in
      "$VAULT_ROOT"/*)
        [ "$DRY_RUN" -eq 1 ] && info "(dry-run) rm $d" || rm -rf "$d"
        inc "skills_removed"
        ;;
    esac
  done

  ok "uninstall concluido"
  log "  commands removidos: ${SUMMARY[commands_removed]:-0}"
  log "  skills removidas:   ${SUMMARY[skills_removed]:-0}"
  log ""
  log "Para limpeza completa, edite manualmente:"
  log "  - $HOME/.claude/settings.json  (remova entradas hook apontando para $VAULT_ROOT)"
  log "  - $HOME/.claude/CLAUDE.md      (remova bloco 'Second Brain' se houver)"
  log "  - crontab -e                   (remova linhas de cron)"
  exit 0
fi

# ============================================================================
# Resolve destinos
# ============================================================================

title "Destinos de instalacao"

# Defaults — usuario pode redefinir
CLAUDE_HOME_DEFAULT="${CLAUDE_HOME:-$HOME/.claude}"
CODEX_HOME_DEFAULT="${CODEX_HOME:-$HOME/.codex}"

CLAUDE_HOME=$(ask_path "Diretorio config Claude Code" "$CLAUDE_HOME_DEFAULT")
CLAUDE_CMDS_DIR="$CLAUDE_HOME/commands"
CLAUDE_SETTINGS="$CLAUDE_HOME/settings.json"
CLAUDE_MD_GLOBAL="$CLAUDE_HOME/CLAUDE.md"

CODEX_HOME=$(ask_path "Diretorio config Codex CLI (deixe vazio para pular Codex)" "$CODEX_HOME_DEFAULT")
if [ -n "$CODEX_HOME" ]; then
  CODEX_SKILLS_DIR="$CODEX_HOME/skills"
else
  CODEX_SKILLS_DIR=""
fi

info "Claude commands:  $CLAUDE_CMDS_DIR"
info "Claude settings:  $CLAUDE_SETTINGS"
info "Claude CLAUDE.md: $CLAUDE_MD_GLOBAL"
[ -n "$CODEX_SKILLS_DIR" ] && info "Codex skills:     $CODEX_SKILLS_DIR" || warn "Codex: SKIP"

# ============================================================================
# 1. Slash commands Claude
# ============================================================================

title "1. Slash commands Claude (~37 comandos)"

if confirm "Instalar slash commands em $CLAUDE_CMDS_DIR?" Y; then
  if [ "$DRY_RUN" -eq 0 ]; then
    mkdir -p "$CLAUDE_CMDS_DIR"
  else
    info "(dry-run) mkdir -p $CLAUDE_CMDS_DIR"
  fi

  count=0
  for cmd in "$VAULT_ROOT"/.claude/commands/*.md; do
    [ -f "$cmd" ] || continue
    dst="$CLAUDE_CMDS_DIR/$(basename "$cmd")"
    link_or_copy "$cmd" "$dst" && count=$((count + 1))
  done
  ok "$count commands instalados"
  SUMMARY[commands]=$count
else
  warn "commands: SKIP"
fi

# ============================================================================
# 2. Skills Codex
# ============================================================================

if [ "$MINIMAL" -eq 0 ] && [ -n "$CODEX_SKILLS_DIR" ]; then
  title "2. Skills Codex (~37 ports paritarias)"

  if confirm "Instalar skills Codex em $CODEX_SKILLS_DIR?" Y; then
    if [ "$DRY_RUN" -eq 0 ]; then
      mkdir -p "$CODEX_SKILLS_DIR"
    else
      info "(dry-run) mkdir -p $CODEX_SKILLS_DIR"
    fi

    count=0
    for skill_dir in "$VAULT_ROOT"/.codex/skills/sb-*; do
      [ -d "$skill_dir" ] || continue
      dst="$CODEX_SKILLS_DIR/$(basename "$skill_dir")"
      link_or_copy "$skill_dir" "$dst" && count=$((count + 1))
    done
    ok "$count skills Codex instaladas"
    SUMMARY[skills]=$count
  else
    warn "skills Codex: SKIP"
  fi
else
  [ "$MINIMAL" -eq 1 ] && info "Skills Codex: SKIP (--minimal)" || info "Skills Codex: SKIP (Codex desabilitado)"
fi

# ============================================================================
# 3. Hooks em settings.json
# ============================================================================

if [ "$MINIMAL" -eq 0 ]; then
  title "3. Hooks Claude Code (settings.json)"

  if confirm "Configurar hooks em $CLAUDE_SETTINGS?" Y; then
    backup_file "$CLAUDE_SETTINGS"
    local_settings="$VAULT_ROOT/.claude/settings.json"

    if [ ! -f "$local_settings" ]; then
      err "settings.json local nao encontrado em $local_settings"
    elif [ "$DRY_RUN" -eq 1 ]; then
      info "(dry-run) merge $local_settings -> $CLAUDE_SETTINGS"
      SUMMARY[hooks]=1
    else
      if ! [ -f "$CLAUDE_SETTINGS" ]; then
        if [ "$DRY_RUN" -eq 0 ]; then
          mkdir -p "$(dirname "$CLAUDE_SETTINGS")"
          cp "$local_settings" "$CLAUDE_SETTINGS"
        fi
        ok "settings.json criado (nao havia existente)"
        SUMMARY[hooks]=1
      else
        # Existe — precisa merge. Tenta jq, depois python, depois fallback manual.
        if command -v jq >/dev/null 2>&1; then
          jq -s '.[0] * .[1]' "$CLAUDE_SETTINGS" "$local_settings" > "$CLAUDE_SETTINGS.tmp" && \
            mv "$CLAUDE_SETTINGS.tmp" "$CLAUDE_SETTINGS"
          ok "settings.json merged via jq (backup em $CLAUDE_SETTINGS.bak.$TIMESTAMP)"
          SUMMARY[hooks]=1
        elif command -v python3 >/dev/null 2>&1; then
          python3 - "$CLAUDE_SETTINGS" "$local_settings" <<'PY'
import json, sys
dst, src = sys.argv[1], sys.argv[2]
with open(dst) as f: a = json.load(f)
with open(src) as f: b = json.load(f)
def merge(x, y):
    if isinstance(x, dict) and isinstance(y, dict):
        out = dict(x)
        for k, v in y.items():
            out[k] = merge(x[k], v) if k in x else v
        return out
    return y
m = merge(a, b)
with open(dst, "w") as f: json.dump(m, f, indent=2)
PY
          ok "settings.json merged via python3 (backup em $CLAUDE_SETTINGS.bak.$TIMESTAMP)"
          SUMMARY[hooks]=1
        else
          warn "jq e python3 ausentes — nao posso fazer merge automatico de JSON"
          warn "merge manual necessario:"
          warn "  origem:  $local_settings"
          warn "  destino: $CLAUDE_SETTINGS"
          warn "  backup:  $CLAUDE_SETTINGS.bak.$TIMESTAMP"
        fi
      fi
    fi
  else
    warn "hooks: SKIP"
  fi
else
  info "hooks: SKIP (--minimal)"
fi

# ============================================================================
# 4. CLAUDE.md global
# ============================================================================

if [ "$MINIMAL" -eq 0 ]; then
  title "4. Pointer global em CLAUDE.md"

  if confirm "Adicionar bloco 'Second Brain' em $CLAUDE_MD_GLOBAL?" Y; then
    SB_BLOCK_MARKER_BEGIN="<!-- BEGIN second-brain-premium scaffold -->"
    SB_BLOCK_MARKER_END="<!-- END second-brain-premium scaffold -->"
    SB_BLOCK_CONTENT="$SB_BLOCK_MARKER_BEGIN
## Second Brain

Vault operacional em: \`$VAULT_ROOT\`

Contrato agentico durável: \`$VAULT_ROOT/AGENTS.md\`. Leia antes de operar.
Onboarding: \`$VAULT_ROOT/START-HERE.md\`.

Workflows disponiveis: ver tabela \"Mapa de Workflows\" em AGENTS.md.
Resposta final apos trabalho produtivo deve declarar:
\`vault: atualizado\` | \`vault: pendente\` | \`vault: nao aplicavel\`.
$SB_BLOCK_MARKER_END"

    if [ -f "$CLAUDE_MD_GLOBAL" ] && grep -qF "$SB_BLOCK_MARKER_BEGIN" "$CLAUDE_MD_GLOBAL"; then
      info "bloco Second Brain ja existe em $CLAUDE_MD_GLOBAL — atualizando"
      backup_file "$CLAUDE_MD_GLOBAL"
      if [ "$DRY_RUN" -eq 0 ]; then
        # Remove bloco antigo e adiciona novo
        python3 - "$CLAUDE_MD_GLOBAL" "$SB_BLOCK_MARKER_BEGIN" "$SB_BLOCK_MARKER_END" "$SB_BLOCK_CONTENT" <<'PY' 2>/dev/null || {
import sys, re
path, b, e, content = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4]
with open(path) as f: text = f.read()
pattern = re.compile(re.escape(b) + r".*?" + re.escape(e), re.DOTALL)
new_text = pattern.sub(content, text)
with open(path, "w") as f: f.write(new_text)
PY
          # python ausente: append no fim (poderia haver duplicacao mas o usuario tem o backup)
          warn "python3 ausente — adicionando bloco no fim (pode haver duplicata)"
          printf "\n%s\n" "$SB_BLOCK_CONTENT" >> "$CLAUDE_MD_GLOBAL"
        }
      else
        info "(dry-run) atualizaria bloco Second Brain em $CLAUDE_MD_GLOBAL"
      fi
    else
      backup_file "$CLAUDE_MD_GLOBAL"
      if [ "$DRY_RUN" -eq 0 ]; then
        mkdir -p "$(dirname "$CLAUDE_MD_GLOBAL")"
        printf "\n%s\n" "$SB_BLOCK_CONTENT" >> "$CLAUDE_MD_GLOBAL"
      else
        info "(dry-run) adicionaria bloco Second Brain em $CLAUDE_MD_GLOBAL"
      fi
    fi
    ok "CLAUDE.md global atualizado"
    SUMMARY[claude_md]=1
  else
    warn "CLAUDE.md global: SKIP"
  fi
else
  info "CLAUDE.md global: SKIP (--minimal)"
fi

# ============================================================================
# 5. Crons (instrucoes manuais — nao modifica crontab)
# ============================================================================

if [ "$MINIMAL" -eq 0 ]; then
  title "5. Crons opcionais"

  if confirm "Mostrar linhas para colar no crontab?" Y; then
    cat <<EOF

Cole as linhas abaixo no seu crontab editando com 'crontab -e':

${C_DIM}# second-brain-premium scaffold
0 7 * * *  cd "$VAULT_ROOT" && bash .claude/scripts/daily-heartbeat.sh >> .logs/daily-heartbeat.log 2>&1
0 9 * * 1  cd "$VAULT_ROOT" && bash .claude/scripts/weekly-vault-lint.sh >> .logs/weekly-vault-lint.log 2>&1
32 9 * * 1 cd "$VAULT_ROOT" && bash .claude/scripts/weekly-core-session.sh >> .logs/weekly-core-session.log 2>&1${C_RESET}

EOF
    info "(crontab nao foi modificado automaticamente — colar manual e seguro)"
    SUMMARY[crons]=1
  else
    warn "crons: SKIP"
  fi
fi

# ============================================================================
# 6. Stack semantico (instrucoes)
# ============================================================================

if [ "$MINIMAL" -eq 0 ] && command -v docker >/dev/null 2>&1; then
  title "6. Stack semantico opcional (Qdrant + Ollama)"

  if confirm "Mostrar comandos para subir o stack?" N; then
    cat <<EOF

Stack semantico habilita /ask, /search, /justify com recall semantico. Sem ele,
todos os comandos degradam para fallback grep. Tudo local, sem custo recorrente.

Subir o stack:
${C_DIM}docker compose -f "$VAULT_ROOT/_bootstrap/agentic/docker-compose.yml" up -d
docker exec sb-ollama ollama pull bge-m3
bash "$VAULT_ROOT/.claude/scripts/sb-reindex.sh"${C_RESET}

Trade-offs e detalhes: $VAULT_ROOT/_bootstrap/agentic/README.md

EOF
    SUMMARY[agentic_shown]=1
  else
    info "stack semantico: SKIP (instrucoes nao mostradas)"
  fi
elif [ "$MINIMAL" -eq 0 ]; then
  warn "docker nao encontrado — pulando stack semantico opcional"
fi

# ============================================================================
# Summary
# ============================================================================

title "Resumo"

log "Componente            Status"
log "-------------------  --------"
log "Commands Claude      $([ -n "${SUMMARY[commands]:-}" ] && echo "${SUMMARY[commands]} instalados" || echo "skip")"
log "Skills Codex         $([ -n "${SUMMARY[skills]:-}" ] && echo "${SUMMARY[skills]} instaladas" || echo "skip")"
log "Hooks settings.json  $([ -n "${SUMMARY[hooks]:-}" ] && echo "configurado" || echo "skip")"
log "CLAUDE.md global     $([ -n "${SUMMARY[claude_md]:-}" ] && echo "atualizado" || echo "skip")"
log "Crons (instrucoes)   $([ -n "${SUMMARY[crons]:-}" ] && echo "mostradas" || echo "skip")"
log "Stack semantico      $([ -n "${SUMMARY[agentic_shown]:-}" ] && echo "instrucoes mostradas" || echo "skip")"
log ""
[ "$DRY_RUN" -eq 1 ] && warn "MODO DRY-RUN — nenhuma alteracao foi efetivada" || true
log ""
log "Proximos passos:"
log "  1. Preencha sua identidade em $VAULT_ROOT/AGENTS.md (Secao 2)"
log "  2. Copie $VAULT_ROOT/_knowledge/projects/_template para seu primeiro projeto"
log "  3. No Claude Code, rode: /focus <seu-projeto>"
log "  4. Detalhes: $VAULT_ROOT/guia-personalizacao.md"
log ""
log "Para desinstalar: $SCRIPT_NAME --uninstall"
log ""
ok "concluido"
