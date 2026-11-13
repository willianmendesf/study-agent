# 2026-11-13 — Lote de livros enviado ao BookOrbit (William mandou pelo Telegram)

**Pedido:** "Sobe esses livros no bookorbit" — 20 arquivos chegaram pelo Telegram
em `/tmp/picoclaw_media/` (13 PDFs + 7 EPUBs).

## O que foi feito

1. **Identifiquei cada arquivo antes de nomear** (regra de 2026-11-13: nunca nomear
   por presunção). EPUB → `dc:title`/`dc:creator` do OPF. PDF com camada de texto →
   `pdftotext`. PDF sem camada → `pdftoppm` + `tesseract -l por` em 2-3 páginas.
2. **Upload via API HTTP** (`POST /api/v1/libraries/1/upload?folderId=1`), sessão
   única (1 login), nome de arquivo `Autor - Título.ext` para o BookOrbit montar
   autor/título pelo nome (o `orbit-upload.py` original mandava só o autor como
   nome do arquivo e o app ficava com `_unorganized.pdf`).

## Resultado: 18 enviados · 1 já existia · 0 falhas

| # | Obra | Formato | bookId |
|---|---|---|---|
| 1 | Bryan Chapell — *Pregação Cristocêntrica* | epub | 1878 |
| 2 | Bryan Chapell — *Adoração Cristocêntrica* | epub | **já existia (id 7)** |
| 3 | Paulo Wesley — *O Segredo da Leitura Dinâmica* | epub | 1880 |
| 4 | Chan Hu Wang — *Leitura Dinâmica* | epub | 1882 |
| 5 | Ricardo Collins — *Leitura Dinâmica: Segredos…* | epub | 1883 |
| 6 | Fernando Costa — *Leitura Dinâmica para Iniciantes* | epub | 1885 |
| 7 | Jay E. Adams — *A Theology of Christian Counseling* | epub | 1887 |
| 8 | Jay E. Adams — *The Christian Counselor's Manual* | epub | 1890 |
| 9 | Jay E. Adams — *How to Help People Change* | epub | 1891 |
| 10 | Fee & Stuart — *Entendes o que lês?* (3ª ed., Vida Nova 2011) | pdf | 1892 |
| 11 | Fee & Stuart — *Como ler a Bíblia livro por livro* (Vida Nova 2013) | pdf | 1893 |
| 12 | Sidney Greidanus — *Pregando Cristo a partir do AT* (Cultura Cristã 2006) | pdf | 1894 |
| 13 | Adler & Van Doren — *Como Ler Livros* | pdf | 1895 |
| 14 | Jennings & Morea — *Leitura Super Rápida* (2013) | pdf | 1896 |
| 15 | Alberto Dell'Isola — *Treinamento Prático em Leitura Dinâmica* (2010) | pdf | 1898 |
| 16 | Van Groningen — *O Progresso da Revelação no AT* (Cultura Cristã 2006) | pdf | 1899 |
| 17 | Van Groningen — *O Reino, a Aliança e o Mediador* Vol 1 (658 p.) | pdf | 1900 |
| 18 | Van Groningen — *O Reino, a Aliança e o Mediador* Vol 2 (525 p.) | pdf | 1901 |
| 19 | Van Groningen — *O Reino, a Aliança e o Mediador* Vol 3 (451 p.) | pdf | 1902 |

**BookOrbit: 1.129 → 1.147 livros** (pdf 556→566, epub 544→552).

## 🐛 Arquivos descartados (medido, não suposto)

- `14960a5e_file_32` e `9dbabb3c_file_34.pdf` são **byte-a-byte idênticos**
  (md5 `fcc9ce2b…`) e **PDF corrompido**: `pdfinfo` não lê, `pdftotext` vazio,
  pypdf → `PdfStreamError: Stream has ended unexpectedly / EOF marker not found`.
  É uma versão parcial (10 páginas, capa + sumário) de *Como ler a Bíblia livro
  por livro* — o arquivo bom (`9480d61e_file_36.pdf`, 532 páginas) foi o enviado.
  **Não subi arquivo quebrado no app.**
- `eccb847d_file_37.pdf` (105 p., sem camada de texto) — OCR da capa/página 2
  confirmou: *O Progresso da Revelação no Antigo Testamento*, Van Groningen.

## Armadilha técnica registrada

`orbit-upload.py` usa `filename = autor or ebook.stem` — ou seja, o **nome do
arquivo no app vira só o autor**. Resultado: 3 PDFs diferentes viraram
`_unorganized.pdf` e o 2º em diante deu **409 "já existe"**. Por isso, neste lote,
fiz um upload nomeado (`Autor - Título.ext`) direto na API, sem mudar o script
canônico (mexer nele afeta o cron de reenvio — fica para quando o William pedir).

## Script usado
`/tmp/upload_lote_orbit.py` (efêmero). Reaproveitável se o William quiser
promover para `scripts/` com lista via YAML.
