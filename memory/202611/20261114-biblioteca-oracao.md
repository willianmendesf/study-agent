# 2026-11-14 — Biblioteca de oração (18 obras) + 3 bugs no caminho

## Pedido
1. "Busque livros de e sobre oração" (chegaram 4 arquivos anexados que se perderam).
2. "Baixe o suba no orbit".

## Resultado
18 obras PT-BR: `.md` em `data/biblioteca/`, catalogadas nas KBs, no BookOrbit (1.147 → 1.172).
Índice: `data/estudos/notas/biblioteca-oracao/01-obras-adquiridas.md` · memo `memos/2jHRTx9MvikddAtSwXtAYv`.
Commit `c4f5dc4` (data) pushado. Lint: 0 erro novo.

## Bugs corrigidos
1. `epub2md.py`: `get_items_of_type(ITEM_DOCUMENT)` = [] → devolvia "" sem exceção →
   "saída curta demais" → livro perdido. Guarda: cai no `_epub_zip_fallback`.
2. `_epub_zip_fallback`: `sort()` alfabético punha `main-10` antes de `main-2`.
   Chave natural por números.
3. `orbit-upload.py` fazia login por arquivo → 429 no 4º. Novo `orbit-upload-lote.py`:
   1 login por fila, backoff, nome `"Autor - Titulo.ext"`.

## Armadilhas
- **Cron de reenvio ao Orbit apaga o `_incoming` após subir.** Trabalhar em `/tmp/<lote>/`.
- **Anexos do Telegram (`media://`) expiram em 30 min** e ficam irrecuperáveis (`unknown ref`).
- `z-lib.gd` ativo hoje; 8 contas × 10 = 80 downloads disponíveis (gastei ~40).
- Descartados por título enganoso: *Oração para Desaparecer* (ficção), Joseph Murphy (Novo Pensamento).
