---
data: 2026-11-21
tipo: relatorio
serie: rodada-bibliotecario
tags: [bibliotecario, aquisicao, rodada-diaria]
---

# Rodada diária de aquisição — 2026-11-21 (06:30 UTC / 03:30 BRT)

Script: `data/perfil/bibliotecario/rodada-diaria.sh --max 3`
Log: `data/perfil/bibliotecario/logs/rodada-2026-11-21.log`
Duração: 06:30:16 → 06:34:53 UTC (~4m37s)

## Resultado

| item | valor |
|---|---|
| Materiais baixados | **0** |
| Gaps fechados | **0** |
| Gaps pendentes | **0** (13 áreas saturadas) |
| Lint | **0 erro novo** · 4 conhecidos no baseline · 1 aviso |

## Fase 0 — metadado

- Acervo: **1365 `.md`** · **1574 materiais** catalogados · 0 descartado · 0 duplicata · 0 YAML inválido
- Paths: 1574 com `caminho_md`, **0 problema**
- Tagueados agora: 0 · já tinham tags: 1346 · blocos YAML reparados: 0
- Sem tag inferível: **19** (1,4%) — estável desde 2026-11-12 (arquivos auxiliares:
  `LEVANTAMENTO-NECESSIDADES.md`, `catalogo-compras.md`, `outros/*` etc.)

## Fase 1 — aquisição dirigida por gap

`gaps-pendentes-rotina.py` → `areas: {}` + **13 áreas saturadas**:
apologetica, contexto-historico, critica-textual, filosofia, hermeneutica, ingles,
linguas-originais, metodologia, pastoral, portugues, preaching, teologia-biblica,
teologia-sistematica.

**Prova de que a saturação é legítima (não sensor quebrado):**
- Os **59 candidatos** de `rodape.CANDIDATOS` testados um a um com
  `ja_no_acervo(titulo, autor, idx_titulos, idx_sigs)` → **59/59 já no acervo**.
  Lista não-vazia + sensor confirmando = saturação real.
- **Livros bíblicos sem comentário: 0** (cobertura 100%).

**Estado do serviço (medido, não presumido):**

| domínio | resultado |
|---|---|
| `z-lib.gd` | timeout TCP (000) |
| `z-lib.fm` | 000 |
| `z-lib.io` | DNS não resolve |
| `z-lib.sk` | 307 DiamWall |
| `1lib.sk` | 307 DiamWall / cert expirado |

→ O z-library está **fora do ar em todos os domínios** hoje. Mesmo que houvesse
gap pendente, não haveria como baixar. **Não é a causa do 0** (a causa é a
saturação), mas é um segundo bloqueio que precisa ser registrado.

## Fase 2 — catálogo + índice + lint

- `.md` do acervo sem entrada em nenhuma KB: **0** → acervo 100% catalogado
- Cobertura por área: 13/13 **OK** (Hermenêutica 92, Teologia bíblica 35,
  Sistemática 194, Contexto 80, Línguas 34, Prática 206, Filosofia 47,
  Pregação 20, Português 44, Inglês 9, Metodologia 22, Discipulado 92,
  Comentários 122)
- `study-lint.py`: **0 erro novo**, 4 conhecidos no baseline, 1 aviso
  (`esp:mnemos:tags-sem-kb` — tags sem KB no pool: anotacoes, schema, mapa,
  sintese-pessoal, catalogo-de-leitura, philosophy-of-mind) — aviso pré-existente,
  não é erro.

## Nada a corrigir

Lint limpo, 0 órfão, 0 YAML inválido, 0 path quebrado, 0 livro bíblico sem
comentário. A rodada não exigiu correção de causa.

## Ação durável

O catálogo de candidatos (`rodape.CANDIDATOS`, 59 alvos) está **100% coberto**.
Para a rodada voltar a render é preciso **ampliar o catálogo** (instrução
permanente do William, 2026-11-18): acrescentar alvos novos medidos em
`LEVANTAMENTO-NECESSIDADES.md` / `rodape.CANDIDATOS` / `catalogo-ficcao.yaml`.

## Diff do dia

85 arquivos alterados, todos `+1/-1` (só carimbo `atualizado_em` das KBs +
`gerado_em` do `gap-report.json`). Commit `7bef473` pushado para
`git@github.com:willianmendesf/data.git` (master).
