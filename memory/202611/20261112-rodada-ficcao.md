# Rodada de ficção — 2026-11-12 07:15 UTC (04:15 BRT)

## Resultado da rodada automática (00:16 UTC, cron)
- `rodada-ficcao.sh --max 12` → **0 baixados, 1 falha** (`Retratos` / Joyce).
- Cota intacta: 8 contas × 10 = **79 downloads** disponíveis.
- O único candidato que apareceu (`Dublineses`, z-library id 23905843, metadados
  "Portuguese") era na verdade a **tradução espanhola** — o gate de idioma pegou
  corretamente (`es 41.26 / fr 22.03 / pt 17.94`) e recusou.

## Rodada manual (07:15 UTC, a pedido do William)
- **z-library INALCANÇÁVEL** neste turno: `z-lib.gd` recusa TCP (000),
  `z-lib.sk` e `z-lib.fm` devolvem **307 DiamWall**, `z-lib.su` 301,
  resto 000. `zlib-api.py domains` cai no fallback `z-lib.gd` (que está morto)
  → todo `limits` estoura timeout. **Não é cota: é serviço bloqueado.**
- 2ª via (libgen, sem cota) rodou: `biblio-api.py search` responde normal.
- O catálogo estava com **94 obras / 93 adquiridas / 1 pendente** — o `Retratos`
  era a ÚNICA obra pendente de todo o catálogo.

## Correção feita (a causa, não o sintoma)
- `biblio-api.py search "Dublinenses Joyce"` achou a **edição PT-BR real**
  (EPUB, md5 `2b636b0f…`, 609 kB) — o z-library só tinha a espanhola.
- Baixada + convertida: 448 KB, 4.457 linhas, `detectar_idioma` = **pt 42.5%**
  (es 12.7, fr 10.9) → é PT-BR de verdade.
- Gravada em `data/biblioteca/literatura-mundial-classica/anglo-saxoes/Retratos-James-Joyce.md`
  **substituindo** o .md espanhol que tinha entrado por engano em 2026-11-11.
- KB `kb-literatura.yaml`: `idioma: Spanish → Portuguese`, `374 KB/1897 lin →
  448 KB/4457 lin`.
- `pipeline-estado.json`: `Retratos-James-Joyce` → `adquirido` (2026-11-12).
- Ebook espanhol movido para `/tmp/rejeitados-2026-11-12/` (não versionado,
  não vai pro Orbit — é tradução errada).

## Estado final do catálogo
**94 no catálogo · 94 adquiridos · 0 pendentes.**

## Pendências reais (não são da rodada)
1. **z-library bloqueado** (DiamWall nos espelhos `.sk`/`.fm`; `.gd` sem TCP).
   Nada a baixar até voltar — a cota (79) está preservada.
2. **BookOrbit (LXC 26) sem rota** — `reenvio-orbit-auto.log` a cada 15 min com
   `[Errno 113] No route to host`. Fila em `_incoming/` intacta (17 arquivos).
3. **`Retratos-James-Joyce.epub` → HTTP 409 no Orbit** ("Dublineses.epub" já
   existe lá) — ou seja, o ebook em PT-BR **já está no BookOrbit**; o 409 é
   falso alarme do reenviador, não falta de arquivo.

## Lint
`study-lint.py` → **0 erro novo**, 4 conhecidos no baseline, 1 aviso (tags sem KB).
