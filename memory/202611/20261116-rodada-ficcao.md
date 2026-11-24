# Rodada de ficção — 2026-11-16 (07:15 UTC / 04:15 BRT)

## Resultado

**0 livros baixados · 0 falhas · cota preservada (61 de 80 disponíveis).**

Rodou 2x: cron do sistema às 00:17 UTC e manual às 07:15 UTC (`--max 12`).
Mesmo resultado nas duas. Não é cota, não é rede, não é sensor: o **catálogo
está 94/94 adquirido** — não havia o que baixar. Terceira rodada seguida
(14, 15 e 16/11) na mesma situação.

## Provas (medidas, não supostas)

1. `pipeline-aquisicao.py --status` → **94 no catálogo · 94 adquiridos · 0 pendentes**.
2. `pipeline-estado.json` → 101 itens: 101 com arquivo existente, **0 bytes nulos,
   0 traceback, 0 arquivo ausente** (auditoria arquivo a arquivo).
3. **z-library no ar:** `POST https://z-lib.gd/eapi/book/search` → `{"success":1}`.
   Domínio ativo `z-lib.gd`. Cota: zlib=7, zlib2..8=7-8 → **61 downloads livres**.
4. Etapa 2b (libgen, sem cota): exit 1 = rodou OK, nada a baixar (não é erro).

## O que ficou pendente

1. **Catálogo é o teto** — 94/94. Para a rodada voltar a render:
   `estante-william.yaml` + `lista-aquisicao.md` → `scripts/gerar-catalogo-ficcao.py`.
   Gaps reais fora do catálogo (medidos hoje): ***O Nome da Rosa* (Umberto Eco)** —
   só existe `como-se-faz-uma-tese-umberto-eco.md`; **A Escravidão na História
   (Adam Gurowski)**; **Obras de Eça de Queiroz vols I-III** (coletâneas da estante).
2. **BookOrbit (192.168.15.26) SEM ROTA agora** — `curl` HTTP 000 / Errno 113.
   Às 02:00 UTC ele estava no ar (respondia 409). **18 arquivos** em `_incoming/`:
   - **7 já existem no Orbit** (409 "already exists"): `A-Casa-dos-Espelhos-Virginia-Woolf.epub`,
     `A-Perdicao-Eca-de-Queiroz.epub`, `As-Relacoes-Perigosas-Choderlos-de-Laclos.epub`,
     `zlib-1021315.pdf` (+3 de rodadas antigas). São duplicatas → só saem com OK do William.
   - **11 com erro de rede** na hora da queda (Errno 111/104/113, timeout).
   O cron de 15 min segue tentando; sobe sozinho quando a LXC voltar.
3. **2 `.md` de bytes nulos** continuam no disco (órfãos; KB aponta para os bons):
   `literatura-mundial-classica/outros/anna-karenina-liev-tolstoi.md` (1,92 MB) e
   `.../outros/idiota-fiodor-dostoievski.md` (1,64 MB). **Apagar exige OK do William.**
4. ***O Caso Final de Sherlock Holmes* (1927)** — segue sem tradução PT-BR.

## Lint

`study-lint.py` → **0 erro(s) novo(s)**, 4 conhecidos no baseline, 1 aviso
pré-existente (`esp:mnemos:tags-sem-kb`). Nada a corrigir.

## Nada alterado no repo

A rodada não gerou diff em `data/` (só o log do dia). Sem commit a fazer.
