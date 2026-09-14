---
name: study-token-economy
description: "Economia de tokens via rtk (github.com/rtk-ai/rtk) — automática, via hook PreToolUse que reescreve todo comando Bash quando rtk está instalado na máquina do usuário (60-90% menos tokens). Nunca exigido: sem rtk instalado, o hook não faz nada e tudo roda normal. Esta skill documenta o mecanismo e a config versionada (.rtk/filters.toml)."
---

# Economia de tokens (rtk)

**Tipo:** infraestrutura transversal (não é uma skill que o usuário "chama" — é uma prática que a IA
segue em qualquer ação que rode Bash dentro do study-agent) · **Prioridade:** alta

`rtk` ([github.com/rtk-ai/rtk](https://github.com/rtk-ai/rtk)) é um proxy de CLI que filtra/compacta a
saída de comandos comuns (git, grep, find, testes, build, etc.) antes dela entrar no contexto —
tipicamente **60-90% menos tokens**, sem perder a informação que importa.

## Como funciona (automático — não depende de a IA lembrar)

Um hook `PreToolUse` em `.claude/settings.json` (matcher `Bash`) roda `rtk hook claude` antes de
**todo** comando Bash. Se `rtk` estiver instalado, ele **reescreve o comando sozinho** — inclusive
cadeias com `&&` (`git add . && git commit ...` vira `rtk git add . && rtk git commit ...`
automaticamente). A IA não precisa prefixar nada manualmente nem checar se `rtk` existe antes de cada
comando — é transparente. Testado (pipe direto pro hook): com `rtk` presente, reescreve; ausente, o
hook não faz nada (`command -v rtk ... || true`) e o comando roda normal, sem erro.

`rtk` **nunca** é uma dependência do study-agent — é uma ferramenta pessoal opcional do ambiente. O
template nunca instala, nunca assume presença, nunca falha se ausente. Quem não tem `rtk` instalado
não percebe diferença nenhuma.

## Config versionada

- `.rtk/filters.toml` (raiz do study-agent) — filtros locais do projeto, lidos pelo `rtk` quando ele
  roda com cwd nessa raiz. Vem vazio (`schema_version = 1`); adicione blocos `[filters.*]` conforme
  precisar (ver `github.com/rtk-ai/rtk#custom-filters`). **Precisa estar na raiz** — `rtk` não lê esse
  arquivo de dentro de `.claude/skills/`, então não duplique aqui; esta skill só documenta/mantém ele.
- **Trust de projeto:** por padrão o `rtk` trata `.rtk/filters.toml` de um projeto clonado como
  "untrusted" e não aplica os filtros dele até o usuário rodar `rtk trust` (revisão de segurança do
  próprio rtk — não é algo que a IA decide ou executa por conta própria). Enquanto não confiado, o rtk
  ainda reescreve comandos normalmente com os filtros embutidos/globais — só os filtros **locais deste
  projeto** ficam pendentes de aprovação.

## Onde mais compensa dentro do study-agent

| Situação | Comando |
|---|---|
| Ver mudanças/commits em `data/` (Regra 7) | `rtk git status` / `rtk git log` / `rtk git diff` |
| Logs de `book-pipeline` (`server.py`, downloads) | `rtk read <log>` ou `rtk log <arquivo>` |
| Listar `data/biblioteca/` ou `data/estudos/` quando ficarem grandes | `rtk find` / `rtk ls` |
| Buscar padrão em muitos arquivos (`study-gerenciar-bibliotecas`, `study-rag-local`) | `rtk grep <padrão>` |
| Rodar teste/build de uma skill com dependência externa (ex.: `study-h5p` servindo local) | `rtk err <cmd>` (só erros) |

## Referência rápida de comandos (quando `rtk` existe)

```bash
rtk git status / log / diff / show / add / commit / push / pull   # 59-80%
rtk grep <padrão>        # busca agrupada por arquivo — 75%
rtk find <padrão>        # busca de arquivo agrupada por pasta — 70%
rtk read <arquivo>       # leitura filtrada — 60%
rtk ls <pasta>           # árvore compacta — 65%
rtk err <cmd>            # só erros/warnings de qualquer comando
rtk log <arquivo>        # log deduplicado com contagem
rtk json <arquivo>       # estrutura do JSON sem os valores
rtk diff                 # diff ultra-compacto
rtk curl <url> / wget    # resposta HTTP compacta — 65-70%
rtk gain                 # estatística real de economia acumulada
```

Mesmo em cadeias com `&&`, prefixar cada comando: `rtk git add . && rtk git commit -m "..." && rtk git push`.

## O que esta skill NUNCA faz
- Instalar, baixar, ou exigir o binário `rtk` — instalação é decisão e responsabilidade do usuário
  (`github.com/rtk-ai/rtk`), fora do escopo do template.
- Comentar com o usuário quando `rtk` está ausente — o hook degrada em silêncio, o comportamento sem
  ele é idêntico ao de qualquer outro projeto sem essa otimização.
- Duplicar `.rtk/filters.toml` em outro lugar — a raiz é a única cópia válida.
- Depender da IA lembrar de prefixar comandos — o hook `PreToolUse` (`.claude/settings.json`) já faz
  isso sozinho; a tabela de comandos acima é só referência pra quando algo for escrito manualmente
  (ex.: documentação, exemplo pro usuário).
