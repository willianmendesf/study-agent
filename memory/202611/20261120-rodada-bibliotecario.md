# Rodada diária de aquisição — 2026-11-20

## Resultado

| Item | Valor |
|---|---|
| Materiais baixados pela rodada automática | **0** |
| Materiais adquiridos manualmente (gap `metodologia`) | **1** (Fundamentos de Metodologia Científica, Marconi & Lakatos, 8. ed., Atlas 2017) |
| Gaps fechados | **1** (`metodologia`) |
| Gaps pendentes ao final | **0** (13 áreas saturadas) |
| Lint | **0 erro novo**, 4 conhecidos no baseline, 1 aviso |

## O que aconteceu, em ordem

1. **FASE 0 falhou na primeira execução** — `Permission denied` em
   `data/biblioteca/global/kb-*.yaml` e no diretório `logs/`. Causa: 6.410 arquivos de
   `data/` estavam **root-owned** (mesmo problema de 2026-11-13, voltou). Corrigido com
   `sudo chown -R willian:willian data` e a rodada foi repetida.

2. **FASE 1 acusou 1 gap: `metodologia`** — alvo `Metodologia do Trabalho Científico`
   (Lakatos & Marconi). A rodada baixou, mas a conversão falhou:
   - id 2646880 → PDF **escaneado**, `extract_text()` = 0 chars em todas as 212 páginas;
   - id 5147946 → mesmo arquivo (212 páginas, 0 chars).
   - OCR a 150 dpi nesta LXC: **>4 min por página** → ~3h30 para as 212 páginas.
     Inviável dentro da rodada (e `exec` corta em 300 s). Abortado.

3. **Solução real:** baixado o **EPUB com texto** da obra irmã das mesmas autoras —
   *Fundamentos de Metodologia Científica*, 8. ed., Atlas 2017 (z-library id 5458478).
   Cobre a mesma disciplina (CG06/CG12/CG13 do edital IPB), 643 KB, 9.059 linhas.

4. **Descoberta grave:** o arquivo `data/biblioteca/zetesis/Fundamentos-de-Metodologia-Cientifica.md`
   que já estava no acervo era **lixo** — 85 KB, 3.517 linhas, 1.408 delas de **CSS**
   (`page_styles.css`, `calibre7`, `line-height`…), vindo de uma conversão errada de EPUB
   (dump do zip, não do texto). O livro estava catalogado na KB como se fosse bom.
   → Substituído pelo texto real, com frontmatter completo (autor, editora, ano, tags).
   Backup do antigo em `/tmp/Fundamentos-corrompido-backup.md`.

5. **KB corrigida:** `kb-zetesis` — a entrada do "Fundamentos" passou a apontar para o
   texto real (628 KB, 9.059 linhas, autor completo, editora, ano, 4 tags).
   `total_volumes` 9 → **8** (a entrada duplicada que o catalogador automático criou
   foi removida). Todos os 8 caminhos conferidos: existem.

6. **Catálogo ajustado** (`rodape-aquisicao.py`, bloco `metodologia`): o alvo
   `Metodologia do Trabalho Científico (Lakatos)` foi trocado por
   `Fundamentos de Metodologia Científica (Marconi)`, com o motivo registrado no código
   (o outro só existe como PDF escaneado no z-library). Sem isso a rodada tentaria o
   mesmo PDF impossível todo dia e reportaria "falha de conversão" para sempre.

7. **Rodada repetida do zero:** FASE 0 OK (1.544 materiais, 0 problema de path,
   1.316 com tags, 19 sem tag inferível — estável desde 2026-11-12) · FASE 1
   **0 gaps pendentes** (13 áreas saturadas) · FASE 2 0 órfão · lint 0 erro novo.

## BookOrbit — fora do ar

`192.168.15.26` → **No route to host** (HTTP 000, também no `/api/v1/health`).
O upload do EPUB não pôde ser feito. O cron de reenvio automático está registrando a
mesma falha a cada 15 min. O arquivo ficou preservado em
`/tmp/metod-dl/Marconi & Lakatos - Fundamentos de Metodologia Cientifica.epub`;
quando o Orbit voltar, subir com `scripts/orbit-subir-livro.py`
(título `Fundamentos de Metodologia Científica`, autor
`Marina de Andrade Marconi & Eva Maria Lakatos`).

## Cota do z-library

8 contas × 10 = **79 downloads disponíveis** no início; 5 consumidos (3 do Lakatos
que não serviram + 2 aproveitados: EPUB 5458478 e a 7. ed. 24059947 como reserva).

## Regras que este dia reforçou

- **Permission denied em `data/` → checar `sudo find data -user root` antes de suspeitar
  do código.** Segunda reincidência (a primeira foi 2026-11-13).
- **PDF escaneado no z-library não é falha da rodada, é característica do arquivo.**
  Antes de insistir, medir `extract_text()` das primeiras páginas. Se 0, trocar o alvo
  (obra irmã, outra edição, outro formato) — não gastar horas de OCR.
- **Arquivo no acervo ≠ arquivo bom.** O `Fundamentos` estava catalogado e era um dump
  de CSS. Sempre que substituir um `.md`, conferir se há `page_styles` / `calibre` no
  texto e contar linhas de prosa contra linhas de estilo.
