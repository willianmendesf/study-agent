# Rodada diária de aquisição — 2026-11-12

**Horário:** 06:30–06:34 UTC (03:30 BRT)
**Comando:** `bash data/perfil/bibliotecario/rodada-diaria.sh --max 2`
**Log:** `data/perfil/bibliotecario/logs/rodada-2026-11-12.log`

## Resultado

- **Baixados:** 0
- **Gaps fechados:** 0
- **Gaps pendentes:** 0 (13 áreas saturadas)
- **Lint:** 0 erro novo · 4 conhecidos no baseline · 1 aviso

## Fase 0 — metadado
- acervo: **1198 .md**
- materiais: 1405 | descartados 0 | dup 0 | yaml_err 0
- MATERIAIS COM PATH: 1405 | problemas: 0
- tagueados: 0 · já tinham tags: 1179 · YAML reparado: 0
- 19 sem tag inferível (LEVANTAMENTO, catálogo de compras, `outros/*`)

## Fase 0/2 — gap-analysis
- Acervo 1286 arquivos · 184 tags distintas · 20 invisíveis (1,6%) · 1405 catalogados
- 13 áreas, **todas com LACUNA 0 / OK**:
  Hermenêutica 86 · Teol. bíblica 33 · Teol. sistemática 161 · Contexto 79 ·
  Línguas originais 34 · Teol. prática 130 · Filosofia 41 · Pregação 19 ·
  Português 44 · Inglês 9 · Metodologia 22 · Discipulado 91 · Comentários 121
- Livros bíblicos SEM comentário: **0**

## Fase 1 — aquisição
- `gaps-pendentes-rotina.py --json` → `areas: {}`, `saturados: [13 áreas]`
- **Prova de que a saturação é legítima (e não sensor quebrado):** os 50
  candidatos de `rodape.CANDIDATOS` foram testados um a um com
  `ja_no_acervo(titulo, autor, idx_titulos, idx_sigs)` → **50/50 já no acervo,
  0 pendentes**. Lista de candidatos não está vazia; a biblioteca é que cobre.
- **Serviço z-library no ar:** `POST https://z-lib.gd/eapi/book/search`
  (`message=calvin institutes&limit=1`) → `{"success":1, books:[...]}`.
  Ou seja: 0 downloads **não** é serviço fora do ar nem cota esgotada —
  é saturação real. Cota preservada.

## Fase 2 — catálogo + índice + lint
- `.md` sem entrada em nenhuma KB: **0** — acervo 100% catalogado
- `study-lint`: 0 erro novo · 4 conhecidos · 1 aviso
  (`esp:mnemos:tags-sem-kb`: anotacoes, schema, mapa, sintese-pessoal,
  catalogo-de-leitura, philosophy-of-mind) — aviso conhecido, não erro.

## Commit
- `4b5e83c` (data) — 85 arquivos, todos `atualizado_em` das KBs + gap-report.json
- Push: `b568a38..4b5e83c master -> master` (git@github.com:willianmendesf/data.git)
