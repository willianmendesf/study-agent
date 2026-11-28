#!/usr/bin/env bash
# =============================================================================
# SUBIR EDERSHEIM AO BOOKORBIT — fila propria, fora de _incoming/
# =============================================================================
# POR QUE EXISTE
#   Os 17 arquivos do Edersheim (12 ES + 6 EN, com o Templo ES ja existente)
#   foram preparados em 2026-11-28 03:50 BRT com o metadado reescrito
#   ("Alfred Edersheim - <Titulo>.ext"). O BookOrbit estava dormindo
#   (liga 05:00, desliga 23:00 BRT) e o Memos idem.
#
#   NAO usar data/biblioteca/_incoming/: o cron reenvio-orbit-automatico.sh
#   (15 min) apaga o arquivo depois do upload e pode "roubar" o original
#   antes da conversao. Fila propria em ~/ebooks-gerados/edersheim-pendente/.
#
# O QUE FAZ
#   1. Testa a saude do BookOrbit (GET /api/v1/health).
#   2. Se offline -> sai em 0 sem tocar em nada (tenta de novo no proximo ciclo).
#   3. Se online -> orbit-upload-lote.py --dir <fila> (1 login para a fila,
#      backoff em 429/401, nome do arquivo = "Autor - Titulo").
#   4. Cada arquivo so e apagado da fila DEPOIS do upload confirmado.
#   5. Notifica o Telegram SO quando a fila zera (orbit-notificar.py).
#
# CRON (a cada 15 min, 05:00-23:00 BRT = 08:00-02:00 UTC)
#   */15 8-23,0-2 * * * bash scripts/subir-edersheim.sh
#
# SAIDA
#   0 = enviado tudo (ou nada a enviar / Orbit dormindo)
#   1 = falha real
# =============================================================================
set -uo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
FILA="${EDERSHEIM_FILA:-$HOME/ebooks-gerados/edersheim-pendente}"
LOG_DIR="$ROOT/data/perfil/bibliotecario/logs"
LOG="$LOG_DIR/subir-edersheim.log"
ORBIT_URL="${ORBIT_URL:-http://192.168.15.26}"

mkdir -p "$LOG_DIR" "$FILA"

log() { echo "[$(date -u '+%Y-%m-%d %H:%M:%S') UTC] $*" >>"$LOG"; }

PEND=$(find "$FILA" -maxdepth 1 -type f \
    \( -name '*.epub' -o -name '*.pdf' -o -name '*.mobi' -o -name '*.azw3' \) 2>/dev/null | wc -l)
if [[ "$PEND" -eq 0 ]]; then
    exit 0
fi

# 1. Orbit acordado?
CODE=$(curl -s -m 10 -o /dev/null -w "%{http_code}" "$ORBIT_URL/api/v1/health" 2>/dev/null)
if [[ "$CODE" != "200" ]]; then
    log "Orbit indisponivel (health=$CODE). $PEND arquivo(s) na fila; nada enviado."
    exit 0
fi

# 2. envia a fila
log "Orbit OK. Enviando $PEND arquivo(s) da fila do Edersheim ..."
OUT=$(python3 "$ROOT/scripts/orbit-upload-lote.py" --dir "$FILA" 2>&1)
RC=$?
echo "$OUT" | tail -30 >>"$LOG"

REST=$(find "$FILA" -maxdepth 1 -type f \
    \( -name '*.epub' -o -name '*.pdf' -o -name '*.mobi' -o -name '*.azw3' \) 2>/dev/null | wc -l)
log "Fim: restantes=$REST rc=$RC"

if [[ "$REST" -eq 0 ]]; then
    python3 "$ROOT/scripts/orbit-notificar.py" --status "edersheim_concluido" \
      --mensagem "✅ Alfred Edersheim no BookOrbit: os 17 arquivos (12 em espanhol + 6 em inglês) subiram para a sua biblioteca." \
      >>"$LOG" 2>&1
fi

exit $RC
