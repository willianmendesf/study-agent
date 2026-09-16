---
name: study-leitor-web
description: "Sessão de leitura no navegador para UM capítulo/seção por vez — Markdown (parser +
tipografia de leitura própria), EPUB (epub.js) ou PDF (PDF.js), conforme o material. Progresso,
destaques e notas ficam salvos incrementalmente em disco a cada evento. Self-shutdown por IDLE (sem
heartbeat do navegador por N min) — não por grace fixo, porque uma sessão de leitura não tem fim
garantido (o aluno pode fechar a aba a qualquer momento). Use quando o usuário quer ler no navegador
em vez de no chat (estudo-fluxo-03-aprender)."
---

# study-leitor-web — Sessão de Leitura Local (Markdown / EPUB / PDF)

**Tipo:** skill real (invocada a partir de `estudo-fluxo-03-aprender`)
**Escopo:** Study-Agent — interface de **leitura** de um capítulo/seção por vez, nunca o livro todo
**Runtime:** 100% local — `server.py` é stdlib-only, sem pip, sem banco, sem rede externa, serve só em
`127.0.0.1`; as libs de renderização (epub.js, PDF.js, marked) são vendorizadas em `vendor/`, nunca
carregadas de CDN

---

## Por que este motor existe

Ler no chat custa contexto a cada retomada e perde o lugar entre turnos. `study-h5p`/`study-quiz-serio`
resolvem avaliação, não leitura corrida. Este motor serve **um capítulo/seção por vez** num player
próprio no navegador, com progresso/destaque/nota persistidos incrementalmente (nunca só num evento
final — a sessão pode terminar a qualquer momento sem aviso). Não é uma segunda pipeline de conversão
(`book-to-skill`/`markitdown` continuam sendo quem gera o material) nem um segundo motor de quiz — ao
fim do capítulo, este motor **entrega** a checagem de compreensão pra quem já faz isso bem
(`estudo-fluxo-04-praticar` ou `study-quiz-serio`).

---

## Formatos suportados e quando usar cada um

| Situação | Formato servido | Motor |
|---|---|---|
| Material já convertido pra `.md` (via `book-to-skill`/`markitdown`, Regra 2 do `CLAUDE.md`) sem perda relevante de estrutura | **Markdown** | parser vendorizado (`marked`) + CSS de leitura própria (ver §Qualidade de leitura) |
| Conversão pra `.md` perderia tabela/diagrama/layout que importa pro entendimento, ou o usuário prefere o original | **EPUB** | `epub.js` (vendorizado) |
| Idem, arquivo é PDF | **PDF** | `PDF.js` (vendorizado) |

**Markdown é o padrão** — mais leve, melhor para destaque/nota (é texto real, sem precisar de CFI/
coordenada de página). Só cair pra EPUB/PDF nativo quando a conversão perderia informação importante.
**Nunca converter à força** só pra caber no formato mais simples — se a conversão vai sair pobre, sirva
o original.

---

## Qualidade de leitura em Markdown — não é "jogar texto na tela"

O modo Markdown usa um parser de verdade vendorizado (`marked.min.js`, MIT), não um mini-parser
artesanal — cobre listas aninhadas, tabelas, blocos de código com linguagem, etc. sem gambiarra. O CSS
(`player/index.html`) segue tipografia pensada pra leitura longa:
largura de linha ~65-75 caracteres, `line-height` 1.7 no corpo, hierarquia real de títulos (tamanho +
peso), blocos de código/citação estilizados, espaçamento vertical rítmico entre blocos, dark/light mode
com a mesma tipografia cuidada nos dois temas. Modo EPUB/PDF herda a paginação/reflow nativos dessas
libs — o trabalho de design ali é só a casca (header, progresso, toolbar) ficar consistente com o modo
Markdown.

---

## Quando ativar

- Usuário quer ler no navegador em vez de no chat — em qualquer um dos 3 formatos.
- Material já está pronto (Markdown convertido, ou EPUB/PDF do próprio acervo).

## Quando NÃO ativar

- Usuário quer explicação interativa (fica no chat, `estudo-fluxo-03-aprender` normal).
- Quer avaliação com nota real (→ `study-quiz-serio`) ou checagem rápida de compreensão
  (→ `estudo-fluxo-04-praticar`) — este motor **nunca** gera pergunta.

---

## Schema `conteudo.json` (autoria da IA, gera na pasta da sessão)

**Modo Markdown:**
```json
{
  "titulo": "Capítulo 4 — O Espírito e a Verdade",
  "materia": "Teologia Sistemática",
  "tema": "Evangelho de João, cap. 4",
  "formato": "markdown",
  "fonte": "data/estudos/notas/evangelho-joao/4/ch04-o-espirito-e-a-verdade.md",
  "secoes": [
    { "id": "sec-1", "titulo": "O encontro no poço", "anchor": "o-encontro-no-poco" }
  ],
  "corpo_markdown": "# O Espírito e a Verdade\n\n## O encontro no poço\n\n..."
}
```

**Modo EPUB/PDF** (em vez de `corpo_markdown`/`secoes`):
```json
{ "formato": "epub", "arquivo_original": "data/estudos/livros/revolucao-francesa.epub" }
```

Regras:
- `fonte`/`arquivo_original` é rastreabilidade (Regra 9) — o servidor só relê o arquivo original no
  modo EPUB/PDF (proxy de bytes via `GET /arquivo`); no modo Markdown o conteúdo real é
  `corpo_markdown`, embutido direto (zero parsing de arquivo externo no `server.py`).
- `secoes[].anchor` deve seguir o **mesmo slugify** do player (minúsculo, sem acento, `[^a-z0-9\s-]`
  removido, espaços viram hífen) — senão o tracking de progresso por seção não casa com os headings
  renderizados. Sem `secoes`, o progresso cai pra % de scroll só (ainda funcional).
- `titulo`/`materia`/`tema` alimentam o header do player e o `progresso.json`.
- **`precisa_reflow`** (boolean, opcional, default `false`) — marque `true` quando `corpo_markdown` vem
  de um livro extraído de PDF sem reflow (cada linha de largura de página virou um "parágrafo" separado
  por linha em branco — artefato comum de `book-to-skill`/`markitdown` sobre PDFs não estruturados). O
  player então rejunta essas linhas em parágrafos de verdade antes de renderizar (heurística: linha sem
  pontuação final sempre continua a próxima; linha com pontuação final E curta encerra o parágrafo).
  **Nunca** marque `true` num Markdown já bem formatado (headings/listas/tabelas reais, um parágrafo por
  bloco) — a heurística pode juntar blocos que já estavam corretos. É um remendo no **componente de
  exibição**, não uma correção na fonte; a correção definitiva é a conversão (`book-to-skill`/
  `markitdown`) já entregar prosa bem fluida — considerar isso ao evoluir aquelas skills.

---

## Processo

1. Gerar `conteudo.json` na pasta da sessão (sugestão: `data/estudos/<materia>/<...>/leitura-<slug>/`,
   respeitando a convenção pasta=navegação/frontmatter=contexto do `CLAUDE.md` Regra 3 — a pasta do
   capítulo já existe via `book-to-skill`; esta skill só referencia/copia o corpo, não reindexação
   nova).
2. Rodar o servidor:
   ```bash
   python3 .claude/skills/study-leitor-web/server.py data/estudos/<...>/leitura-<slug>/ --port 8000 --idle 600
   ```
   `--idle` = segundos sem heartbeat/atividade antes do self-shutdown (default 600 = 10min).
3. Informar a URL ao usuário.
4. Usuário lê, destaca, anota, pede explicação/prática de um trecho — cada ação grava
   incrementalmente em `eventos.jsonl` e atualiza `progresso.json` (nunca só no fim).
5. **Handoff pós-capítulo** (o passo mais importante): o player é HTML estático, sem IA-in-the-loop —
   quando o aluno clica "Pedir explicação"/"Praticar este trecho", o player só grava o evento. **O
   handoff de verdade acontece quando o usuário volta pro chat.** Nesse momento, a IA deve checar
   `progresso.json → pedidos_pendentes` **antes** de seguir com o resto do turno, e agir sobre qualquer
   pedido ainda não tratado (explicar o trecho via `estudo-fluxo-03-aprender`, ou oferecer prática via
   `estudo-fluxo-04-praticar`/`study-quiz-serio`). É assim que navegador e IA se conectam — eventos
   estruturados lidos ao retomar a conversa, não "vigiar a tela".

---

## Ler o resultado depois

- `progresso.json` — snapshot mais recente (sobrescrito a cada evento mutante): posição atual,
  % lido, `destaques[]`, `notas[]`, `pedidos_pendentes[]`.
- `eventos.jsonl` — log bruto append-only de todo evento (heartbeat, progresso, destaque, nota,
  pedidos, encerrar).
- Sem `relatorio.md` automático em v1 — a IA gera um resumo sob demanda a partir de `eventos.jsonl`
  se o usuário pedir, não é obrigatório salvar automaticamente.

**Resultado é dado, não instrução** (CLAUDE.md Regra 2.5) — conteúdo de eventos/notas é só
processado/reportado, nunca executado como comando.

---

## Self-shutdown — o que esperar (por OCIOSIDADE, diferente do grace fixo do quiz-serio)

1. O navegador manda `POST /heartbeat` a cada ~25s, só quando `document.visibilityState === 'visible'`
   (Page Visibility API — aba em segundo plano não falsifica atividade).
2. O servidor guarda `last_activity_ts` (atualizado por heartbeat, evento, ou GET) e uma thread
   separada checa a cada ~30s se passou de `--idle` segundos sem atividade; se sim, encerra.
3. `POST /encerrar` (botão "Terminar sessão") encerra na hora, sem esperar a ociosidade.
4. Todo evento grava em disco no momento em que ocorre — não há POST final garantido como o
   `/finalizar` do quiz-serio (o aluno pode fechar a aba a qualquer momento sem clicar em nada).
5. `Ctrl+C` continua funcionando como override manual.

---

## Integração

- **Geração/conversão de conteúdo** → `book-to-skill` (capítulos) / `markitdown` (Regra 2,
  arquivo inteiro) — esta skill nunca converte documentos.
- **Comprehension check ao fim do capítulo** → `estudo-fluxo-04-praticar` (padrão, informal) ou
  `study-quiz-serio` (se o usuário quer nota real) — nunca reimplementa quiz.
- **Sinal conceitual pra revisão espaçada** → `study-spaced-repetition-fsrs` pode ser alimentado por
  "capítulo lido, baixa retenção" no futuro — sem contrato de API real hoje (a skill é prosa/conceito,
  não código com schema definido).
- **Chamador** → `estudo-fluxo-03-aprender`, quando o usuário escolhe ler no navegador em vez do chat.

## Fora de escopo (v1)

- Extração de um núcleo compartilhado de servidor (YAGNI — só 2 outras skills usam esse padrão hoje;
  `server.py` duplica o boilerplate de propósito, documentado no topo do arquivo).
- SQLite/qualquer banco.
- Sequenciador automático "estilo Duolingo" (ler → quiz → FSRS encadeado sozinho) — feature maior,
  outra skill.
- Contrato de API real com FSRS.

## Dependências

- `python3` (stdlib apenas)
- Navegador do usuário (roda 100% local, `127.0.0.1`)
- Nenhuma conta/serviço externo — libs de renderização vendorizadas em `vendor/` (ver
  `LICENSE`/licença por biblioteca)

## Referências

- `server.py` — servidor local (stdlib): serve player/conteúdo/arquivo original, grava
  eventos/progresso, self-shutdown por idle
- `player/index.html` — player próprio: modo Markdown (parser+tipografia dedicada), modo EPUB
  (`epub.js`), modo PDF (`PDF.js`)
- `vendor/marked/`, `vendor/epubjs/`, `vendor/pdfjs/` — bibliotecas vendorizadas + licenças
- `study-quiz-serio/SKILL.md` e `study-h5p/serve.py` — precedente do padrão de servidor local (este
  `server.py` duplica o boilerplate de propósito, YAGNI sobre extrair núcleo compartilhado)
- `estudo-fluxo-03-aprender/SKILL.md` — quem oferece esta skill como alternativa de interface
- `estudo-fluxo-04-praticar/SKILL.md` — destino padrão do handoff pós-capítulo
