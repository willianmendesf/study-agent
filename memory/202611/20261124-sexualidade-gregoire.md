# 2026-11-24 — The Great Sex Rescue + Weiner-Davis em português

## O que foi pedido
William pediu: baixar *Come as You Are* (Nagoski) e *The Great Sex Rescue* (Gregoire) em
inglês (ele usa tradutor), e mandou o **EPUB traduzido** do Weiner-Davis (*O Casamento
Faminto de Sexo*), já subido por ele no BookOrbit.

## O que foi feito
- **Gregoire baixado**: o download pelo MCP `biblio` falhou ("Libgen direct: terminated")
  e o `curl` normal abortava em ~4,3 MB de 9,3 MB (timeout do libgen). **Solução: `curl -C -`
  (retomada)** em background com `-m 900` → completou os 9.338.354 bytes.
  - Aprendizado: EPUB grande do libgen.li corta a conexão antes do fim; **retomar com
    `-C -`** em vez de rebaixar do zero.
- **Conversão**: `epub2md.py --dest /tmp/sexo-dl` → 425 KB, 4.196 linhas.
  **Sem normalização** (`normalizado=0`) — o texto já vinha limpo.
- Arquivos canônicos:
  - `data/biblioteca/sexual/Gregoire-Great-Sex-Rescue-EN.md`
  - `data/biblioteca/sexual/Weiner-Davis-O-Casamento-Faminto-de-Sexo-PT.md`
- **KB**: `kb-sexual` 8 → **10 volumes** (`yaml.safe_dump(width=4096)`).
- **Nota de estudo atualizada**: `data/estudos/notas/vida-crista/nunca-houve-bons-momentos-desde-o-casamento.md`
  → seção **5.5** (o que o Great Sex Rescue acrescenta) e **5.6** (a edição em PT que ele mandou);
  seção 7 reescrita (5 obras, 2 em PT).

## O achado que importa (Gregoire)
- Pesquisa com **+20.000 mulheres evangélicas**.
- **Só 48%** das mulheres gozam sempre/quase sempre (homens ~95%) → *orgasm gap*.
- **Preliminares adequadas = 6,43× mais chance** de gozar com frequência.
- **Só 39%** gozam só com penetração.
- **70,9%** não estão excitadas no início mas chegam lá (desejo responsivo, com dados de igreja).
- **Metade** das mulheres que casaram virgem **não estavam excitadas na primeira vez**
  (`Only 52% were`). Frase-chave: *"your marital status is not what makes sex orgasmic or
  not — your arousal level is. The key to sexual pleasure is not a wedding ring."*
- **Gatekeeper**: 81,2% cresceram ouvindo que "meninos empurram os limites"; a elas se
  ensinou a ser o **freio**. Consequência: menos facilidade de falar ao marido sobre prazer.
  Caso de Charlotte: **26 anos de casamento** para descobrir o que era excitação.
- **O dado mais forte**: crer que sexo é **obrigação** → **+37% de dor sexual** e **−29% de
  frequência de orgasmo**. Base da frase *"without the ability to say no, we can never truly
  say yes"*.
- Crítica nominal (com citação): *The Act of Marriage* (LaHaye), *Love & Respect*,
  *Intended for Pleasure* (Wheat), *Every Heart Restored*, *His Needs Her Needs*.

## Estado dos serviços (2026-11-24 04:20)
- **BookOrbit (192.168.15.26) fora do ar**: TCP recusa em :80; tailnet `ebooks` offline há 2h;
  `100.82.250.19` timeout; `ebooks.ison-duck.ts.net` sem DNS.
  → **O EPUB do Gregoire foi deixado em `data/biblioteca/_incoming/`
  (`Gregoire - The Great Sex Rescue.epub`, nome `Autor - Titulo.ext`)** e o cron
  `reenvio-orbit-automatico.sh` (15 min) sobe sozinho quando o Orbit voltar.
- **Memos fora do ar**: IPv6 (2804:...), IPv4 (100.103.64.20) e hostname → todos 000/timeout.
  **Nota não postada.**

## Bug/limpeza
- O upload do EPUB do William foi auto-catalogado pelo `catalogar-filemon` e caiu em
  **`comentarios-biblicos/de995506-file-41.md`** (pasta errada, nome feio). Removido
  depois de confirmar **md5 idêntico** ao arquivo bom em `sexual/`.
- O original `/tmp/picoclaw_media/de995506_file_41.epub` **sumiu** (limpeza de mídia do
  picoclaw, janela de 30 min) antes de eu copiá-lo. Não faz falta: ele mesmo já subiu no
  Orbit, e o `.md` está no acervo.

## Lint
`study-lint`: **0 erro novo**, 4 conhecidos, o mesmo aviso `esp:mnemos:tags-sem-kb`.
Commits: `1188780` (data) pushado.
