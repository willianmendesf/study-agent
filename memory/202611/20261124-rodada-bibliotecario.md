# Rodada diária de aquisição — 2026-11-24 06:30 UTC (03:30 BRT)

## Resultado

| item | valor |
|---|---|
| materiais baixados | **0** |
| gaps fechados | **0** |
| pendentes (títulos medidos) | **15** em 8 áreas |
| lint | **0 erro novo** (4 conhecidos no baseline, 1 aviso `esp:mnemos:tags-sem-kb`) |

Log: `data/perfil/bibliotecario/logs/rodada-2026-11-24.log` (rodada do cron das 03:30 BRT,
concluída 06:36:45 UTC) e `logs/rodada-manual-20261124.log` (execução manual, mesmo resultado).

## Fase 0 — metadado

- acervo: 1.468 `.md` · 1.677 materiais catalogados · 0 descartado · 0 duplicado · 0 YAML inválido
- materiais com path: 1.677 · **problemas: 0**
- arquivos tagueados nesta rodada: 4 (categoria `sexual`) · já tinham tags: 1.445 · blocos YAML reparados: 0
- sem tag inferível: 19 (estável desde 2026-11-12; são índices/LEVANTAMENTO e volumes de `outros/`)

## Fase 1 — aquisição (o ponto do dia)

**Nenhum download.** Duas causas distintas, medidas separadamente (regra de 2026-11-10):

1. **36 candidatos já estavam no acervo** → saturação legítima, o sensor `ja_no_acervo`
   reconheceu e pulou sem gastar cota.
2. **15 candidatos ficaram sem verificação** porque o eAPI do z-library respondeu
   **`{"success":0,"error":"Access denied"}`** (HTTP 400) em todos os domínios ativos:
   `z-lib.gd` 400 · `z-lib.sk` 400 (307 → DiamWall) · `z-lib.su` 400 · os outros 11 sem resposta.
   **`zlib-api.py limits` ainda responde 10/10 nas 8 contas** — cota intacta, mas
   **cota OK não prova busca OK** (a lição de 2026-11-23 se repetiu).

### Os 15 pendentes (medidos, não são fantasma)

| área | título |
|---|---|
| hermeneutica | Gospel-Centered Hermeneutics (Goldsworthy) |
| teologia-biblica | New Testament Theology (Schreiner) · Old Testament Theology (House) · Biblical Theology (Vos) |
| preaching | Christ-Centered Preaching (Chapell) |
| pastoral | The Christian Ministry (Bridges) · Shepherding God's People (Tan) |
| apologetica | Tactics (Koukl) · Reasonable Faith (Craig) |
| contexto-historico | The New Testament World (Malina) · Backgrounds of Early Christianity (Ferguson) |
| metodologia | Pesquisa Social (Minayo) |
| portugues | Novíssima Gramática (Cegalla) · Gramática de Usos do Português (Neves) · A Gramática para Concursos (Pestana) |

**Teste de existência por fora do z-library (MCP `biblio`/libgen) em 3 amostras:**
Goldsworthy ✓ EPUB 1 MB · Vos ✓ PDF 12 MB · Chapell ✓ EPUB 2 MB (3ª ed. 2018).
→ **"sem resultados" aqui significa "o z-library negou acesso", não "o livro não existe".**
A 2ª via (libgen, sem cota) resolveria — não foi rodada nesta rodada porque a
`rodada-diaria.sh` só usa o caminho z-library.

## Fase 2 — catálogo + índice + lint

- `.md` do acervo sem entrada em nenhuma KB: **0** (acervo 100% catalogado)
- 13/13 áreas OK (todas com LACUNA 0) · livros bíblicos sem comentário: **0**
- lint: **0 erro novo**

## Ações

- `data/` commitado e pushado: `e651f19` (só carimbos `atualizado_em` das KBs + `gap-report.json`).

## Pendente / próximo passo

1. **Rodar a 2ª via (libgen) para os 15 pendentes** — eles existem, o z-library é que está negando.
2. z-library: aguardar normalização (Access denied em 3 domínios ativos desde 2026-11-23).
3. Ampliar catálogo conforme instrução permanente de 2026-11-18 (8 áreas com 15 títulos
   pendentes já é material; ampliar depois de fechá-los).

## 🐛 Bug corrigido — "sem resultados" engolia "Access denied" (2026-11-24)

**Sintoma:** a FASE 1 dizia `(sem resultados)` para 15 alvos e o resumo anunciava
"0 baixados" — indistinguível de acervo saturado.

**Causa raiz:** `zlib_search()` em `rodape-aquisicao.py` devolvia `[]` nos 3 casos
(serviço fora do ar, acesso negado, busca realmente vazia). O eAPI respondia
`{"success":0,"error":"Access denied"}` (HTTP 400) e o parser pegava `books` ausente → `[]`.

**Correção aplicada:**
- `zlib_search()` devolve **`None`** quando a busca NÃO pôde ser feita
  (`returncode != 0` ou `success == 0`), e `[]` só para busca vazia de verdade.
- O chamador loga `(z-library NEGOU/nao respondeu a busca — servico fora do ar)`,
  grava `{"tipo":"servico_indisponivel"}` no `rodada-log.jsonl` e **continua** os outros gaps.
- Contador global `SERVICO_INDISPONIVEL` imprime no fim:
  `AVISO: N busca(s) falharam por SERVICO FORA DO AR / ACESSO NEGADO — os alvos NAO
  foram verificados. Isto NAO e saturacao do acervo.`
- Validado: `--gap hermeneutica --dry` → 6 já no acervo + 1 `NEGOU` + o AVISO novo.

**Regra durável (3ª vez que aparece):** função que devolve `[]`/`""` para "vazio" E para
"falhou" **mente no relatório**. Sempre separar `None` (falha) de `[]` (vazio) — foi o
mesmo padrão do `epub2md.py` devolvendo 0 chars e do exit code genérico de 2026-11-13.
