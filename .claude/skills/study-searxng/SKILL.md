---
name: study-searxng
description: "Busca web agregada via SearXNG local (tools-searxng em 192.168.15.41:82). Substitui/complementa a web_search nativa do picoclaw quando você quer múltiplos engines (Google+Bing+DDG+Brave juntos) com privacidade (sem API key, sem rate limit de provedor) e filtragem por idioma/janela temporal. Use quando a busca nativa do agente falhar, quando quiser perspectiva agregada, ou quando quiser ler conteúdo de uma URL no chat."
---

# study-searxng — Busca web agregada via SearXNG local

**Tipo:** skill utilitária (invocada manualmente no shell ou por outras skills).
**Escopo:** Study-Agent — provê busca web ao IAM e a qualquer sub-skill que precise de conteúdo externo.
**Endpoint:** `http://192.168.15.41:82/search?format=json&q=...` (LXC tools-searxng no Tailnet).
**Dependências:** apenas stdlib Python 3.10+ (`urllib`, `json`, `argparse`).
**Quando usar:** web_search nativa falhou / quer múltiplos engines agregados / quer privacidade (sem API key, sem rastreamento) / precisa de filtro temporal (d/w/m/y) ou por idioma.

## Por que esta skill existe

O picoclaw já vem com `web_search` (uma engine) e `web_fetch` (extrai conteúdo de uma URL). Esta skill
cobre o **meio-termo**: quando você quer **encontrar** uma página sobre um tema (não já ter a URL), com
a vantagem de o SearXNG agregar vários engines de uma vez (Google, Bing, DuckDuckGo, Brave, Startpage...)
e expor filtros (idioma, janela temporal, engines específicos, safesearch) que a web_search nativa não tem.

Como o SearXNG é **local na sua rede** (não usa API key de provedor externo), não há rate limit
comercial e a privacidade é preservada — útil pra buscas exploratórias durante estudo.

## Como invocar

```bash
# Texto (humano, 10 res)
python3 .claude/skills/study-searxng/bin/searxng-search.py "calvinismo e razão"

# JSON puro (pra piping/script)
python3 .claude/skills/study-searxng/bin/searxng-search.py "João Calvino vida" -k 5 --json

# Filtros
python3 .claude/skills/study-searxng/bin/searxng-search.py "hermenêutica reformada" --lang pt-BR
python3 .claude/skills/study-searxng/bin/searxng-search.py "novidades IA teologia" --time w
python3 .claude/skills/study-searxng/bin/searxxng-search.py "..." --engines "google,bing"
python3 .claude/skills/study-searxng/bin/searxng-search.py "..." --safe 0
```

## API Python (pra outras skills / sub-agents)

```python
from searxng_search import search_json
data = search_json("reformed epistemology", limit=5, lang="en-US", time_range="y")
for r in data["results"]:
    print(r["title"], "→", r["url"])
```

## Quando NÃO usar

- **Você já tem a URL** e quer só extrair conteúdo → use `web_fetch` (mais barato).
- **Busca em livros da biblioteca local** → use `study-busca-livros` (Regra 1 do AGENTS.md).
- **A busca nativa já respondeu bem** → não duplicar chamada (custa 2-3s no SearXNG).

## Integração com o IAM

Quando o orquestrador (eu) precisa de info da web, o fluxo é:

1. **Primeira tentativa:** `web_search` nativa (rápido, integrado).
2. **Se falhar / vier vazio / vier raso / você pedir "busca mais ampla":** cai pra esta skill.
3. **Se você pedir uma URL específica:** `web_fetch` direto.

A skill `study-searxng` **não** substitui `web_search` por padrão — é **fallback/complemento**, não default.

## Status e saúde

- **Endpoint testado em 2026-10-09** (esta instalação): HTTP 200 em ~6ms, JSON 16631B em 2.4s pra query "test".
- **Schema retornado:** `query, results, answers, corrections, infoboxes, suggestions, unresponsive_engines`.
- **Engines ativos detectados:** `google cse` (e provavelmente mais, dependendo da config do SearXNG).
- **Falhas comuns:**
  - Timeout 8s+ sem resposta → rede local off (verifique `tailscale status` e rota pra 192.168.15.0/24).
  - `unresponsive_engines` não-vazio → SearXNG perdeu contato com algum upstream,結果 ainda vêm dos que responderam.
  - JSON inválido → proxy/cache na frente do SearXNG quebrado; tente `?format=json` explícito.

## Dependências

- `python3` (já tem).
- Acesso de rede ao `192.168.15.41:82` (verificar com `curl -m 5 http://192.168.15.41:82/`).
- Nenhuma credencial, nenhuma API key.

## Padrão de saída (texto)

```
🔎  Busca: <query>  —  N resultados
💡 Resposta direta: <se houver>

[1] <título>
    <url>
    <snippet 240 chars>
    (engine=google cse | score=1.00)

[2] ...
```

Padrão de saída (JSON) preserva o schema original do SearXNG — útil pra outras skills consumirem.

## Histórico

- **2026-10-09** — Criada. Decisão: IAM pode usar esta skill como fallback/complemento da `web_search` nativa. Não é default; é acionada quando (a) busca nativa falhou, (b) William pediu busca mais ampla, ou (c) filtro temporal/de idioma faz diferença.
