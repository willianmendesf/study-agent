#!/usr/bin/env bash
# =============================================================================
# REENVIO AUTOMATICO — ebooks de _incoming/ para o BookOrbit
# =============================================================================
# POR QUE EXISTE
#   Em 2026-11-05 a fila de 31 ebooks ficou parada em `data/biblioteca/_incoming/`
#   porque a conta `study-agent` (id=2) do BookOrbit esta como VIEWER e o
#   upload exige a permissao `library_upload` -> HTTP 403.
#   Essa permissao SO pode ser concedida por um admin no app BookOrbit.
#
# O QUE FAZ
#   1. Testa a permissao de upload (LOGIN + LEITURA — nao cria nada no Orbit).
#   2. Se ainda faltando permissao -> nao envia nada, registra o estado
#      "aguardando_permissao" e NAO repete a notificacao (evita ~96 msgs/dia).
#   3. Se a permissao foi concedida -> reenvia TODOS os ebooks da fila.
#   4. Cada arquivo so e apagado localmente DEPOIS do upload confirmado (HTTP
#      200/201). Se algo falhar, o arquivo local e PRESERVADO.
#   5. Notifica o Telegram SO quando o STATUS MUDA (scripts/orbit-notificar.py).
#
# USO
#   bash scripts/reenvio-orbit-automatico.sh          # tenta (idempotente)
#   bash scripts/reenvio-orbit-automatico.sh --dry    # so lista o que faria
#
# CRON (a cada 15 min)
#   */15 * * * * bash /home/willian/study-agent/scripts/reenvio-orbit-automatico.sh
#
# SAIDA
#   0 = tudo enviado (ou nada a enviar)
#   3 = falta a permissao `library_upload` (acao do William no app)
#   1 = falha outra
# =============================================================================
set -uo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SCRIPT="$ROOT/scripts/reenviar-incoming-orbit.py"
UPLOAD="$ROOT/scripts/orbit-upload.py"
NOTIFY="$ROOT/scripts/orbit-notificar.py"
LOG_DIR="$ROOT/data/perfil/bibliotecario/logs"
LOG="$LOG_DIR/reenvio-orbit-auto.log"

mkdir -p "$LOG_DIR"

log() { echo "[$(date -u '+%Y-%m-%d %H:%M:%S') UTC] $*" | tee -a "$LOG"; }

DRY=""
if [[ "${1:-}" == "--dry" ]]; then DRY="--dry"; fi

# --- 1. checa a permissao ------------------------------------------------
CHECK_OUT=$(python3 "$UPLOAD" --check 2>&1)
CHECK_RC=$?
echo "$CHECK_OUT" | tail -4 | tee -a "$LOG"

if [[ $CHECK_RC -eq 3 ]]; then
    log "FALTA a permissao 'library_upload'. Nada foi enviado. Fila intacta."
    # Status novo -> notifica UMA vez. Depois disso o script fica calado ate
    # o status mudar (o notificador compara com o estado gravado).
    python3 "$NOTIFY" --status "aguardando_permissao" \
      --mensagem "📚 Reenvio ao BookOrbit: a conta study-agent ainda está como Viewer. Os ebooks continuam guardados em _incoming/ e sobem sozinhos assim que você promover a conta para Editor no app (Minha Biblioteca → study-agent → Editor)." \
      >>"$LOG" 2>&1
    exit 3
fi

if [[ $CHECK_RC -ne 0 ]]; then
    log "Falha no teste de permissao (rc=$CHECK_RC). Nada foi enviado."
    python3 "$NOTIFY" --status "erro_verificacao" \
      --mensagem "⚠️ Reenvio ao BookOrbit: a verificação de permissão falhou (rc=$CHECK_RC). Os ebooks continuam em _incoming/." \
      >>"$LOG" 2>&1
    exit 1
fi

# --- 2. reenvia ----------------------------------------------------------
log "Permissao OK. Reenviando a fila de _incoming/ ..."
python3 "$SCRIPT" $DRY 2>&1 | tee -a "$LOG"
RC=${PIPESTATUS[0]}

RESTANTES=$(find "$ROOT/data/biblioteca/_incoming" -maxdepth 1 -type f \
    \( -name '*.epub' -o -name '*.mobi' -o -name '*.pdf' -o -name '*.azw3' \
       -o -name '*.azw' -o -name '*.prc' -o -name '*.fb2' \) 2>/dev/null | wc -l)
log "Fim. Restantes em _incoming/: $RESTANTES"

if [[ "$RESTANTES" -eq 0 ]]; then
    python3 "$NOTIFY" --status "concluido" \
      --mensagem "✅ Reenvio ao BookOrbit concluído: os ebooks de _incoming/ subiram para a sua biblioteca e os arquivos locais foram limpos." \
      >>"$LOG" 2>&1
else
    python3 "$NOTIFY" --status "parcial" \
      --mensagem "📚 Reenvio ao BookOrbit parcial: restam $RESTANTES ebook(s) em _incoming/ (rc=$RC). Os arquivos locais foram preservados." \
      >>"$LOG" 2>&1
fi

exit $RC
