# Rodada diária de aquisição — 2026-11-26 06:30-06:41 UTC (03:30-03:41 BRT)

## Resultado

- **12 materiais baixados**, todos convertidos em `.md` com conteúdo real verificado
  (0 bytes nulos, 0 traceback, 25k-486k palavras cada) e catalogados nas KBs.
- **5 gaps de área fechados** parcialmente → 8 áreas tinham pendências, 8 entregaram.
- **5 títulos seguem pendentes em 4 áreas.**
- **Lint: 0 erro novo** (4 conhecidos no baseline, 1 aviso `esp:mnemos:tags-sem-kb`).
- **Commit `915f397`** (98 arquivos) pushado.

## Adquiridos

| gap | obra | `.md` |
|---|---|---|
| hermeneutica | Goldsworthy, *Gospel-Centered Hermeneutics* | 765 KB |
| teologia-biblica | Schreiner, *New Testament Theology* | 2.796 KB |
| teologia-biblica | House, *Old Testament Theology* | 1.862 KB |
| preaching | Chapell, *Christ-Centered Preaching* (3ª ed.) | 1.121 KB |
| pastoral | Bridges, *The Christian Ministry* | 1.463 KB |
| pastoral | Tan, *Shepherding God's People* | 637 KB |
| apologetica | Craig, *Reasonable Faith* | 1.145 KB |
| contexto-historico | Malina, *The New Testament World* | 752 KB |
| contexto-historico | Ferguson, *Backgrounds of Early Christianity* | 1.576 KB |
| metodologia | Minayo, *Pesquisa Social* | 183 KB |
| portugues | Cegalla, *Novíssima Gramática da Língua Portuguesa* | 1.705 KB |
| portugues | Pestana, *A Gramática para Concursos Públicos* | 2.991 KB |

## Pendentes (5 títulos / 4 áreas)

- **teologia-biblica** — Vos, *Biblical Theology* (não tentado: `--max 2` já consumido por Schreiner+House)
- **apologetica** — Koukl, *Tactics* (buscado: "nenhum candidato com título/autor compatível")
- **portugues** — Neves, *Gramática de Usos do Português* (**FALHA na conversão**: PDF 46 MB / 508 páginas **sem camada de texto** = escaneado; precisa OCR)
- **critica-textual** — Metzger, *The Text of the New Testament* + Tov, *Textual Criticism of the Hebrew Bible*
  (área ficou **fora do corte** de `--max-areas 8`; é a 13ª da PRIORIDADE)

## Estado do acervo

- 1.508 `.md` · **1.716 materiais** em 86 KBs · 0 órfão · 0 YAML inválido
- 19 `.md` sem tag inferível (estável desde 2026-11-12)
- 13/13 áreas do gap-analysis em **OK**, 0 livro bíblico sem comentário

## BookOrbit fora do ar (de novo)

- `http://192.168.15.26/` e `/api/v1/health` → **código 000** (sem rota).
- **12 uploads falharam** (`orbit_push_falha` no `rodada-log.jsonl`); os ebooks originais
  ficaram **preservados** em `data/biblioteca/_incoming/` (15 arquivos).
- O cron `reenvio-orbit-automatico.sh` (15 min) sobe a fila sozinho quando a LXC voltar.
  **Não é falha da rodada** — é serviço fora do ar.

## Arquivos grandes no `_incoming/` (não convertidos, não são bug)

- `zlib-28429672.pdf` (46 MB, 508 pág.) = Neves, *Gramática de Usos* — escaneado
- `zlib-2768112.pdf` (172 MB, 695 pág.) = Cegalla (o `.md` saiu do EPUB, este PDF é o irmão)
- `zlib-124495400.pdf` (16 MB, 276 pág.) = Malina — **converteu OK** (tem camada de texto)

## Lição

`--max 2` por gap é o que garante cota para 8 áreas; o preço é que o 3º candidato de uma
área produtiva (Vos) fica para a próxima rodada. Não é bug — é o contrato do `--max`.
