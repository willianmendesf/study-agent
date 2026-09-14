#!/usr/bin/env bash
# inventario-biblioteca.sh — UserPromptSubmit. Injeta, COMPACTO, o inventário de
# data/biblioteca/ + especialistas + a obrigação da Regra 9. NUNCA injeta conteúdo
# de arquivo — só nome curto + tags (≈300 tokens/turno).
set -euo pipefail

ROOT="$(pwd)"
BIB="$ROOT/data/biblioteca"
PERFIL="$ROOT/data/perfil"
ctx=""

if [[ -d "$BIB" ]]; then
  ctx+="BIBLIOTECA (data/biblioteca/ — Regra 9: abra os arquivos do escopo, ancore, cite a fonte):\n"
  while IFS= read -r f; do
    name="$(basename "$f")"
    tags="$(grep -m1 -oE 'tags:\s*\[[^]]*\]' "$f" 2>/dev/null | sed 's/tags:\s*//' || true)"
    ctx+="  ${name} ${tags}\n"
  done < <(find "$BIB" -type f \( -name '*.md' -o -name '*.yaml' -o -name '*.txt' \) ! -name '*.disabled' 2>/dev/null | sort)
  ctx+="Escopo do turno: SEM especialista chamado -> qualquer arquivo. COM especialista (nome/apelido/'modo X'/tema)\n"
  ctx+="-> so os arquivos cujas tags cruzam com tags_do_dominio do .yaml dele; o resto fica fora. Se nada do\n"
  ctx+="escopo servir, diga 'nao ha material sobre isso na sua biblioteca' antes de usar conhecimento geral.\n"
else
  ctx+="data/biblioteca/ nao existe ainda — rode o setup (CLAUDE.md Regra 7).\n"
fi

if [[ -d "$PERFIL/especialistas" ]]; then
  esp="$(find "$PERFIL/especialistas" -maxdepth 1 -name '*.yaml' -printf '%f ' 2>/dev/null || true)"
  [[ -n "$esp" ]] && ctx+="Especialistas disponiveis (ativar so se o usuario chamar): ${esp}(ver 'quando_ativar' dentro)\n"
fi
[[ -f "$PERFIL/orquestrador-global-profile.yaml" ]] && ctx+="Perfil: data/perfil/orquestrador-global-profile.yaml (dominio, modos favoritos, lente de dominio).\n"

printf '{"hookSpecificOutput":{"hookEventName":"UserPromptSubmit","additionalContext":%s}}' \
  "$(printf '%b' "$ctx" | python3 -c 'import json,sys; print(json.dumps(sys.stdin.read()))')"
