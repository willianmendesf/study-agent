#!/usr/bin/env bash
# =============================================================================
# ROTINA DIARIA DE AQUISICAO DO BIBLIOTECARIO (unificada)
# =============================================================================
# O QUE FAZ (rodando todo dia, sem intervencao do William):
#
#   FASE 1  LEVANTAMENTO — o Bibliotecario mede os gaps (por area de
#           necessidade teologica + por obra da rampa de leitura) e escreve
#           o plano do dia. Nao gasta cota.
#   FASE 2  AQUISICAO DE FICCAO — baixa do z-library as obras do catalogo
#           (data-driven), ja existentas ou nao na estante fisica do William.
#           Usa TODAS as 8 contas (cota de 80/dia).
#   FASE 3  REINDEXE + CATALOGO — cataloga o material novo nas KBs, reindexa
#           a base de busca e roda o lint.
#   FASE 4  REENVIO AO BOOKORBIT — manda os ebooks para o app de leitura.
#   FASE 5  NOTIFICACAO — avisa no Telegram SO quando algo novo entrou
#           (nada de spam diario).
#
# POR QUE ESTE WRAPPER (2026-11-06)
#   A `rodada-ficcao.sh` (raiz do data/) so' rodava a FASE 2. As outras
#   fases (levantamento de gap teologico, reindexe, lint, reenvio) ficavam
#   em scripts separados, disparados por jobs diferentes — e NENHUM deles
#   funcionava, porque o `data/` era root:root e o crontab roda como
#   `willian`. O cron disparava, o `>>` no log morria, e a rodada nunca
#   acontecia. Este wrapper roda TUDO em sequencia, num unico processo,
#   e cada fase falha sem derrubar as demais.
#
# CRON
#   15 0 * * *  (00:15 UTC = 21:15 BRT — 15 min apos o reset da cota do
#                z-library, que e' a meia-noite UTC)
#
# LOG
#   data/perfil/bibliotecario/logs/rodada-bibliotecario-YYYY-MM-DD.log
# =============================================================================
set -uo pipefail

ROOT="$(cd "$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")/.." && pwd)"
LOG_DIR="$ROOT/data/perfil/bibliotecario/logs"
LOG="$LOG_DIR/rodada-bibliotecario-$(date +%Y-%m-%d).log"
MAX_FICCAO="${1:-12}"
MAX_GAP="${2:-2}"

mkdir -p "$LOG_DIR"

log() { echo "[$(date -u '+%Y-%m-%d %H:%M:%S') UTC] $*" | tee -a "$LOG"; }

log "=== RODADA DO BIBLIOTECARIO (max_ficcao=$MAX_FICCAO max_gap=$MAX_GAP) ==="

# --- FASE 1: levantamento de gaps (nao gasta cota) --------------------------
log "--- FASE 1: levantamento de gaps ---"
if [[ -f "$ROOT/data/perfil/bibliotecario/biblioteca-orbit/gap-analysis.py" ]]; then
  python3 "$ROOT/data/perfil/bibliotecario/biblioteca-orbit/gap-analysis.py" 2>&1 \
    | tail -25 | tee -a "$LOG"
else
  log "gap-analysis.py ausente — fase pulada"
fi

# --- FASE 2: aquisicao de ficcao (z-library, 8 contas) ----------------------
log "--- FASE 2: aquisicao de ficcao ---"
FICCAO_OUT="$LOG_DIR/.rodada-ficcao.$$.out"
if [[ -f "$ROOT/data/perfil/bibliotecario/rodada-ficcao.sh" ]]; then
  bash "$ROOT/data/perfil/bibliotecario/rodada-ficcao.sh" --max "$MAX_FICCAO" \
    >"$FICCAO_OUT" 2>&1
  FICCAO_RC=$?
  tail -40 "$FICCAO_OUT" | tee -a "$LOG"
else
  log "rodada-ficcao.sh ausente — fase pulada"
  FICCAO_RC=1
  : >"$FICCAO_OUT"
fi
ADQ=$(grep -oE "[0-9]+ adquirido\(s\)" "$FICCAO_OUT" | grep -oE "^[0-9]+" | tail -1)
FAL=$(grep -oE "[0-9]+ falha\(s\)" "$FICCAO_OUT" | grep -oE "^[0-9]+" | tail -1)
ADQ=${ADQ:-0}; FAL=${FAL:-0}
rm -f "$FICCAO_OUT"

# --- FASE 2b: aquisicao TEOLOGICA dirigida por gap (rodada-diaria.sh) -------
# POR QUE ESTA FASE EXISTE (2026-11-07): o `rodada-diaria.sh` (fases 0/1/2
# — gaps TEOLOGICOS) NAO estava em nenhum cron. So a `rodada-ficcao.sh`
# rodava. Resultado: desde 2026-11-05 (commit 999a0a1) a aquisicao por gap
# TEOLOGICO estava MORTA por um NameError (`ACCOUNTS` nao existia mais) e
# ninguem percebeu — o crash aparecia no log, mas a rodada "terminava" e
# seguia. Aqui a fase roda MESMO, e o wrapper DETECTA o crash.
log "--- FASE 2b: aquisicao por gap teologico (rodada-diaria.sh) ---"
GAP_OUT="$LOG_DIR/.rodada-gap.$$.out"
if [[ -f "$ROOT/data/perfil/bibliotecario/rodada-diaria.sh" ]]; then
  bash "$ROOT/data/perfil/bibliotecario/rodada-diaria.sh" --max "$MAX_GAP" \
    >"$GAP_OUT" 2>&1
  GAP_RC=$?
  tail -40 "$GAP_OUT" | tee -a "$LOG"
  # --- ALERTA DE CRASH (a FASE 1 do rodape morria com traceback) ---
  if grep -qE "^Traceback|NameError|KeyError|ModuleNotFoundError" "$GAP_OUT"; then
    log "!!! FASE 2b CRASHOU (rc=$GAP_RC) — aquisicao por gap teologico NAO rodou"
    grep -E "NameError|KeyError|ModuleNotFoundError|^Traceback" "$GAP_OUT" \
      | head -5 | tee -a "$LOG"
    GAP_RC=99
  else
    GAP_ADQ=$(grep -oE "TOTAL adquirido: [0-9]+" "$GAP_OUT" | grep -oE "[0-9]+" | tail -1)
    log "FASE 2b ok: ${GAP_ADQ:-0} material(is) por gap teologico"
  fi
else
  log "rodada-diaria.sh ausente — fase pulada"
  GAP_RC=1
fi
rm -f "$GAP_OUT"

# --- FASE 3: catalogo + reindexe + lint -------------------------------------
log "--- FASE 3: catalogo + reindexe + lint ---"
for s in "catalogar-automatico.py" "reconstruir-kbs.py"; do
  p="$ROOT/data/perfil/bibliotecario/biblioteca-orbit/$s"
  [[ -f "$p" ]] && { python3 "$p" 2>&1 | tail -6 | tee -a "$LOG"; }
done
if [[ -f "$ROOT/.claude/skills/study-busca-livros/indexar.py" ]]; then
  python3 "$ROOT/.claude/skills/study-busca-livros/indexar.py" 2>&1 \
    | tail -4 | tee -a "$LOG"
fi
python3 "$ROOT/.claude/scripts/study-lint.py" 2>&1 | tail -4 | tee -a "$LOG"

# --- FASE 4: reenvio ao BookOrbit ------------------------------------------
log "--- FASE 4: reenvio ao BookOrbit ---"
if [[ -x "$ROOT/scripts/reenvio-orbit-automatico.sh" ]]; then
  "$ROOT/scripts/reenvio-orbit-automatico.sh" 2>&1 | tail -8 | tee -a "$LOG"
else
  log "reenvio-orbit-automatico.sh ausente — fase pulada"
fi

# --- FASE 5: notificacao (so quando o total muda) ---------------------------
log "--- FASE 5: notificacao ---"
python3 "$ROOT/scripts/rodada-ficcao-notificar.py" --falhas "$FAL" 2>&1 \
  | tail -6 | tee -a "$LOG"
NOTIF_RC=$?

log "=== FIM: $ADQ adquirido(s) ficcao | $FAL falha(s) | gap_rc=$GAP_RC | ficcao_rc=$FICCAO_RC | notif_rc=$NOTIF_RC ==="
exit 0
