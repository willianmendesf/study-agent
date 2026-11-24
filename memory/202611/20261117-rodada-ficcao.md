# Rodada de ficção — 2026-11-17 (07:15 UTC / 04:15 BRT)

## Resultado

**0 livros baixados · 0 falhas · cota intacta (80 de 80 disponíveis).**

Rodou 2x: cron do sistema às 00:17 UTC e manual às 07:15 UTC (`--max 12`).
Mesmo resultado nas duas. **Quarta rodada seguida** (14, 15, 16 e 17/11) sem
download — o **catálogo está 94/94 adquirido**. Não é cota, não é rede, não é
sensor.

## Provas (medidas)

1. `pipeline-aquisicao.py --status` → **94 no catálogo · 94 adquiridos · 0 pendentes**.
2. `pipeline-estado.json` → 101 itens: **101 com arquivo existente e íntegro**
   (0 bytes nulos, 0 traceback, 0 arquivo ausente, 0 caminho defasado).
   *Nota:* 3 chaves têm `caminho_md` apontando para arquivos que não existem
   (`A-Escola-de-Mulheres-Moliere`, `Os-Misterios-de-Poe`, `idiota/anna-karenina`),
   mas os `.md` reais existem com outro nome (`frances/escola-mulheres-moliere.md`,
   `portugues/Poe-Edgar-Allan-Os-Misterios-de-Poe.md`, e os reapontados em
   `dostoievski/` e `tolstoi/`). Auditoria por nome normalizado: 0 problema.
3. **z-library no ar:** `POST https://z-lib.gd/eapi/book/search` → `{"success":1}`.
   `zlib-api.py limits` → **8 contas × 10 = 80 downloads livres** (today=0).
4. Etapa 2b (libgen, sem cota): **exit 1** = rodou OK, nada a baixar (não é erro).

## O que ficou pendente

1. **Catálogo é o teto** — 94/94. Para a rodada voltar a render:
   `estante-william.yaml` (58) + `lista-aquisicao.md` → `scripts/gerar-catalogo-ficcao.py`.
   Gaps reais fora do catálogo: ***O Nome da Rosa* (Umberto Eco)** — o acervo só tem
   `Como se faz uma tese` do Eco; **A Escravidão na História (Gurowski)**; **obras
   de Eça em coletânea** (vols I-III da estante).
2. **BookOrbit (192.168.15.26) SEM ROTA** — `curl` HTTP 000 / Errno 113 (confirmado
   às 07:16 UTC). O cron de reenvio (15 min) está falhando desde as 06:15 UTC no
   teste de permissão. **18 arquivos** em `_incoming/` (72 MB) esperando a LXC voltar.
   Sobe sozinho quando ela voltar — o cron é idempotente.
3. **2 `.md` de bytes nulos** seguem no disco (órfãos; KB aponta para os bons):
   `outros/anna-karenina-liev-tolstoi.md` (1,92 MB) e
   `outros/idiota-fiodor-dostoievski.md` (1,64 MB). **Apagar exige OK do William.**
4. ***O Caso Final de Sherlock Holmes* (1927)** — segue sem tradução PT-BR.

## Lint

`study-lint.py` → **0 erro(s) novo(s)**, 4 conhecidos no baseline, 1 aviso
pré-existente (`esp:mnemos:tags-sem-kb`). Nada a corrigir.

## Diff em `data/`

Só `perfil/bibliotecario/gap-report.json` (carimbo `gerado_em` 06:32 → 06:34,
gerado pela rodada teológica anterior). Sem alteração de conteúdo.
