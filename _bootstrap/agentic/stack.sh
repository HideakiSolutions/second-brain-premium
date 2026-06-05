#!/usr/bin/env bash
# stack.sh — gerencia a stack semantica (Qdrant + Ollama) em modo docker ou nativo.
#
# A escolha de modo e GPU vive em stack.env (gerado pelo install.sh, por maquina):
#   SB_STACK_MODE=docker|native
#   SB_STACK_GPU=on|off
#
# Uso:
#   bash stack.sh setup    # primeira vez: baixa binarios/imagens + modelo bge-m3
#   bash stack.sh start    # sobe Qdrant + Ollama conforme o modo
#   bash stack.sh stop     # para (docker: compose stop; nativo: so o que este script subiu)
#   bash stack.sh status   # saude de Qdrant, Ollama e modelo
#
# Modo docker:  requer Docker; GPU via override docker-compose.gpu.yml.
# Modo nativo:  Qdrant binario oficial (GitHub release) + Ollama instalado no SO.
#               GPU e detectada automaticamente pelo Ollama; off forca CPU.
# Os dois modos compartilham o storage em data/qdrant (mesma versao do Qdrant).

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE="$SCRIPT_DIR/stack.env"
NATIVE_DIR="$SCRIPT_DIR/native"
RUN_DIR="$NATIVE_DIR/run"
COMPOSE="$SCRIPT_DIR/docker-compose.yml"
COMPOSE_GPU="$SCRIPT_DIR/docker-compose.gpu.yml"

# Mesma versao da imagem em docker-compose.yml — mantem o formato de storage
# compativel ao alternar entre os modos.
QDRANT_VERSION="v1.12.4"
EMBED_MODEL="bge-m3"
QDRANT_URL="${SB_QDRANT_URL:-http://127.0.0.1:6333}"
OLLAMA_URL="${SB_OLLAMA_URL:-http://127.0.0.1:11434}"

# Cores ANSI (mesma convencao do install.sh)
if [ -t 1 ] && [ "${TERM:-dumb}" != "dumb" ]; then
  C_RESET=$'\033[0m'; C_DIM=$'\033[2m'
  C_RED=$'\033[31m'; C_GREEN=$'\033[32m'; C_YELLOW=$'\033[33m'; C_BLUE=$'\033[34m'
else
  C_RESET=""; C_DIM=""; C_RED=""; C_GREEN=""; C_YELLOW=""; C_BLUE=""
fi

log()  { printf "%s\n" "$*"; }
info() { printf "%s[info]%s %s\n" "$C_BLUE" "$C_RESET" "$*"; }
ok()   { printf "%s[ok]%s   %s\n" "$C_GREEN" "$C_RESET" "$*"; }
warn() { printf "%s[warn]%s %s\n" "$C_YELLOW" "$C_RESET" "$*"; }
err()  { printf "%s[err]%s  %s\n" "$C_RED" "$C_RESET" "$*" >&2; }

usage() { sed -n '2,17p' "${BASH_SOURCE[0]}" | sed 's/^# \?//'; exit "${1:-0}"; }

# ----------------------------------------------------------------------------
# Config
# ----------------------------------------------------------------------------

load_env() {
  SB_STACK_MODE="docker"
  SB_STACK_GPU="off"
  if [ -f "$ENV_FILE" ]; then
    local line
    while IFS= read -r line || [ -n "$line" ]; do
      line="${line%$'\r'}"   # tolera CRLF de edicao no Windows
      case "$line" in
        SB_STACK_MODE=*) SB_STACK_MODE="${line#SB_STACK_MODE=}" ;;
        SB_STACK_GPU=*)  SB_STACK_GPU="${line#SB_STACK_GPU=}" ;;
      esac
    done < "$ENV_FILE"
  fi
  case "$SB_STACK_MODE" in
    docker|native) ;;
    *) err "SB_STACK_MODE invalido em $ENV_FILE: '$SB_STACK_MODE' (use docker|native)"; exit 1 ;;
  esac
}

detect_platform() {
  case "$(uname -s)" in
    Linux*) echo "linux" ;;
    Darwin*) echo "macos" ;;
    MINGW*|MSYS*|CYGWIN*) echo "windows" ;;
    *) echo "unknown" ;;
  esac
}

detect_arch() {
  case "$(uname -m)" in
    x86_64|amd64) echo "x86_64" ;;
    arm64|aarch64) echo "aarch64" ;;
    *) echo "unknown" ;;
  esac
}

qdrant_asset() {  # $1=platform $2=arch
  case "$1:$2" in
    linux:x86_64)   echo "qdrant-x86_64-unknown-linux-gnu.tar.gz" ;;
    linux:aarch64)  echo "qdrant-aarch64-unknown-linux-musl.tar.gz" ;;
    macos:x86_64)   echo "qdrant-x86_64-apple-darwin.tar.gz" ;;
    macos:aarch64)  echo "qdrant-aarch64-apple-darwin.tar.gz" ;;
    windows:x86_64) echo "qdrant-x86_64-pc-windows-msvc.zip" ;;
    *) return 1 ;;
  esac
}

qdrant_bin() {
  if [ "$(detect_platform)" = "windows" ]; then
    echo "$NATIVE_DIR/qdrant.exe"
  else
    echo "$NATIVE_DIR/qdrant"
  fi
}

# Preenche COMPOSE_ARGS (array global) — evita mapfile, ausente no bash 3.2 do macOS
set_compose_args() {
  COMPOSE_ARGS=(-f "$COMPOSE")
  [ "$SB_STACK_GPU" = "on" ] && COMPOSE_ARGS+=(-f "$COMPOSE_GPU")
  return 0
}

# ----------------------------------------------------------------------------
# Healthchecks
# ----------------------------------------------------------------------------

qdrant_ready() { curl -fsS --max-time 3 "$QDRANT_URL/readyz" >/dev/null 2>&1; }
ollama_ready() { curl -fsS --max-time 3 "$OLLAMA_URL/api/version" >/dev/null 2>&1; }

model_present() {
  curl -fsS --max-time 5 "$OLLAMA_URL/api/tags" 2>/dev/null | grep -q "\"$EMBED_MODEL"
}

wait_ready() {  # $1=nome $2=funcao de check
  local i
  for i in $(seq 1 30); do
    if "$2"; then ok "$1 pronto"; return 0; fi
    sleep 1
  done
  err "$1 nao respondeu em 30s"
  return 1
}

# ----------------------------------------------------------------------------
# Processos nativos (pidfile em native/run/ — so paramos o que subimos)
# ----------------------------------------------------------------------------

start_bg() {  # $1=nome, restante=comando
  local name="$1"; shift
  mkdir -p "$RUN_DIR"
  local pidf="$RUN_DIR/$name.pid" logf="$RUN_DIR/$name.log"
  if [ -f "$pidf" ] && kill -0 "$(cat "$pidf")" 2>/dev/null; then
    info "$name ja em execucao (pid $(cat "$pidf"))"
    return 0
  fi
  nohup "$@" >"$logf" 2>&1 </dev/null &
  echo $! >"$pidf"
  info "$name iniciado (pid $(cat "$pidf"), log: $logf)"
}

stop_bg() {  # $1=nome
  local pidf="$RUN_DIR/$1.pid"
  if [ ! -f "$pidf" ]; then
    info "$1: sem pidfile — nada que este script tenha subido"
    return 0
  fi
  local pid; pid="$(cat "$pidf")"
  if kill -0 "$pid" 2>/dev/null; then
    kill "$pid" 2>/dev/null || true
    local i
    for i in $(seq 1 10); do
      kill -0 "$pid" 2>/dev/null || break
      sleep 1
    done
    kill -0 "$pid" 2>/dev/null && kill -9 "$pid" 2>/dev/null
    ok "$1 parado (pid $pid)"
  else
    info "$1: processo do pidfile ja nao existe"
  fi
  rm -f "$pidf"
}

# ----------------------------------------------------------------------------
# setup
# ----------------------------------------------------------------------------

setup_docker() {
  command -v docker >/dev/null 2>&1 || { err "docker nao encontrado"; exit 1; }
  set_compose_args
  info "baixando imagens e subindo containers..."
  docker compose "${COMPOSE_ARGS[@]}" up -d
  wait_ready "Ollama" ollama_ready
  info "baixando modelo $EMBED_MODEL (~1.2GB na primeira vez)..."
  docker exec sb-ollama ollama pull "$EMBED_MODEL" || pull_fallback_help
}

setup_native_qdrant() {
  local plat arch asset url
  plat="$(detect_platform)"; arch="$(detect_arch)"
  if [ -x "$(qdrant_bin)" ]; then
    info "qdrant ja presente em $(qdrant_bin) — skip download"
    return 0
  fi
  asset="$(qdrant_asset "$plat" "$arch")" || { err "plataforma sem binario qdrant: $plat/$arch"; exit 1; }
  url="https://github.com/qdrant/qdrant/releases/download/$QDRANT_VERSION/$asset"
  mkdir -p "$NATIVE_DIR"
  info "baixando qdrant $QDRANT_VERSION ($asset)..."
  curl -fL --retry 2 -o "$NATIVE_DIR/$asset" "$url"
  case "$asset" in
    *.tar.gz) tar -xzf "$NATIVE_DIR/$asset" -C "$NATIVE_DIR" ;;
    *.zip)    unzip -oq "$NATIVE_DIR/$asset" -d "$NATIVE_DIR" ;;
  esac
  rm -f "$NATIVE_DIR/$asset"
  chmod +x "$(qdrant_bin)" 2>/dev/null || true
  [ -x "$(qdrant_bin)" ] || { err "binario qdrant nao encontrado apos extracao"; exit 1; }
  ok "qdrant instalado em $(qdrant_bin)"
}

setup_native_ollama() {
  if ! command -v ollama >/dev/null 2>&1 && ! ollama_ready; then
    err "ollama nao encontrado. Instale nativamente e rode setup de novo:"
    log "  Windows: winget install Ollama.Ollama"
    log "  macOS:   brew install ollama"
    log "  Linux:   curl -fsSL https://ollama.com/install.sh | sh"
    exit 1
  fi
  ollama_ready || start_native_ollama
  wait_ready "Ollama" ollama_ready
  if model_present; then
    info "modelo $EMBED_MODEL ja presente — skip pull"
    return 0
  fi
  info "baixando modelo $EMBED_MODEL (~1.2GB na primeira vez)..."
  ollama pull "$EMBED_MODEL" || pull_fallback_help
}

pull_fallback_help() {
  warn "ollama pull falhou. Se o registry do Ollama estiver inacessivel na sua"
  warn "rede, baixe o GGUF FP16 do Hugging Face e crie o modelo manualmente:"
  log "  1. https://huggingface.co/gpustack/bge-m3-GGUF/resolve/main/bge-m3-FP16.gguf"
  log "  2. echo \"FROM ./bge-m3-FP16.gguf\" > Modelfile"
  log "  3. ollama create $EMBED_MODEL -f Modelfile"
  return 1
}

cmd_setup() {
  if [ "$SB_STACK_MODE" = "docker" ]; then
    setup_docker
  else
    setup_native_qdrant
    start_native_qdrant
    wait_ready "Qdrant" qdrant_ready
    setup_native_ollama
  fi
  ok "setup concluido. Proximo passo: bash .claude/scripts/sb-reindex.sh"
}

# ----------------------------------------------------------------------------
# start / stop
# ----------------------------------------------------------------------------

start_native_qdrant() {
  qdrant_ready && { info "Qdrant ja respondendo em $QDRANT_URL"; return 0; }
  [ -x "$(qdrant_bin)" ] || { err "binario qdrant ausente — rode: bash stack.sh setup"; exit 1; }
  mkdir -p "$SCRIPT_DIR/data/qdrant"
  QDRANT__STORAGE__STORAGE_PATH="$SCRIPT_DIR/data/qdrant" \
    start_bg qdrant "$(qdrant_bin)"
}

start_native_ollama() {
  ollama_ready && { info "Ollama ja respondendo em $OLLAMA_URL (servico do SO?)"; return 0; }
  command -v ollama >/dev/null 2>&1 || { err "ollama nao encontrado — rode: bash stack.sh setup"; exit 1; }
  if [ "$SB_STACK_GPU" = "off" ]; then
    # Forca CPU: oculta GPUs do runtime (NVIDIA e AMD)
    CUDA_VISIBLE_DEVICES="-1" HIP_VISIBLE_DEVICES="-1" start_bg ollama ollama serve
  else
    start_bg ollama ollama serve
  fi
}

cmd_start() {
  if [ "$SB_STACK_MODE" = "docker" ]; then
    command -v docker >/dev/null 2>&1 || { err "docker nao encontrado"; exit 1; }
    if [ "$SB_STACK_GPU" = "on" ] && ! command -v nvidia-smi >/dev/null 2>&1; then
      warn "SB_STACK_GPU=on mas nvidia-smi nao encontrado — o up pode falhar sem NVIDIA Container Toolkit"
    fi
    set_compose_args
    docker compose "${COMPOSE_ARGS[@]}" up -d
  else
    start_native_qdrant
    start_native_ollama
  fi
  wait_ready "Qdrant" qdrant_ready
  wait_ready "Ollama" ollama_ready
}

cmd_stop() {
  if [ "$SB_STACK_MODE" = "docker" ]; then
    set_compose_args
    docker compose "${COMPOSE_ARGS[@]}" stop
    ok "containers parados (dados preservados)"
  else
    stop_bg qdrant
    stop_bg ollama
    if ollama_ready; then
      info "Ollama segue respondendo — roda como servico do SO; pare pelo proprio servico se desejar"
    fi
  fi
}

# ----------------------------------------------------------------------------
# status
# ----------------------------------------------------------------------------

cmd_status() {
  log "modo: ${SB_STACK_MODE} ${C_DIM}(gpu: ${SB_STACK_GPU})${C_RESET}"
  if qdrant_ready; then ok "Qdrant online ($QDRANT_URL)"; else err "Qdrant OFFLINE ($QDRANT_URL)"; fi
  if ollama_ready; then ok "Ollama online ($OLLAMA_URL)"; else err "Ollama OFFLINE ($OLLAMA_URL)"; fi
  if ollama_ready; then
    if model_present; then ok "modelo $EMBED_MODEL presente"; else warn "modelo $EMBED_MODEL ausente — rode: bash stack.sh setup"; fi
  fi
  info "collection: bash .claude/scripts/sb-reindex.sh status"
}

# ----------------------------------------------------------------------------
# Dispatch
# ----------------------------------------------------------------------------

command -v curl >/dev/null 2>&1 || { err "curl e obrigatorio para este script"; exit 1; }
load_env
case "${1:-}" in
  setup)  cmd_setup ;;
  start)  cmd_start ;;
  stop)   cmd_stop ;;
  status) cmd_status ;;
  -h|--help) usage 0 ;;
  *) usage 1 ;;
esac
