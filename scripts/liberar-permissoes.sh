#!/usr/bin/env bash
# =============================================================================
# LIBERTAR PERMISSOES DE ESCRITA PARA O USUARIO DE OPERACAO (willian)
# =============================================================================
# CONTEXTO (2026-11-06)
#   O `data/` inteiro foi instalado como root:root. O crontab do `willian`
#   (uid 1000) roda as rodadas de aquisicao e o reenvio ao BookOrbit, mas
#   nao conseguia ESCREVER em:
#     - data/perfil/bibliotecario/logs/       (log da rodada)
#     - data/biblioteca/_incoming/            (ebooks baixados)
#     - data/biblioteca/<pasta>/              (.md extraido)
#     - data/biblioteca/global/kb-*.yaml      (catalogo nas KBs)
#     - data/perfil/bibliotecario/*.yaml      (catalogo + estado do pipeline)
#
#   Efeito medido: o cron DISPARAVA (journal mostra a sessao aberta) mas o
#   log parava em 23:30 de 05/11 — a saida morria no `>>` para um arquivo
#   root-only. A rodada das 21h15 NUNCA rodou uma vez sequer.
#
#   Pior: o `PermissionError` do `creds()` matava o pipeline na CAUSA (lido
#   do YAML de credenciais root-only) — ja corrigido no codigo.
#
# O QUE ESTE SCRIPT FAZ
#   1. `chown -R willian:willian` nos diretorios de TRABALHO (nao no repo
#      git inteiro, para nao mexer no historico de-owned).
#   2. `chmod 644` no YAML de credenciais (leitura) — o cache do usuario
#      continua sendo a fonte primária; o YAML vira backup legivel.
#   3. Deixa `data/.git` e `data/.gitignore` como root (git roda como root
#      no commit diario; ver nota abaixo).
#
# NOTA SOBRE O GIT
#   O repo `data/` tem remote `git@github.com:willianmendesf/data.git`.
#   A chave SSH de push esta em /root/.ssh (so o root tem). Por isso o
#   commit diario roda como root. Consequencia: arquivos tocados pelo root
#   ficam root-owned de novo. Este script NAO roda o commit — ele apenas
#   garante que o TRABALHO da rodada (logs, incoming, acervo) e' gravavel
#   pelo `willian`, que e' quem roda o download.
#
# USO: sudo bash scripts/liberar-permissoes.sh
# =============================================================================
set -uo pipefail

ROOT="$(cd "$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")/.." && pwd)"
USUARIO="${1:-willian}"
GRUPO="${2:-willian}"

echo "=== Liberando escrita para ${USUARIO}:${GRUPO} ==="

# --- 1. diretorios de trabalho da rodada ------------------------------------
for d in \
  "$ROOT/data/perfil/bibliotecario/logs" \
  "$ROOT/data/biblioteca/_incoming" \
  "$ROOT/data/biblioteca/global" \
  "$ROOT/data/perfil/bibliotecario"
do
  if [[ -d "$d" ]]; then
    chown -R "$USUARIO:$GRUPO" "$d" 2>/dev/null
    echo "  chown  $d"
  fi
done

# --- 2. subpastas do acervo (cada obra baixada entra numa delas) -----------
for d in "$ROOT"/data/biblioteca/*/; do
  [[ -d "$d" ]] || continue
  chown -R "$USUARIO:$GRUPO" "$d" 2>/dev/null
done
# BUG (2026-11-08): o glob `*/` so pegava SUBDIRETORIOS. Os arquivos soltos
# na raiz de data/biblioteca/ (ex.: `canones-referidos-listas-leitura.md`,
# `catalogo-compras.md`, `lista-aquisicao.md`) ficavam root:root — e o
# `catalogar-automatico.py` CRASHAVA com PermissionError ao ler um deles,
# derrubando a FASE 2 da rodada (os 3 orfaos nunca entravam nas KBs).
find "$ROOT/data/biblioteca" -maxdepth 1 -type f \
  ! -name '*.git*' -exec chown "$USUARIO:$GRUPO" {} + 2>/dev/null
echo "  chown  data/biblioteca/*/ + arquivos da raiz"

# --- 3. credenciais: legivel (leitura), nao gravavel ------------------------
CREDS="$ROOT/data/perfil/bibliotecario/zlib-credentials.yaml"
if [[ -f "$CREDS" ]]; then
  chown "$USUARIO:$GRUPO" "$CREDS" 2>/dev/null
  chmod 640 "$CREDS" 2>/dev/null
  echo "  chmod 640 $CREDS (agora legivel pelo operador)"
fi

# --- 4. notas/estudos: gravaveis (o pipeline pode gerar material) ----------
for d in "$ROOT/data/estudos" "$ROOT/data/historico"; do
  [[ -d "$d" ]] && chown -R "$USUARIO:$GRUPO" "$d" 2>/dev/null && echo "  chown  $d"
done

# --- 5. data/perfil INTEIRO (recursivo) -----------------------------------
# BUG (2026-11-06): o passo 1 so' cobria `data/perfil/bibliotecario`, mas
# `data/perfil/perfis.md` (lido pelo lint), `data/perfil/especialistas/*.yaml`
# (lidos pelos especialistas) e `data/perfil/memorias/` continuaram root-only.
# Resultado: o lint quebrava com PermissionError e o lint eh OBRIGATORIO
# antes de fechar qualquer turno que mexe em data/.
chown -R "$USUARIO:$GRUPO" "$ROOT/data/perfil" 2>/dev/null
echo "  chown  data/perfil/ (recursivo)"

# --- 6. indice de busca (SQLite) ------------------------------------------
# O `livros.db` tem 2,1 GB e precisa de WAL: o modo WAL grava arquivos
# -wal/-shm ao lado do banco. Se o diretorio for root-only, o PRAGMA
# journal_mode=WAL falha com "attempt to write a readonly database" e a
# BUSCA NOS LIVROS fica fora do ar.
if [[ -d "$ROOT/data/.indice" ]]; then
  chown -R "$USUARIO:$GRUPO" "$ROOT/data/.indice" 2>/dev/null
  rm -f "$ROOT/data/.indice"/livros.db-wal "$ROOT/data/.indice"/livros.db-shm 2>/dev/null
  echo "  chown  data/.indice/ (SQLite WAL)"
fi

# --- 7. lista-aquisicao.md (o indexador percorre data/biblioteca/) --------
if [[ -f "$ROOT/data/biblioteca/lista-aquisicao.md" ]]; then
  chown "$USUARIO:$GRUPO" "$ROOT/data/biblioteca/lista-aquisicao.md" 2>/dev/null
fi

echo ""
echo "=== VERIFICACAO (testa escrita real) ==="
# BUG (2026-11-08): o probe de "data/perfil/perfis.md" usava o arquivo REAL
# como alvo de `touch` + `rm -f`. Cada execucao do script APAGAVA o indice de
# especialistas — e o lint acusou "esp:bibliotecario:path:data/perfil/perfis.md
# (especialista cita arquivo inexistente)" na rodada de 2026-11-08.
# REGRA: NUNCA usar um arquivo real como alvo de probe. Todo alvo precisa ser
# um arquivo temporario descartavel (`.probe`), criado e removido no mesmo
# passo. Para testar um arquivo que JA existe, apenas verificamos se ele
# esta gravavel (`test -w`), sem tocar nele.
falhas=0
for d in \
  "$ROOT/data/perfil/bibliotecario/logs" \
  "$ROOT/data/biblioteca/_incoming" \
  "$ROOT/data/biblioteca/global" \
  "$ROOT/data/perfil/bibliotecario" \
  "$ROOT/data/perfil" \
  "$ROOT/data/.indice" \
  "$ROOT/data/biblioteca/literatura-mundial-classica"
do
  probe="$d/.probe"
  if sudo -u "$USUARIO" touch "$probe" 2>/dev/null; then
    rm -f "$probe"; echo "  OK      ${d#$ROOT/}/"
  else
    echo "  BLOQ.   ${d#$ROOT/}/"; falhas=$((falhas+1))
  fi
done

# Arquivos REAIS: apenas conferem se estao gravaveis — nunca sao tocados.
for f in \
  "$ROOT/data/perfil/perfis.md" \
  "$ROOT/data/biblioteca/lista-aquisicao.md"
do
  [[ -f "$f" ]] || continue
  if sudo -u "$USUARIO" test -w "$f" 2>/dev/null; then
    echo "  OK      ${f#$ROOT/} (gravavel)"
  else
    echo "  BLOQ.   ${f#$ROOT/} (nao gravavel)"; falhas=$((falhas+1))
  fi
done

echo ""
if [[ $falhas -eq 0 ]]; then
  echo "RESULTADO: tudo gravavel pelo operador."
else
  echo "RESULTADO: ${falhas} caminho(s) ainda bloqueado(s)."
fi
exit $falhas
