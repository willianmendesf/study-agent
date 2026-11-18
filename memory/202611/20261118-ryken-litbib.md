# 2026-11-18 — Ryken em português: medido de novo, não existe; catálogo ampliado

## Pedido do William

> "veja se você acha esses 3 livros: Leland Ryken, *A Bíblia como você nunca leu*
> (Cultura Cristã, 2026); *Formas literárias da Bíblia* (2017); *Para ler a Bíblia
> como literatura* (2017). do mesmo autor, baixe e suba no bookorbit, em portugues,
> prioridade."
>
> "Sim, sempre amplie o catálogo, tinha uma rotina e já regras para isso."

## Resposta 1 — as 3 em PT NÃO existem (reconfirmado, 8 contas)

| query | resultado |
|---|---|
| `Leland Ryken` lang=portuguese (20) | só *Santos no Mundo* (7 edições) + obras do **Philip Graham Ryken** (irmão) |
| `A Bíblia como você nunca leu` | série homônima de **A. L. Defide** (*"A Bíblia como você nunca viu"*) + Pablo Marçal — não é Ryken |
| `Formas literárias da Bíblia` | nada |
| `Para ler a Bíblia como literatura` | nada (Fee, MacArthur, Francine Prose) |
| ISBN 9788576226468 · 6559894517 | zero |
| Libgen (biblio-mcp) + Anna's Archive | zero em PT; só os originais em inglês |

**Conclusão:** compra (itens #187.1–#187.3). O acervo tem os 3 **originais em
inglês** (bookIds 2023/2025/2026), que servem para estudo, não para citação PT.

## Resposta 2 — o que foi adquirido no lugar (PT-BR, mesmo método)

Três obras de análise literária da Bíblia em português, medidas como disponíveis
e ausentes do acervo:

| obra | autor | editora | `.md` |
|---|---|---|---|
| O Código dos Códigos: a Bíblia e a Literatura | Northrop Frye | Boitempo 2004 | 777 KB · 3.956 linhas |
| A Bíblia como Literatura | John B. Gabel & Charles B. Wheeler | Loyola 2003 | 788 KB · 10.885 linhas |
| As Formas Literárias do Novo Testamento | Klaus Berger | Loyola 1998 (orig. *Formgeschichte des Neuen Testaments*, 1984) | 1.255 KB · 17.704 linhas |

→ `data/biblioteca/exegese-hermeneutica/`, `kb-exegese-hermeneutica` 52 → **55**.

## Bônus — *Santos no Mundo* (Ryken, PT-BR)

A busca por Ryken em PT devolvia 7 edições deste livro e o acervo **não tinha
nenhuma**. EPUB da Editora Fiel (2016) → `data/biblioteca/teologia/Santos-no-Mundo-Ryken.md`
(681 KB · 6.573 linhas), `kb-teologia` 50 → **51**.

## BookOrbit — 4 novos

| bookId | título | autor |
|---|---|---|
| 2032 | O Código dos Códigos | Northrop Frye, Flávio Aguiar |
| 2034 | A Bíblia como Literatura | John B. Gabel, Charles B. Wheeler |
| 2036 | As Formas Literárias do Novo Testamento | Klaus Berger |
| 2038 | Santos no Mundo: Os puritanos como realmente eram | Leland Ryken |

## 🐛 Bug 1 — `upload()` mandava só o AUTOR como nome do arquivo

`scripts/orbit-upload.py`: `nome = autor or ebook.stem`. Resultado medido: os
bookIds **2030 "Gabel"** e **2031 "Berger"** subiram como livro **sem título e
sem autor** (o BookOrbit deriva título/autor do nome do arquivo quando o
metadado embutido não serve).

**Correção:** `upload(..., autor, titulo)` → `"Autor - Titulo.ext"`. O
`pipeline-aquisicao.py` passou a mandar `titulo=it["titulo"]`.

**Lixo no app (só o William apaga):** 2030 e 2031. A conta `study-agent` só tem
`library_upload` → `DELETE /api/v1/books/<id>` = 404, `PATCH /books/<id>/metadata`
= 403.

## 🐛 Bug 2 — o catalogador decide a pasta pela PASTA do arquivo

As 3 obras caíram em `literatura-mundial-classica/outros/` e na `kb-literatura`
(ficção!) porque o pipeline as baixou para lá. Movidas para
`exegese-hermeneutica/` e re-catalogadas na KB certa (com `yaml.safe_dump`
`width=4096`, senão o `caminho_md` quebra em duas linhas).

**Detalhe que quase passou:** o primeiro script criou uma chave `materiais` no
TOPO do YAML (fora de `knowledge_base_*`) — o lint não pega isso, mas a busca
não acharia. Corrigido inserindo dentro da lista certa.

## Catálogo de aquisição ampliado (`rodape-aquisicao.py`)

8 alvos novos, medidos com `ja_no_acervo` (não por suposição):

- **hermenêutica:** Gabel · Berger · Frye (os 3 acima; ficam no catálogo para o
  sensor reconhecer)
- **teologia-sistematica:** *Teologia Sistemática* de **Hodge** e de **Strong**
- **teologia-biblica:** *Teologia do Novo Testamento* de **Ladd** e *Teologia do
  Antigo Testamento* de **Eichrodt** (acervo só tinha Ladd em inglês e Eichrodt II)
- **preaching:** *Pregação e Pregadores* de **Lloyd-Jones** (acervo só em inglês)
- **metodologia:** *Metodologia do Trabalho Científico* de **Lakatos & Marconi**

`--listar` agora acusa: hermeneutica 6 · teologia-sistematica 6 · teologia-biblica 5
· preaching 6 · metodologia 4 (antes eram 3/4/3/5/3).

## Armadilhas operacionais do dia

1. **`zlib-api.py search` — a conta é POSICIONAL depois da query.** `search "X" zlib3 --limit 30`
   funciona; `search "X" --lang portuguese zlib3` dá `unrecognized arguments`.
2. **`zlib-api.py download` — `--dest` e `--ext` são opções, o resto é posicional:**
   `download <id> <hash> --dest /tmp/x --ext pdf`.
3. **BookOrbit devolve 429 no `/auth/login` a partir do 3º/4º login em minutos.**
   Precisa de espera de 30-60 s entre lotes. `orbit-subir-livro.py` (login por
   arquivo) estoura fácil; usar o script de lote com 1 login.
4. **`--lang portuguese` no z-library é furado** — devolve espanhol e inglês.
   Filtrar o campo `lang` na mão.
5. **`GET /api/v1/libraries/1` NÃO devolve a lista de livros** — só os metadados da
   biblioteca. Para buscar livro: `GET /api/v1/books/search?q=...`.
6. **`edit_file` derruba o bit de execução** de `.sh`/`.py` — conferir `chmod 755`.

## Estado

- Lint: **0 erros novos** (4 conhecidos no baseline, 1 aviso).
- Commits: `2828ffc` (data, 10 arquivos) · `3f8a538` (repo) — ambos pushados.
- Nota canônica atualizada: `data/estudos/notas/biblioteca-ryken/01-ryken-obras-pedidas.md`.
