---
name: study-rag-local
description: "Indexação e busca semântica local (ChromaDB + sentence-transformers) para livros grandes da biblioteca — evita ler um arquivo de 10+ MB inteiro. A IA roda index.py/search.py via Bash quando precisa; não é automático (Regra 4). Use quando um material relevante for grande (acima de ~150-200KB) ou quando o Grep simples não achar o trecho certo por vocabulário diferente."
---

# RAG Local — indexação e busca semântica de verdade

**Tipo:** utility, invocada pela IA via Bash — **não** é uma camada automática/invisível (Regra 4 do
`CLAUDE.md`: nenhuma skill roda sozinha sem a IA de fato executar o passo).

Existe pra resolver o caso que a trava de tamanho da Regra 9 identifica: alguns livros da biblioteca
passam de 10 MB (~3 milhões de tokens se lidos inteiros). Nesses casos, `Grep` acha uma palavra exata,
mas não "o trecho que fala sobre X" quando o vocabulário do livro é diferente do da pergunta. RAG local
resolve isso: quebra o livro em pedaços, gera embeddings, e busca por **significado**, devolvendo só o
trecho relevante + a linha exata pra citar (Regra 9) ou fazer um `Read` pontual se precisar de mais
contexto ao redor.

## Setup (uma vez, gated — nunca assumido)

```bash
bash .claude/skills/study-rag-local/setup.sh
```

Instala `chromadb` + `sentence-transformers` (modelo `all-MiniLM-L6-v2`, ~90MB, roda em CPU) via
`pip install --user`. Se o ambiente for "externally managed" (Debian/Ubuntu), o script tenta
`--break-system-packages` automaticamente. Sem essas duas libs, `index.py`/`search.py` avisam e param
— nunca travam a sessão nem fingem que funcionou.

## Indexar

```bash
python3 .claude/skills/study-rag-local/index.py data/estudos/livros --min-size-kb 500
# ou um arquivo específico:
python3 .claude/skills/study-rag-local/index.py data/estudos/livros/<pasta>/<arquivo>.md --min-size-kb 0
```

- Quebra por heading markdown (`#`..`######`); blocos ainda grandes (ou sem heading nenhum — comum em
  OCR) são sub-quebrados por tamanho fixo (~1500 caracteres) com overlap de 150 caracteres, pra não
  cortar uma frase ao meio na fronteira do chunk.
- Já indexado? Pula por padrão — use `--force` pra reindexar (ex.: depois de reprocessar o arquivo).
- Guarda em `data/rag/` (ChromaDB persistente, coleção `biblioteca`), com metadados `arquivo`,
  `titulo`, `linha_inicio`, `linha_fim` por chunk — o suficiente pra citar a fonte exata.
- **Importante:** a coleção é criada com `hnsw:space=cosine` (sentence-transformers é calibrado pra
  similaridade de cosseno — o padrão do ChromaDB, distância L2, rankeia errado). Se você já tinha uma
  coleção antiga sem essa config, apague `data/rag/` e reindexe.

## Buscar

```bash
python3 .claude/skills/study-rag-local/search.py "pergunta em linguagem natural" --top-k 5
```

Devolve, por resultado: arquivo, faixa de linha, distância (menor = mais parecido), e o trecho. Use
`--json` pra saída estruturada, `--arquivo <caminho>` pra restringir a busca a um livro só.

## Quando usar (a IA decide, não é automático)

1. Pergunta de conteúdo cujo material relevante é grande (>150-200KB — mesmo limiar da trava de
   tamanho, Regra 9) e a resposta não está óbvia por título/pasta.
2. `Grep` simples não achou nada relevante (vocabulário da pergunta ≠ vocabulário do livro).
3. Depois de rodar `search.py`, se o trecho devolvido não for suficiente, faça `Read` do arquivo
   original com `offset`/`limit` ao redor da `linha_inicio`/`linha_fim` retornada — nunca o arquivo
   inteiro.

Se o material é pequeno (abaixo do limiar), `Grep`/`Read` direto continuam sendo mais simples — RAG
local é pra quando o tamanho do arquivo torna isso inviável.

## Manutenção

```bash
# reindexar um livro específico depois de corrigir a conversão
python3 index.py data/estudos/livros/<pasta>/<arquivo>.md --force --min-size-kb 0

# apagar o índice inteiro e recomeçar (ex.: mudou o modelo de embedding)
rm -rf data/rag/
```

Não existe comando de "stats"/"remover"/"rebuild paralelo" — isso era promessa de uma versão anterior
desta skill que nunca foi implementada. O que existe é `index.py` e `search.py`, chamados via Bash.

## Referências
- `CLAUDE.md` Regra 9 — trava de tamanho antes de `Read`, e por que RAG local existe
- `study-gerenciar-bibliotecas` — cataloga/tagueia o pool; RAG local busca *dentro* de um arquivo já
  catalogado, não substitui a tag
