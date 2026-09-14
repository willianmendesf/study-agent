#!/usr/bin/env bash
# auto-pull-framework.sh — UserPromptSubmit. A cada ~3 dias, tenta um `git pull --ff-only`
# do framework (master) em background, sem avisar o usuário e sem bloquear o turno.
#
# Nunca toca data/ — é um repositório git próprio do usuário, fora do controle deste git
# (Regra 7). Falha (rede off, mudança local, histórico divergente) é sempre silenciosa:
# não bloqueia o turno, não força nada (sem --force/reset --hard), só tenta de novo daqui
# a 3 dias. O marcador de "última tentativa" fica em data/ (Regra 3 — estado do usuário).
set -euo pipefail
ROOT="$(pwd)"
MARKER="$ROOT/data/.study-agent-last-pull"
LOG="$ROOT/data/.study-agent-pull.log"
INTERVALO=259200  # 3 dias em segundos

agora=$(date +%s)
ultimo=0
if [[ -f "$MARKER" ]]; then
  ultimo="$(cat "$MARKER" 2>/dev/null || echo 0)"
  [[ "$ultimo" =~ ^[0-9]+$ ]] || ultimo=0
fi

if (( agora - ultimo >= INTERVALO )); then
  mkdir -p "$ROOT/data" 2>/dev/null || exit 0
  echo "$agora" > "$MARKER" 2>/dev/null || true
  (
    cd "$ROOT" || exit 0
    {
      echo "--- $(date -u +%Y-%m-%dT%H:%M:%SZ) auto-pull ---"
      git pull --ff-only origin master 2>&1
    } >> "$LOG" 2>&1
  ) &
  disown
fi

# Nunca imprime nada no stdout — roda 100% em segundo plano, sem injetar contexto
# nem interromper o turno.
exit 0
