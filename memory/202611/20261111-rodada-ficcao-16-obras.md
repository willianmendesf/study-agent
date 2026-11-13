# 2026-11-11 — Rodada de ficção: 16 obras novas (o z-library VOLTOU)

## Resposta curta
Sim, baixou: **16 obras novas** na rodada de 00:17 UTC (era a primeira rodada com
z-library de pé depois de 3 dias offline).

## Números medidos
- Acervo: 1.150 .md (10-11) → **1.183 .md** (11-11)
- Materiais catalogados nas KBs: 1.357 → **1.390** (0 sem KB, 0 path quebrado)
- Índice: 1.528 docs / 676.078 trechos / 2.275 MB (+4.838 trechos)
- Rodada teológica (gap): 13 áreas, 0 lacunas, 0 downloads — **saturação legítima**
- Lint: 0 erro novo, 4 conhecidos no baseline, 1 aviso (tags sem KB)

## As 16 obras
Via z-library (cota 8 contas × 10 = 80, domínio `z-lib.gd` de pé):
1. Contos — Ivan Turgenev (russo, 254 KB)
2. Cyrano de Bergerac — Edmond Rostand (romantismo, 207 KB)
3. Estado de Sítio — Albert Camus (frances, 209 KB)
4. O Poder e a Glória — Graham Greene (ingles, 477 KB)
5. O Problema da Dor — C. S. Lewis (ingles, 279 KB)
6. O Sol Também Se Levanta — Ernest Hemingway (anglo-saxoes, 373 KB)
7. Ortodoxia — G. K. Chesterton (ingles, 392 KB)
8. Os Amores — Bocage (antigos, 259 KB)
9. Pedro Páramo — Juan Rulfo (mexicano, 209 KB)
10. Pequenos Burgueses — Maxim Gorki (russo, 194 KB)
11. Quando o Espiritual Domina — Simone de Beauvoir (modernismo, 444 KB)
12. Santuário — William Faulkner (romantismo, 459 KB)

Via 2ª via sem cota (libgen/biblio, dentro da rodada bibliotecário):
13. Terra dos Homens — Antoine de Saint-Exupéry (antigos, 245 KB)
14. Suave É a Noite — F. Scott Fitzgerald (anglo-saxoes, 819 KB)
15. Tartufo — Molière (frances, 358 KB)
16. O Homem que foi Quinta-feira — G. K. Chesterton (ingles, 309 KB)

Todas com conteúdo conferido, catalogadas nas KBs (12 em `kb-literatura.yaml`,
4 em `kb-literatura-mundial-classica.yaml`) e enviadas ao BookOrbit (`Orbit=ok`).

## Falhas (5) — e o que elas revelam
1. **O Estrangeiro (Camus)** — 66 MB, edição *manga*: a extração devolveu
   erro/CSS em vez de texto. **NÃO gravado** (a trava anti-lixo funcionou).
2. **O Peregrino** — o z-library serviu `The Pilgrim's Progress` (inglês) para o
   título PT → "conteúdo divergente: título não aparece no texto".
3. **Uma História de Duas Cidades** — idem: veio "História em Duas Cidades"
   (tradução ≠ a que o catálogo pede) → conteúdo divergente.
4. **Sangue Bom (Flannery O'Connor)** — veio como **RTF com extensão `.bin`**
   → o conversor não reconheceu → "conversão-sem-md".
5. **O Conde de Abranhos** — nenhum candidato no z-library (score -99).

**Lição:** a trava de conteúdo divergente e a de erro-no-lugar-de-obra
funcionaram — nenhuma obra corrompida entrou no acervo. O que falta é
(a) reconhecer RTF (`.bin` com cabeçalho `{\rtf`) no conversor e
(b) fallback de idioma no matcher (aceitar o título original `titulo_en`).

## BookOrbit: 14 ebooks na fila, TODOS com HTTP 409
`reenvio-orbit-automatico.sh` (crontab de 15 min) roda e leva 409 em 100% da fila:
```
A file named "A Room of One's Own (1929).epub" already exists at the target location
```
O nome no servidor vem dos **metadados do EPUB** (`dc:title` + ano), não do nome
local — e as obras JÁ FORAM enviadas antes (o log mostra `[OK] A-Casa-dos-Espelhos-
Virginia-Woolf.epub -> Orbit` em rodadas anteriores). **O 409 é "já está lá"**,
não erro. O script trata 409 como falha → os arquivos locais nunca são apagados →
a fila nunca esvazia e o cron roda para sempre barrando.
**Correção a fazer:** tratar 409 como sucesso-equivalente (apagar local, contar como
reenviado). Assim a fila de 14 se resolve sozinha.

## Orbit ficou lento no fim da janela
02:06 UTC — `GET /api/v1/libraries/1/books` respondeu 404 (rota inexistente = servidor
vivo) em 37 s; o `POST /auth/login` seguinte estourou 115 s de timeout. O Orbit está
no ar mas lento (coerente com a fila grande de upload de madrugada).

## Commits
- `7ed5243` — ficcao: +16 obras novas
- `85b778f` — bibliotecario: estado da rodada 2026-11-11
- Ambos pushados para `origin/master`.

## Pendências
1. **Corrigir o tratamento de 409** no `reenviar-incoming-orbit.py` → fila de 14
   limpa sozinha.
2. **Suporte a RTF** no conversor (`.bin` com cabeçalho `{\rtf`) → "Sangue Bom".
3. **Fallback de idioma** no matcher de título (`titulo_en` do catálogo).
