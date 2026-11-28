# Rodada diária de aquisição — 2026-11-28 06:30 UTC (03:30 BRT)

## Resultado

| item | valor |
|---|---|
| baixados | **0** |
| gaps fechados | **0** |
| gaps pendentes | **0** (13 áreas saturadas) |
| lint | **0 erro novo** (4 conhecidos + 1 aviso `esp:mnemos:tags-sem-kb`) |

## Por que 0 baixados — as duas causas medidas (regra 2026-11-10)

1. **Saturação legítima (é o caso):**
   - `gaps-pendentes-rotina.py --json` → `{"areas": {}, "comentarios": [], "saturados": [13 áreas]}`
   - Os **76 candidatos** de `rodape.CANDIDATOS` testados um a um com
     `ja_no_acervo(c[0], c[1], idx_titulos, idx_sigs)` → **76/76 já no acervo**, 0 faltando.
     Lista não-vazia + sensor confirmando = saturação real (BUG V2 fechado em 2026-11-11).
   - Por isso a FASE 1 foi no-op explícito: `gaps medidos (pendentes no acervo): 0`.
2. **Serviço: z-library NEGANDO acesso hoje.** `POST https://z-lib.gd/eapi/book/search`
   → `{"success":0,"error":"Access denied"}`. Se houvesse gap, não baixaria nada
   (4ª ocorrência: 2026-11-23, 24, 28). **Cota OK não prova busca OK.**
   Caminho alternativo que funciona: 2ª via libgen (`pipeline-biblio.py`) / MCP `biblio`.

## Fase 0 (metadado)

- acervo **1.554** `.md` · **1.763** materiais nas KBs · 0 descartado · 0 duplicado · 0 YAML inválido
- materiais com path: 1.763 · problemas: **0**
- tagueados nesta rodada: **16** (historia-biblica 9 · messias 4 · cultura-textos-biblicos 2 ·
  comentarios-biblicos 1) — são os **Edersheim** de 2026-11-28 que estavam sem `tags:`
- já tinham tags: 1.519 · blocos YAML reparados: 0 · sem tag inferível: 19 (estável desde 2026-11-12)

## Fase 2 (catálogo + lint)

- `.md` sem entrada em nenhuma KB: **0** → acervo 100% catalogado, nada a fazer
- 13/13 áreas OK · 0 livro bíblico sem comentário
- `study-lint: 0 erro(s) novo(s), 4 conhecido(s) no baseline, 1 aviso(s)`

## Diff do dia

Só carimbo: `atualizado_em` em ~84 KBs + `gap-report.json` + os 16 frontmatters de tag
(Edersheim). 101 arquivos, 185 inserções / 105 deleções.
Commit `8bb6af3` (data), pushado.

## Pendências (fora desta rotina)

- **Edersheim**: 17 arquivos prontos em `~/ebooks-gerados/edersheim-pendente/` e
  `/tmp/edersheim/upload/` — BookOrbit dorme até 05:00 BRT; `scripts/subir-edersheim.sh`
  sobe sozinho na janela.
- `_incoming/` com 21 arquivos (fila do cron de reenvio ao Orbit, 15 min, janela 05:00–23:00 BRT).
- **Para a rodada voltar a render**: ampliar o catálogo (`rodape.CANDIDATOS` /
  `catalogo-ficcao.yaml` / `LEVANTAMENTO-NECESSIDADES.md`) — instrução permanente de
  2026-11-18. Com z-library negando acesso, ampliar sem plano de 2ª via não resolve.
