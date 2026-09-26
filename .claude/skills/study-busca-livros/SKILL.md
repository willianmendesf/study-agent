---
name: study-busca-livros
description: "Busca de texto completo nos livros da biblioteca (data/estudos/ e data/biblioteca/) em segundos, devolvendo livro + linhas exatas + trecho para citar, e confirma se uma citação literal existe no livro. É o PRIMEIRO passo da Regra 9 para qualquer pergunta de conteúdo, citação ou 'em qual livro fala de X?'. Respeita o escopo por tags do especialista (Regra 8). Só stdlib Python; sem instalação, sem LLM, sem rede."
---

# Busca nos livros — índice de texto completo (SQLite FTS5)

**Tipo:** utility que a IA roda via Bash (Regra 4: nada roda sozinho — quem executa é você).
Resolve o problema de ler livros: o acervo passa de **800 MB de markdown** (centenas de livros, vários
acima de 10 MB); `Grep` recursivo leva minutos e devolve arquivos inteiros. Esta skill mantém um
índice derivado em `data/.indice/livros.db` e devolve, em segundos, **só os trechos certos com a
fonte exata** (arquivo + linhas), que é o que a Regra 9 exige para citar.

## Quando usar (ordem obrigatória na Regra 9)

1. **Toda pergunta de conteúdo de estudo**, todo pedido de citação, "em qual livro fala de X?",
   "o que o autor Y diz sobre Z?" → **`buscar.py` primeiro**, antes de qualquer `Grep`/`Read`.
2. Resposta com **citação literal** (aspas) → confirme com `buscar.py --verificar` antes de mostrar.
3. Depois de achar o trecho: `Read` do arquivo com `offset`/`limit` ao redor das linhas devolvidas —
   **nunca o livro inteiro** (trava de tamanho da Regra 9).
4. Nada achado com termos simples → tente sinônimos/`termo*` (prefixo); se o vocabulário do livro for
   muito diferente do da pergunta, use `study-rag-local` (semântico). Se ainda assim nada: diga ao
   usuário que **não há material** (Regra 9.4) — não preencha de cabeça.

## Buscar

```bash
python3 .claude/skills/study-busca-livros/buscar.py "justificação pela fé"
python3 .claude/skills/study-busca-livros/buscar.py justific* fé --tags teologia,soteriologia -k 10
python3 .claude/skills/study-busca-livros/buscar.py --frase "somente pela fé"
python3 .claude/skills/study-busca-livros/buscar.py graça obras --json
```

| Opção | Efeito |
|---|---|
| _(padrão)_ | todos os termos (E); sem distinção de **acento/caixa**; stopwords (`de`, `pela`…) ignoradas; se nenhum trecho tiver todos os termos, cai para OU e avisa "aproximado" |
| `termo*` | prefixo (`justific*` → justificação, justificado…) |
| `--exato` | não reduz os termos ao radical (por padrão `justificar` já acha `justificação`) |
| `--frase "…"` | frase exata (termos adjacentes, na ordem; mantém stopwords) |
| `--ou` | qualquer termo |
| `--tags a,b` | **escopo do especialista** (Regra 8): só livros cujas tags cruzam com `a` **ou** `b`. Passe as `tags_do_dominio` do especialista ativo. Sem `--tags` = pool inteiro (inclui livros sem tag) |
| `--arquivo x` | só arquivos cujo caminho contém `x` |
| `-k N` / `--max-por-livro N` | nº de resultados (8) / máximo por livro (2, para diversificar) |
| `--json` | saída estruturada (`arquivo`, `titulo`, `tags`, `linha_inicio`, `linha_fim`, `secao`, `trecho`) |

Cada resultado traz **título — `data/<arquivo>:<linha_ini>-<linha_fim>` · seção · tags** e o trecho com
os termos entre «». Cite assim: `— Fonte: data/estudos/livros/…/livro.md, linhas 120-134, seção "…"`.
Códigos de saída: `0` achou · `3` nada achado · `2` uso/índice ausente · `1` erro.

## Verificar citação literal (anti-alucinação, Regra 9.3)

```bash
python3 .claude/skills/study-busca-livros/buscar.py --verificar "texto exato que vou colocar entre aspas"
python3 .claude/skills/study-busca-livros/buscar.py --verificar "…" --arquivo nome-do-livro
```

- `CONFIRMADA (EXATA)` → pode usar entre aspas, citando o arquivo e a linha informados.
- `CONFIRMADA (APROXIMADA — difere em caixa/acentos)` → use o texto **como está no livro** (confira o
  trecho impresso), não a sua versão.
- `NÃO CONFIRMADA` → **não use aspas**: apresente como paráfrase/resumo. Livros vindos de OCR têm
  ruído (`T E O L O G IA`, palavras coladas), então uma citação real pode falhar; nesse caso abra o
  trecho com `Read` (offset/limit) e cite o que de fato está lá.
- Hifenização de fim de linha (`defen-`/`dida`) é tratada automaticamente.

## Indexar (a IA roda; o usuário nunca precisa)

```bash
python3 .claude/skills/study-busca-livros/indexar.py            # incremental (só o que mudou)
python3 .claude/skills/study-busca-livros/indexar.py --refazer  # do zero (~36 min no acervo todo, disco lento)
python3 .claude/skills/study-busca-livros/buscar.py --info      # estado do índice
```

- **Automático na busca:** `buscar.py` confere os arquivos antes de cada consulta e reindexa sozinho
  até 25 arquivos novos/alterados/removidos (ou se um KB mudou de tags). Acima disso avisa para rodar
  `indexar.py`.
- **Bibliotecário:** após converter/adicionar/mover/apagar livros (`study-gerenciar-bibliotecas`,
  `book-pipeline`, `book-to-skill`), rode `indexar.py` no mesmo turno.
- Indexa `.md`/`.txt` de `data/estudos/` e `data/biblioteca/`; ignora pastas ocultas, `.processing`,
  `_tools`. **Tags** vêm dos `kb-*.yaml` (`tags` + `materiais[].caminho_md`); livro fora de qualquer KB
  fica **sem tag** e só aparece quando não há especialista ativo (Regra 8).
- Trechos de ~1,4 KB com **faixa de linhas** e a última seção `#`; o índice guarda o texto, então
  ocupa espaço próprio (ver `--info`). É **derivado e descartável**: apague `data/.indice/` quando
  quiser — nunca é fonte de verdade e **não vai para o git** (`data/.gitignore`).

## Limites conhecidos

- Léxico, não semântico: acha as **palavras** (com acento/caixa/prefixo flexíveis), não o sentido.
  Para "trecho sobre X" com vocabulário diferente → `study-rag-local`.
- Radical **leve, sem dicionário** (tira sufixos comuns do português): `justificar`, `justificado` e
  `justificação` se encontram (`justific*`), e o cabeçalho mostra as expansões aplicadas. Pode trazer
  parentes indesejados (`obras` → `obra*`); nesse caso use `--exato`. Termos curtos (radical < 4 letras,
  como `deus`) e `--frase` nunca expandem.
- Frase que atravessa o limite entre dois trechos pode não casar em `--frase`; use `--verificar`
  (lê o arquivo) ou busque os termos em modo E.
- OCR com **letras espaçadas** (`T E O L O G IA`) é corrigido **na origem**: `.claude/scripts/normalizar_md.py`
  roda dentro do `book-pipeline` (e do `ocr-pdf.py`) em toda conversão, e a Regra 2 manda rodá-lo após conversão
  manual. Livros que já estavam no disco com o defeito são normalizados **no índice** como rede de segurança
  (mesma função), mas o arquivo continua espaçado, então `--verificar` de um trecho assim não casa: corrija o
  arquivo com `normalizar_md.py <arquivo|pasta>` (use `--dry-run` antes). Só letras latinas: grego/hebraico ficam
  intactos. Outros defeitos de OCR (letras trocadas, palavras coladas, palavra de 2 letras isolada) não são corrigidos.
- **Desempenho medido** (acervo de ~1.000 arquivos / 540 mil trechos, VM com disco lento): indexação inicial
  ~36 min e ~1,8 GB (uma vez; depois é incremental); consulta ~1,5 s com cache quente e até ~9 s a frio, contra
  mais de 150 s de `grep -r` nos mesmos livros. Em disco SSD é bem mais rápido.
- `--verificar` de uma citação **inexistente** é o caso lento (~30 s medidos): ele precisa ler os livros
  candidatos inteiros para provar que o texto não está lá. Com `--arquivo <livro>` é imediato.
- Livro que **nenhum `kb-*.yaml` lista** fica sem tag: acha-se sem `--tags`, mas o filtro por especialista o
  esconde. O bibliotecário deve catalogá-lo (Regra 8) — `study-lint` acusa "livros sem KB".

## Relacionadas

- `CLAUDE.md` Regra 9 (ancorar e citar) e Regra 8 (escopo por tags).
- `study-rag-local` — semântico (complementar, opcional, dependências pesadas).
- `study-gerenciar-bibliotecas` — mantém o pool/KBs que este índice lê.
