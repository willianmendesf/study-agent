# 2026-11-11 — EBD 1-2 Timóteo: Etapa 0 auditada e corrigida

## Pedido do William (2026-11-11 ~02:40 BRT)

> "sim corrije o tratamento"

Referência: a **Etapa 0** de 1-2 Timóteo
(`data/estudos/aulas/ebd-adolescentes-1-2-timoteo/01-etapa-0-leitura-propria.md`),
com o requisito de **extrair o conteúdo literalmente do texto bíblico, sem interpretações
ou acréscimos tendenciosos**.

## O que foi feito

Auditoria **indepetente** do documento contra as fontes, por script, **sem usar o
documento como entrada** (só a forma). Novo script:
`scripts/timoteo-etapa0-auditoria.py`.

## O que a auditoria CONFIRMOU (não mudou)

- **196/196 versículos** do Apêndice A casam **literal** com `almeida_ra.txt` (113 + 83).
- **66/66 linhas** da tabela de léxico: contagem **e** locais conferidos.
- **76 imperativos** (44 em 1 Tm · 32 em 2 Tm), **62** em 2ª pessoa do singular,
  **53 versículos** com imperativo.
- **154 dos 196 (78.6%)** sem Jesus/Cristo/kúrios; Jesus/Cristo 28 (14.3%); kúrios 24 (12.2%).
- **30/30 nomes** de §8.1 com contagem e locais conferidos.

## O que a auditoria CORRIGIU (11 defeitos reais)

| # | Onde | Antes | Depois |
|---|---|---|---|
| 1 | §0 | "1304 formas lexicais gregas distintas" | **1267** (medido) |
| 2 | §0 | "3050 tokens gregos" | **2901** (medido) |
| 3 | §3 | **17 verbetes Strong** truncados ou substituídos por ruído de TDNT (`TDNT - 4:762,610; n m`) | definição real da fonte |
| 4 | §6.1 | "um só Deus" atribuído a 2 Tm 2:22 | 1 Tm 2:5 (a linha era duplicada) |
| 5 | §6.1 | "ele que te dará a recompensa (o justo juiz)" em 1 Tm 1:17-18 · 2 Tm 4:14 | só 2 Tm 4:14, com a citação literal |
| 6 | §6.2 | "até que ele apareça (φανερόω)" em 1 Tm 6:15 | "no tempo próprio, manifestará…" (literal) |
| 7 | §6.2 | "o Senhor Jesus Cristo" em 2 Tm 4:22 | "O Senhor seja com o teu espírito" |
| 8 | §6.3 | "a metida" em 1 Tm 5:20 | "repreende-os na presença de todos…" |
| 9 | §3.1 / §6.3 | "no laço do Diabo" atribuído a 1 Tm 1:20 | 1 Tm 3:7 · 2 Tm 2:26 ("entregues a Satanás" em 1 Tm 1:20) |
| 10 | §9.7 | παιδεία "inclui repreensão e punição" | o que o texto diz: "para ensinar, para repreender, para corrigir, para instruir em justiça" |
| 11 | §8.2 | "31 pessoas" | **30** (a tabela tem 30) |

Além disso: 9 citações quase-literais normalizadas ao texto da ARC (o doc usava
"Christ Jesus", "há em Cristo Jesus", "a manifestação", "ressuscitado" — a ARC diz
"Jesus Cristo", "está em Cristo Jesus", "manifestou pelo aparecimento", "ressurgido").

## Por que os números 1304/3050 nasceram

A **versão anterior** do documento (commit `058be07`) dizia "1.275 tokens distintos" —
esse número vem do `tr.txt` (não-morfológico). A versão `bfbfcff` trocou por
"1304 / 3050", que **não é reproduzível** por nenhuma medição séria:
variei 4 combinações (com/sem número de verso, com/sem "Chapter", `tr.txt` × `trparsed.txt`,
só 1 Tm / só 2 Tm / + Tito) e nenhum par bate.

**Valor definitivo:** TR parsed (a fonte declarada no frontmatter) →
**2901 tokens gregos** e **1267 formas lexicais distintas**.

## Lição (reutilizar)

> **Um documento de estudo que se diz "medido" precisa de um auditor independente.**
> O script que gerou os números e o script que confere os números **não podem ser o mesmo**
> — se forem, o número errado se auto-confirma. Escrevi `timoteo-etapa0-auditoria.py` do zero
> (parser do TR reescrito: o formato real é `palavra [G####] TAG`, com Strong elíptico
> herdando a palavra anterior), e ele reproduziu **tudo** que estava certo — o que provou
> que os defeitos estavam **nas afirmações**, não no método.

**Armadilha do TR:** a tag morfológica verbal é `V-<tempo><voz><modo>-<pessoa><num>`.
Imperativo = modo `M` (`V-PAM-2S`); indicativo = `V-AAI-2S`. **Falso-controle obrigatório:**
há **22** formas 2ª pessoa do singular **não**-imperativas — sem esse controle, um parser
errado conta "2ª pessoa do singular" em vez de "imperativo".

**Armadilha do ARC:** o fim do livro se acha pelo **título em caixa alta** cercado de linha
vazia, não por regex de "próximo livro" (o `Tito` e o `^Z` do fim de 2 Tm quebram o regex).

## Commits

- `aace256` (data) — Etapa 0 auditada e corrigida
- `e64072c` (repo) — `scripts/timoteo-etapa0-auditoria.py`

Lint: **0 erro novo**, 4 conhecidos no baseline, 1 aviso (tags sem KB).

## Pendência

- O memo no Memos (`memos/9At4hjsNxtASR4EoTg5QGg`) ainda tem a **versão antiga** — precisa
  ser re-postado com o texto corrigido, ou marcado como revisado.
