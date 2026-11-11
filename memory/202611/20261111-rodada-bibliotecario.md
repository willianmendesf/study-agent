# 2026-11-11 — Rodada diária de aquisição (Bibliotecário) 06:30 UTC

**Pedido (cron 06:30 UTC):** rodar `rodada-diaria.sh` (fases 0+1+2) e reportar:
quantos materiais baixados, quais gaps fechados, quantos pendentes, resultado do lint;
se o lint acusar erro novo, corrigir a causa antes de encerrar.

## Resultado medido

| item | valor |
|---|---|
| materiais baixados | **2** (depois das correções; 0 na 1ª execução) |
| gaps fechados | **2** — `teologia-sistematica` e `teologia-biblica` |
| gaps pendentes | **0** (legítimo, auditado) |
| lint | **0 erro(s) novo(s)**, 4 conhecidos no baseline, 1 aviso — **exit 0** |
| acervo | 1.183 → **1.185** `.md` · 1.390 → **1.392** materiais nas KBs |
| 0 deleções | confirmado (`git status` → 0 arquivos ` D`) |

**A 1ª execução reportou 0 gaps e 0 downloads — e isso estava ERRADO.**
A auditoria (regra durável "gap zero = sensor quebrado?") provou que 2 gaps
estavam **mascarados** e que 2 outros apontavam para **obras que não existem**.
Corrigi a causa, re-rodei a fase 1 e fechei os 2 gaps reais.

## Os 2 materiais conquistados

| Gap | Material | Autor | Tamanho |
|---|---|---|---|
| teologia-sistematica | *Systematic Theology* | Louis Berkhof | 2,1 MB · 14.784 linhas |
| teologia-biblica | *Theology of the Old Testament, Vol. II* | Walther Eichrodt | 1,4 MB · 35.118 linhas |

Ambos catalogados (`kb-teologia-sistematica` +1, `kb-teologia-biblica` +1),
0 órfãos, 0 tracebacks na conversão, título conferido **dentro** do arquivo
(regra 10 da memória).

## 3 bugs corrigidos na causa

1. **BUG V2 — o sensor de gaps casava título sem olhar o autor.** O BUG N2/N3/N4/N5
   (2026-10-31) corrigiu o *picker*, mas o *sensor* (`ja_no_acervo`) continuou
   aceitando título exato e Jaccard ≥ 0,85 **sem corroborar o autor**.
   Efeito: "The Art of Biblical Preaching" (Lesslie) casava com o livro do
   **Whitesell**, e "Systematic Theology" (Berkhof) casava com o do **Grudem**.
   → novo helper `_autor_divergente()`; a divergência só é declarada quando o
   frontmatter **tem** `autor:` (onde não há autor, não há como provar divergência).

2. **BUG W — a chave de "já coberto" era só o título.** "Systematic Theology"
   (Grudem) bloqueava "Systematic Theology" (Berkhof) — o rodapé pulava o alvo
   Berkhof **em silêncio**, sem nem buscar no z-library.
   → novo helper `_chave_candidato()` → `titulo|sobrenome`.

3. **BUG X — 2 alvos fantasma no `CANDIDATOS`.**
   - "The Art of Biblical Preaching" (**Lesslie**) → é de **Whitesell** (1950).
     "Lesslie" era **Lesslie Newbigin** (teólogo da missão) — confusão de nome
     no `LEVANTAMENTO-NECESSIDADES.md` (2 lugares).
   - "Theology of the Old Testament" (**Berding**) → **não existe**. O Berding é
     (co)editor de "Three Views on the **New** Testament Use of the Old Testament"
     (que já está no acervo). Trocado pelo canônico real: **Eichrodt**.
   → confirmado por `openlibrary.org/search.json` (fonte externa).

## Teste de regressão

- Auto-referência (1.182 arquivos do acervo): **20 falhas antes, 20 depois**
  → **0 regressão, 0 curação** (as 20 são pré-existentes: títulos curtos como
  "Contos"/"Beloved"/"Tartufo" < 8 chars, bloqueados por design).
- 15/15 pares que **devem** casar continuam casando.
- 0 arquivos corrompidos (NUL), 0 tracebacks novos.

## Estado

- Orbit **OFFLINE**: os 2 ebook originais preservados em `_incoming/`
  (`zlib-124880320.epub`, `zlib-16773105.epub`) — o fix do BUG O funcionou.
- Cota: **58 downloads disponíveis** (8 contas), 0 gastos na 1ª execução.
- SearXNG (192.168.15.41:82) sem rota — usei `web_fetch`/`web_search` nativos.
- Commits: `b6cfdb2` (material + patches) e `93ea03e` (memória) no sub-repo `data/`,
  ambos pushados. Lint exit 0.

## Regras novas (23 no total, em `data/perfil/memorias/rodada-aquisicao.md`)

- **Corrigir o SENSOR junto com o PICKER** — os dois implementam "já está no acervo?".
- **Regra de Jaccard sempre com corroboração de autor.**
- **A chave de "já coberto" tem de ser (título, autor).**
- **Auditar o ALVO, não só o sensor** — gap zero pode esconder sensor quebrado,
  **alvo fantasma** e **autor errado**.
- **Confirmar o autor por fonte externa** quando o z-library só devolve obras diferentes.
