#!/usr/bin/env bash
# inventario-biblioteca.sh — roda no UserPromptSubmit. Injeta no contexto do turno
# o inventário de data/biblioteca/ + data/perfil/ e a obrigação da Regra 9.
# Objetivo: a IA NUNCA responder conteúdo de estudo sem antes abrir o material curado.
#
# Recebe o JSON do hook no stdin (não usa). Escreve JSON no stdout com additionalContext.

set -euo pipefail

ROOT="$(pwd)"
BIB="$ROOT/data/biblioteca"
PERFIL="$ROOT/data/perfil"

ctx=""

if [[ -d "$BIB" ]]; then
  ctx+="=== BIBLIOTECA DO USUÁRIO (data/biblioteca/) — Regra 9: ancore a resposta nela e CITE a fonte ===\n"
  while IFS= read -r f; do
    rel="${f#"$ROOT"/}"
    tagline="$(grep -m1 -E '^\s*tags\s*:' "$f" 2>/dev/null | sed 's/^\s*//' || true)"
    ctx+="- ${rel}"
    [[ -n "$tagline" ]] && ctx+="   (${tagline})"
    ctx+="\n"
  done < <(find "$BIB" -type f \( -name '*.md' -o -name '*.yaml' -o -name '*.txt' \) ! -name '*.disabled' 2>/dev/null | sort)
  ctx+="\nANTES de responder qualquer coisa de conteúdo de estudo: abra (Read/Grep) os arquivos acima que"
  ctx+=" tocam o assunto. Se um especialista está ativo, filtre pelas tags dele. Se NADA na lista for"
  ctx+=" relevante, diga isso explicitamente ('nao ha material sobre X na sua biblioteca') antes de usar"
  ctx+=" conhecimento geral. Nunca responda de cabeca fingindo que veio do acervo.\n"
else
  ctx+="=== data/biblioteca/ ainda nao existe — rode o setup (CLAUDE.md Regra 7) para criar o repositorio pessoal ===\n"
fi

if [[ -d "$PERFIL" ]]; then
  ctx+="\n=== PERFIL / ESPECIALISTAS (data/perfil/) ===\n"
  [[ -f "$PERFIL/orquestrador-global-profile.yaml" ]] && ctx+="- perfil global: data/perfil/orquestrador-global-profile.yaml (leia p/ dominio, modos favoritos, lente de dominio)\n"
  for lente in "$PERFIL"/orquestrador-*.yaml; do
    [[ -e "$lente" ]] || continue
    [[ "$lente" == *"global-profile"* ]] && continue
    ctx+="- lente de dominio: ${lente#"$ROOT"/}\n"
  done
  if [[ -d "$PERFIL/especialistas" ]]; then
    for e in "$PERFIL/especialistas"/*.yaml; do
      [[ -e "$e" ]] || continue
      ctx+="- especialista: ${e#"$ROOT"/} — ativar so se o usuario chamar (ver 'quando_ativar' dentro)\n"
    done
  fi
fi

printf '{"hookSpecificOutput":{"hookEventName":"UserPromptSubmit","additionalContext":%s}}' \
  "$(printf '%b' "$ctx" | python3 -c 'import json,sys; print(json.dumps(sys.stdin.read()))')"
