#!/usr/bin/env bash
# =============================================================================
# RODADA DE FICCAO — wrapper com notificacao (roda pelo crontab do sistema)
# =============================================================================
# POR QUE ESTE WRAPPER (2026-11-05)
#   A `rodada-ficcao.sh` roda o pipeline e loga, mas nao avisa o William.
#   O `cron` do picoclaw nao serve: ele agenda TURNO DE LLM (custo de tokens
#   + mensagem a cada execucao). Aqui o crontab do SISTEMA executa o script
#   direto (zero tokens) e a notificacao sai por curl para o Telegram do
#   William — SO quando o resultado muda (nada de spam diario).
#
# CRON
#   15 0 * * *  (00:15 UTC = 21:15 BRT — depois do reset da cota do z-library)
#
# SAIDA
#   0 = rodada OK (com ou sem downloads)
#   1 = erro
# =============================================================================
set -uo pipefail

ROOT="$(cd "$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")/.." && pwd)"
LOG_DIR="$ROOT/data/perfil/bibliotecario/logs"
LOG="$LOG_DIR/rodada-ficcao-cron.log"
MAX="${1:-12}"

mkdir -p "$LOG_DIR"

log() { echo "[$(date -u '+%Y-%m-%d %H:%M:%S') UTC] $*" | tee -a "$LOG"; }

log "=== RODADA DE FICCAO (max=$MAX) ==="

OUT=$(bash "$ROOT/data/perfil/bibliotecario/rodada-ficcao.sh" --max "$MAX" 2>&1)
RC=$?
printf '%s\n' "$OUT" >>"$LOG"

# resumo do pipeline
ADQ=$(printf '%s\n' "$OUT" | grep -oE "[0-9]+ adquirido\(s\)" | grep -oE "^[0-9]+" | tail -1)
FAL=$(printf '%s\n' "$OUT" | grep -oE "[0-9]+ falha\(s\)" | grep -oE "^[0-9]+" | tail -1)
ADQ=${ADQ:-0}
FAL=${FAL:-0}

log "resultado: $ADQ adquirido(s) nesta rodada | $FAL falha(s) | rc=$RC"

# notificacao (SO quando o total de hoje muda)
python3 "$ROOT/scripts/rodada-ficcao-notificar.py" --falhas "$FAL" >>"$LOG" 2>&1
NR=$?

log "fim (notificador rc=$NR)"
exit $RC
