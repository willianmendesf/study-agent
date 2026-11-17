# 2026-11-17 — Leeman "Authority" não abria no BookOrbit (OPF inválido) + série Sproul

## Sintoma reportado pelo William
Print do app: "Falha ao carregar o livro — XML parsing error: 9798874905637_EPUB.opf
... error on line 4 at column 14: Namespace prefix dc on title is not defined ...
Namespace prefix dc on creator is not defined".

## Causa raiz (2 bugs no MESMO script)
`scripts/renomear-metadata-ebook.py` (criado hoje, 11:51) reescrevia:

    <dc:title xmlns:dc="http://purl.org/dc/elements/1.1/">Texto</dc:title>

como

    <dc:title>Novo</dc:title>

ou seja, **descartava a declaração de namespace que estava no próprio elemento**.
No EPUB do Leeman (produzido por Sigil) o `<package>` NÃO declara `xmlns:dc` — cada
elemento `dc:*` declara o seu. Resultado: XML inválido → o leitor do BookOrbit não
abre o livro. Nos EPUBs do Sproul (calibre) o `xmlns:dc` está no `<metadata>`, por
isso os 20 volumes subiram sem problema.

**Bug 2 (silencioso, descoberto na verificação):** quando eu preservei os atributos,
o livro subiu com `authors: []` e caiu em `/books/Unknown Author/`. O BookOrbit só
reconhece `<dc:creator>` LIMPO — atributo (`id="creator01"`, `xmlns:dc=...`) no
elemento faz o parser dele ignorar o autor.

## Correção (no script, na causa)
- `_garantir_ns_dc()` — injeta `xmlns:dc` no `<package>` se faltar.
- `_trocar_tag()` — troca o conteúdo **e emite a tag limpa** (`<dc:title>`, sem
  atributos), porque o namespace agora está na raiz.
- `_escapar()` — escapa `&`, `<`, `>` no valor.
- **Validação obrigatória:** `ET.fromstring()` no OPF reescrito; se der erro, aborta
  em vez de gravar EPUB quebrado. Testado contra 19/19 EPUBs do Sproul → 0 ruins.

## Estado no BookOrbit
| bookId | título | situação |
|---|---|---|
| 2019 | "Autoridade: Como o Governo Piedoso..." | **LIXO** — OPF inválido, não abre |
| 2021 | "Autoridade - ... (ed. original em ingles)" | **LIXO** — abre, mas `authors=[]` → /Unknown Author/ |
| 2022 | "Autoridade - Como o Governo Piedoso Protege os Vulneraveis (ed. original em ingles)" | **BOM** — abre, autor Jonathan Leeman |

A conta `study-agent` **não consegue apagar**: `DELETE /api/v1/books/<id>` → **404**
(rota inexistente para este token) e `PATCH .../metadata` → 403 `library_edit_metadata`.
→ **Pendente do William apagar 2019 e 2021 no app.**

## Série Sproul "Questões Cruciais" — 20 volumes (confirmado no ar)
BookIds **1999–2018 + 2020**, todos com `authors` preenchido (verificado um a um pela
API, 20/20 OK). `.md` em `data/biblioteca/teologia-sistematica/`, índice em
`data/estudos/notas/biblioteca-sproul/01-serie-questoes-cruciais.md`.

## Regra durável
**Reescrita de metadado de EPUB não pode descartar atributos de namespace.** Sempre
declarar `xmlns:dc` no `<package>` e validar o OPF com um parser XML antes de subir.
E, ao contrário: o BookOrbit **exige** `<dc:creator>` sem atributos para reconhecer o
autor. As duas coisas juntas: namespace na raiz, tag do elemento limpa.
