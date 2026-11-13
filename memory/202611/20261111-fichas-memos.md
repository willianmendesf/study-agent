# 2026-11-11 22:38-23:00 BRT — Fichas de leitura publicadas no Memos (tag nova)

## Pedido
William: "publica no mesmo com nova tag, fichas de livros, algo assim."
Contexto: as 4 fichas novas (20-23) do *Último Adeus de Sherlock Holmes* estavam
só no `data/`. As 17 e 18 já estavam no Memos.

## Tag criada
`#fichas-de-livros` — pedido explícito do William. Acrescentada à tabela de
trilhas em `.claude/skills/study-memos-sync/SKILL.md`.

## Publicado (5 memos novos)
| ficha | memo |
|---|---|
| 19 Os Planos do Bruce-Partington | `memos/2hMtnNmv5TdyndRwoGpJx6` |
| 20 O Detetive Moribundo | `memos/RoyVEAW3gYcYHdigJTmM7o` |
| 21 Lady Frances Carfax | `memos/2QTj3uGwBh74d67cjNgHgp` |
| 22 O Pé do Diabo | `memos/GP2tWKTK4MmLsr9WXNBqtW` |
| 23 Seu Último Adeus | `memos/367t7kh5KrAoTJcK3wJgE7` |

Tag aplicada também nas 3 antigas: 17 Vila Glicínia (`gxoUuEBPyFwcCALLHVqnoHV`),
18 Círculo Vermelho (`ENBXqyz3HCMhDyjakb9kkj`) e a ficha do *A Capital*
(`oRdk5derGznvSRozo4zoya`). Total: 8 fichas com `#fichas-de-livros`.

## 🐛 Problema de rede encontrado (IMPORTANTE)
`memos.ison-duck.ts.net` **não resolve** nesta LXC: o **MagicDNS do Tailscale está
desligado** (`tailscale dns status` → "Use Tailscale DNS: disabled").
Além disso o **IPv4 do tailnet** (`100.103.64.20`) **não responde** nas portas
80/443/5230 — timeout. Quem responde é o **IPv6 global** do host:

    http://[2804:7f0:6942:a634:e221:6309:fdc:f815]/api/v1/...

→ `curl` com `-g` (globoff) obrigatório por causa dos `[ ]`.
→ Solução definitiva seria `tailscale set --accept-dns=true`, mas isso mexe em
config de sistema — **não fiz**, só contornei por IP.

## Script criado
`scripts/postar-fichas-memos.py` — posta `.md` de ficha no Memos, remove o
frontmatter, anexa a linha de tags e **grava `memo_id` de volta no frontmatter**.
Testa 3 bases em ordem (IPv6 → IPv4 → hostname) e fixa a que responder.

## Armadilha do GET por uid
`GET /api/v1/memos/<uid>` deu **404** para a ficha da Vila Glicínia enquanto ela
aparecia na listagem com `state: NORMAL`. Não é memo apagado — a listagem e o GET
individual divergiram naquele momento. O **PATCH por uid funcionou** (200).
→ Contorno: buscar o memo pela **listagem** (`pageSize=50`) e usar o uid de lá.

## Lint / commit
`study-lint.py`: 0 erro novo. Commit `099ec75` no repo `data/` (memo_id das 19-23),
push OK.
