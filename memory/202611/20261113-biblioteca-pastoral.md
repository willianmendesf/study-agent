# 2026-11-13 01:10-01:40 BRT — Biblioteca pastoral (chamado, vocação, pastor x presbítero IPB)

## Pedido
William: "Busque livros para mim sobre chamado pastoral, vocação pastoral, e como saber
se sou chamado ao pastoreio, diferença entre pastores, presbíteros na visão da IPB"
Depois: "Catáloga, extrai desses livros e os suba no bookorbit"

## Entregue
13 obras -> data/biblioteca/pastoral/ (.md), kb-pastoral 21 -> 34 volumes,
BookOrbit 1.091 -> 1.104 livros. Nota 11 em data/estudos/notas/vocacao-ministerial/.

### Chamado / vocação
- Harvey, Eu sou chamado? (epub zlib 22058730) — o mais direto
- Peterson, A Vocação Espiritual do Pastor (pdf 16782271)
- Spurgeon, O chamado para o ministério (epub 12346642)
- Calvi, O preço do chamado pastoral (ENVIADO pelo William)
- CNBB, Vocação e Discernimento (ENVIADO pelo William) — católico, só o método serve
- Croft, A Família do Pastor (115963706)
- MacArthur, Redescobrindo o Ministério Pastoral (23242147)
- Piper & Carson, O Pastor como Mestre e o Mestre como Pastor (21871421)

### Governo / pastor x presbítero
- Westminster, Governo Presbiteriano (22059717)
- Reed, Governo Bíblico de Igreja (22060509)
- Bannerman, A Igreja de Cristo (14242118)
- Miller, O Presbítero Regente (22057757)
- Martins, O Pastor Auxiliar (116148741)

## Lacunas (não existem no z-library — 5 buscas)
Kléos César (Vocação, Ultimato) · W. H. Roberts (O Sistema Presbiteriano) ·
Thiselton (Called by God) · Peace (Vocation and the Ministry) · Allen (Discerning Your Call)

## A resposta constitucional (fonte primária)
Constituicao_da_IPB.md Art. 25 (3 ofícios), Art. 30 par. único (bispo/pastor/presbítero/
ancião = MESMO ofício, "funções diversas e não graus diferentes de dignidade"),
Art. 50-52 (presbítero tem autoridade IGUAL à dos ministros), Art. 31 (privativo do
ministro: sacramentos, bênção, casamento, liturgia), Art. 33 (4 designações).

## 🐛 5213 arquivos de data/ estavam root-owned (não willian)
Causa: algo rodou como root (provavelmente o índice `data/.indice/livros.db` de 2,4 GB
criado 2026-11-12 07:36, e o cache do bibliotecário). Sintomas: `buscar.py` ->
"attempt to write a readonly database"; lint -> 8 erros novos (relacionamentos.yaml
ilegível); kb-pastoral.yaml não gravava.
Correção: `sudo chown -R willian:willian data` (5213 -> 0). Lint voltou a 0 erro novo.
**Regra: se um script falhar com Permission denied em data/, checar `sudo find data -user root`
antes de suspeitar do código.**

## 🐛 epub2md falha em EPUB do Google Play (spine sem ordem de leitura)
O `epub_to_md` usa `get_items_of_type(ITEM_DOCUMENT)`; em EPUBs do Google Play
(o do Cleber Martins e o da Vanessa Calvi) isso devolve 0 chars. Solução: ler o
`content.opf`, pegar `itemref idref` na ordem do spine, mapear para href e extrair
na ordem. Reusar esse caminho quando o conversor devolver vazio.

## Armadilha do upload Orbit
1 login para a FILA (não por arquivo) + sleep 0.4 — 13/13 OK, zero 429.
Arquivo enviado ao Orbit não fica versionado; só o .md no data/.

## Lote 2 — 4 itens enviados pelo William (2026-11-13 ~04:40-05:10 BRT)

| arquivo | obra | pasta | KB | BookOrbit |
|---|---|---|---|---|
| 187a78a2_file_11.pdf | Duarte, *A Vocação para o Serviço ou o Serviço dos Vocacionados?* (FIDES REFORMATA XVI/2, 2011, 95-117) | revistas-fides | kb-pastoral 35 | bookId 1841 |
| 93d82b69_file_14.pdf | Lidório, *Vocacionados* (Betânia 2014) | pastoral | kb-pastoral 36 | 1842 |
| 719fd29c_file_13.epub | Lowe, *Construindo Pontes* | aconselhamento | kb-aconselhamento 40 | 1843 |
| 2cfe1cf2_file_12.pdf | **Nicolosi & Nicolosi, *Homossexualidade: um guia de orientação aos pais*** | sexual | kb-sexual 4 | 1845 |

BookOrbit: 1.104 → **1.108** livros.

### ARMADILHA: o PDF grande NÃO era o Julie Lowe
O William mandou o PDF de 12 MB junto com o EPUB do Lowe e eu presumi que fossem
o mesmo livro. **Não eram.** O PDF escaneado é o **Nicolosi** (121 páginas, capa
+ CIP da Shedd). Só descobri porque rodei OCR de 2 páginas de amostra e li o
título. **Regra: antes de nomear o arquivo de saída, OCR/extrair 1-2 páginas de
amostra e LER o título.** Nomear por presunção teria virado livro errado na
biblioteca (o mesmo tipo de bug do "A Revolução dos Animais com texto do 1984").

### OCR de PDF escaneado — o caminho que funciona nesta LXC
PDF do HP OfficeJet (`/Creator: hp officejetpro`) não tem camada de texto:
pypdf devolve 0 chars em TODAS as páginas, e o `pdf_to_md` do epub2md levanta
"provavelmente escaneado". Caminho:
1. `pdftoppm -r 200 -gray -png in.pdf /tmp/pg` (121 páginas em ~2 min)
2. `pytesseract.image_to_string(Image.open(p), lang="por")` por página
   (~2 s/página → 121 páginas ≈ 4 min)
3. limpar: remover linha que é só número (número de página), desfazer
   hifenização (`acon-` + nova linha + `selhamento`), juntar quebras no meio da
   frase, colapsar espaços.
Rodar em **background** (`nohup`) — o `exec` corta em 300 s e o total passa de
6 min. Resultado Nicolosi: 624 KB, 5.856 linhas. Tesseract com `por` instalado.

### EPUB do Google Play
O Lowe (epub) extraiu OK pelo `epub_to_md` normal (367 KB). O bug de spine
desordenado de ontem era só dos EPUBs de outra origem. Antes de reescrever o
conversor, **testar o caminho padrão primeiro**.

### Limpeza do .md do Lowe
O EPUB traz o sumário com números de página em linhas soltas (1, 2, 3... até
~48, e depois 96-151). Removidas as linhas que são só dígito + "Guide/Cover/
Table of contents" → 3.166 → 2.866 linhas.

## Lote 3 — 4 arquivos, mas 2 obras (Peterson) — 2026-11-13 ~05:15-05:40 BRT

| arquivo | o que é | destino |
|---|---|---|
| 94e475b3_file_16.pdf (17 MB, 290 p, Internet Archive) | Peterson, **O Pastor que Deus Usa** (Textus 2003; orig. *Five Smooth Stones*) | `pastoral/Peterson-O-Pastor-que-Deus-Usa.md` |
| d7fe483e_file_17.epub (1,7 MB, oficial Cultura Cristã 2022) | Peterson, **O pastor segundo Deus** (orig. *Working the Angles*) | `pastoral/Peterson-O-Pastor-Segundo-Deus.md` |
| 73900537_file_15.pdf (1 MB, Word→Foxit) | digitalização de *Working the Angles* com título **"Um pastor segundo o coração de Deus"** | DESCARTADO (duplicata) |
| 40ee6d36_file_18.pdf (868 KB, novaPDF) | mesma digitalização, outra tiragem | DESCARTADO (duplicata) |

kb-pastoral: 36 → **38 volumes**. BookOrbit: 1.108 → **1.110**.

### ARMADILHA: 4 arquivos ≠ 4 livros
Os dois PDFs de ~1 MB têm nomes de metadata diferentes ("Eugene Peterson - Um pastor
segundo o coração de Deus" e "Microsoft Word - Eugene Peterson - Um pastor segundo o
coração de Deus.doc"), mas são **a mesma obra**, e é a **mesma do EPUB** (título
editorial diferente: Textus chamou de *Um pastor segundo o coração de Deus*; Cultura
Cristã chamou de *O pastor segundo Deus*). Comparei assinatura de texto + tamanho:
342.725 (epub) vs 352.691 (pdf15) vs 355.386 (pdf18) — diferença é só o lixo do
Foxit/novaPDF no rodapé.
**Regra: quando chegam vários arquivos do mesmo autor, comparar assinatura de texto
(primeiras N palavras significativas) e tamanho ANTES de extrair. Título diferente no
metadata ≠ obra diferente.**

### Detalhe do EPUB oficial
O EPUB da Cultura Cristã tem `dc:identifier urn:isbn:9786559890699`, `publisher:
Cultura Cristã`, `date: 2022-01-26`, `language: pt-BR` — é edição comercial, não
digitalização. Vale como fonte canônica para citação (Regra 9).

### file_16 (Internet Archive) — o que precisou de limpeza
Tem camada de texto (513 KB extraídos), mas com: cabeçalho corrente em toda página
("o Pastor Que Deus Usa"), marca do Internet Archive ("Digitized by the Internet
Archive in 2014" + URL), e o OCR troca "Que" por "Qiie"/"Qjie". Limpezas aplicadas:
regex do cabeçalho (case-insensitive, tolerando as variantes), remoção das linhas do
archive.org, hifenização de fim de linha, colapso de espaços. Sobrou **1** ocorrência
de "pastor que Deus usa" — que é o título legítimo no corpo do texto (CIP), não
cabeçalho.
