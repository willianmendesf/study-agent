#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────
# rodar-aula-portugues.sh — dispara a aula diária de Português (Portuga).
#
# POR QUE EXISTE (2026-11-17):
#   O job do picoclaw (agent_turn) rodava um TURNO DE LLM só pra executar
#   este script. Como o agente no fim do turno chamava apenas `send_file()`
#   e respondia "Requested output delivered via tool attachment", a CAPA
#   textual nunca era enviada — William recebia "só os áudios jogados"
#   (confirmado nas sessões cron de 2026-11-13, 14, 15 e 16).
#   Agora: script entrega capa+áudio ele mesmo, e o disparo vem do CRONTAB
#   do sistema (zero tokens, zero turno de LLM). Mesma decisão tomada para
#   o reenvio do BookOrbit em 2026-11-05.
#
# Instalado em: crontab -e →  0 22 * * * .../rodar-aula-portugues.sh
#   22:00 UTC = 19:00 BRT
# ─────────────────────────────────────────────────────────────────────────
set -uo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LOG_DIR="$ROOT/data/perfil/portuga/logs"
LOG="$LOG_DIR/aula-$(date +%Y%m%d).log"
mkdir -p "$LOG_DIR"

{
  echo "════════════════════════════════════════════════════════"
  echo "início: $(date -Is)"
  echo "════════════════════════════════════════════════════════"
  bash "$ROOT/data/estudos/notas/portugues-aulas-diarias/enviar-aula.sh"
  rc=$?
  echo "────────────────────────────────────────────────────────"
  echo "fim: $(date -Is) | exit=$rc"
  exit $rc
} >> "$LOG" 2>&1
