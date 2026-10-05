#!/bin/bash
# Commita e sobe data/historico/ (so essa pasta) para o repositorio data. Chamado a cada 5 min pelo
# picoclaw-historico.service. Sem chave autorizada no GitHub, apenas commita localmente e tenta de novo no proximo ciclo.
WS="${WS:-/home/study-agent}"
cd "$WS/data" 2>/dev/null || exit 0
exec 9>/tmp/sync-historico.lock
flock -n 9 || exit 0

G=(git -c safe.directory='*' -c user.name="Study-Agent Bibliotecario" -c user.email="bibliotecario@study-agent.local")
export GIT_SSH_COMMAND="ssh -o BatchMode=yes -o StrictHostKeyChecking=accept-new -o ConnectTimeout=10"

# 1) se a deploy key ja foi autorizada, troca o remoto de https para ssh (uma vez)
url=$("${G[@]}" remote get-url origin 2>/dev/null)
if [[ "$url" == https://github.com/* ]] && ssh -o BatchMode=yes -o StrictHostKeyChecking=accept-new -T github-data 2>&1 | grep -q "successfully authenticated"; then
  repo=${url#https://github.com/}
  "${G[@]}" remote set-url origin "git@github-data:${repo}"
fi

# 2) commit restrito a historico/
"${G[@]}" add -A -- historico
if ! "${G[@]}" diff --cached --quiet -- historico; then
  "${G[@]}" commit -q -m "data: historico picoclaw $(date -u +%Y-%m-%dT%H:%M:%SZ)" -- historico
fi

# 3) push (so se houver commit a subir e o remoto for ssh)
if [[ "$("${G[@]}" remote get-url origin)" == git@* ]]; then
  if [ -n "$("${G[@]}" log origin/master..HEAD --oneline 2>/dev/null)" ]; then
    "${G[@]}" push -q origin HEAD 2>&1 | tail -2
  fi
fi
exit 0
