# 2026-11-25 — Luto no acervo + auditoria acervo × BookOrbit

## Pedido
1. "quais livros do meu acervo tratam sobre o luto?"
2. "Você está toda hora referenciando livros que não existem pra mim no bookorbit,
   precisa rever, ex: Aconselhamento Bíblico vol. 8, nao existe no bookorbit"
3. "ou mesmo com outro nome: Aconselhamento Bíblico vol. VIII"

## O erro (confirmado por medição)
O William estava certo. **`Aconselhamento Bíblico Vol VIII` não existe no app.**
O acervo local tem 1.601 títulos nas KBs; o BookOrbit tem **1.404 livros**.
**653 títulos das KBs não têm correspondência no app.** Eu citava a KB, não o app.

Caso concreto: `Coletanias_de_Aconselhamento_Biblico-Volume_VIII.md` (454 KB,
11.999 linhas) está no acervo e NÃO está no app. Contém o melhor capítulo de luto
do acervo: **"A Dor da Perda: compreendê-la e tratá-la não é questão de um
processo, mas de uma Pessoa"** (Paul Randolph). O PDF original está em
`/media/willianmendesf/...` — HD não montado nesta máquina → não há como
reconverter para subir.

## O que foi feito
- `scripts/auditar-orbit.py` (novo): cruza todas as KBs com o catálogo do app,
  grava `data/perfil/bibliotecario/auditoria-orbit.json`.
  Tem `--validar` com **10 casos de controle** (10/10 OK), incluindo o Vol VIII.
- Catálogo do app levantado por varredura de id 1→2600 (a `/books/search` do
  BookOrbit **não pagina** e tem `limit` máximo 20; `GET /books` → 404).
  1.404 livros com título legível → `/tmp/orbit-catalogo.json` (efêmero).
- Nota de estudo: `data/estudos/notas/vida-crista/luto-o-que-existe-no-bookorbit.md`
  → Memos `memos/7LC2PbsocbMgrB5akLf9ie` (IPv4 100.103.64.20; IPv6 em timeout).

## Os 4 bugs de casamento que o auditor teve (todos medidos)
1. `minimo=4` + alvo `max(2, ...)` → título de 1 token ("Coletâneas Vol III")
   **nunca** casava. 5 falsos negativos só em aconselhamento.
2. Sem trava de volume, **"Vol VIII" casava com "Vol VI"** — exatamente o erro
   que o William apontou. Volume diferente agora nunca casa.
3. Número de série do app ("Série Aconselhamento Livro 16") não existe na KB →
   falso negativo em toda a série. Trava de volume só vale quando a **KB** declara.
4. Prefixo de 5 letras: "familia"×"familias", "biblico"×"biblica". Igualdade
   exata perdia plural/gênero.

## Método que funcionou para achar tudo no app
`GET /api/v1/books/<id>` um a um (1→2600, 0,22 s de pausa, ~11 min).
`/books/search?q=` limita a 20 e não pagina; `GET /books` → 404;
`GET /libraries/1/books` → 404. Só o endpoint por id devolve o catálogo inteiro.

## Resposta do luto (o que está de fato no app)
- **[152]** Sofrendo com a perda de um filho — Ryan Showalter (o único com tema inteiro)
- **[144]** Enfrentando a morte com esperança — Powlison
- **[115]/[408]** Aconselhamento Bíblico Vol 6 — cap. "Como Ajudar uma Criança
  Enlutada", Judy Blore, p. 51
- **[130]/[420]** Coletâneas Vol VI — mesmo capítulo
- **[145]** Eu quero morrer · **[146]** Lutando contra o câncer ·
  **[150]** Doença de Alzheimer (Série Aconselhamento)
- **[1764]** O problema da dor (Lewis; metadado sujo no app) ·
  **[1548]** Confissões (Livro IV = amigo morto, Livro IX = morte de Mônica) ·
  **[320]** Envelhecendo com Graça · **[339]** Mulheres em Apuros (viúvas) ·
  **[158]/[425]** Teologia do Aconselhamento Cristão · **[421]** O Pastor e o Aconselhamento

## Pendente (precisa de aprovação do William)
1. **Vol VIII** — converter o `.md` em EPUB e subir ao app (escrita externa →
   precisa de ok). É o único jeito de ele ler "A Dor da Perda" no celular.
2. **Manual Bíblico de Perguntas Difíceis e Polêmicas** — mesmo caso, não está no app.
3. **Coletâneas Vol III, IV, VI (na KB como "Coletâneas Vol III/IV/VI")** — os
   nomes na KB são genéricos; o app tem II, III, IV, V, VI, VII? conferir um a um.

## Regra durável
Antes de citar qualquer livro como leitura disponível: **conferir o bookId no
app**. A KB diz o que o acervo *tem*; o BookOrbit diz o que ele *pode ler no
celular*. São conjuntos diferentes em 40% dos casos.
