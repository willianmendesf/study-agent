# 2026-11-28 — Edersheim: janela do BookOrbit/Memos e fila de upload automática

## O que o William informou (03:57 BRT)

> "O Book Orbit inicia as 5am e desliga as 23pm, tanto ele como o memos."

Isso explica as falhas noturnas de upload e de postagem no Memos: eu estava
tentando às 03:40, quando os dois serviços estão dormindo.

## O que foi feito

1. **Crontab estreitado para a janela real dos serviços.**
   - `reenvio-orbit-automatico.sh`: era `*/15 * * * *` (24 h) → agora
     `*/15 8-23,0-2 * * *` (= 05:00–23:00 BRT). Antes, fora da janela, cada
     execução só gastava timeout.
   - Backup do crontab anterior em `/tmp/cron-backup-20261128.txt`.

2. **Fila própria do Edersheim, fora de `_incoming/`.**
   - `~/ebooks-gerados/edersheim-pendente/` — 17 arquivos (15 EPUB + 2 PDF).
   - **Por que fora de `_incoming/`:** o `reenvio-orbit-automatico.sh` apaga o
     arquivo local depois do upload confirmado, e podia "roubar" o original
     antes da conversão (mesma armadilha de 2026-11-14).

3. **`scripts/subir-edersheim.sh`** (novo, chmod 755):
   - testa `GET /api/v1/health`; app dormindo → sai 0 sem tocar em nada;
   - app no ar → `orbit-upload-lote.py --dir <fila>` (1 login para a fila,
     backoff 429/401, nome `"Autor - Titulo.ext"`);
   - só apaga o local depois do upload confirmado;
   - notifica o Telegram uma vez, quando a fila zera.
   - cron: `*/15 8-23,0-2 * * *`.

4. **Metadado dos EPUBs limpo.** O `dc:title` de todos os 15 EPUBs ainda
   carregava o sufixo `(ES)` / `(EN)` que eu usava só para me organizar —
   isso ia aparecer no app. Removido (15/15). Zip e todos os XML validados:
   **0 ruins** (a lição do OPF da Crossway, 2026-11-17).

5. **Os 2 PDFs vão como PDF**, não convertidos:
   - *Historia de la Biblia AT – Vol 07* (234 p., camada de texto OK, 2.584
     chars nas 3 primeiras páginas);
   - *La vida y los tiempos de Jesus el Mesias* (856 p., digitalização — só 22
     chars nas 3 primeiras páginas, precisa OCR de ~40 min). Não vale OCR só
     para subir: o `/Title` e `/Author` já estão corretos no PDF.

6. **Nota atualizada** (`data/estudos/notas/biblioteca-edersheim/01-...md`) com
   a seção de envio/janela. Lint: 0 erro novo. Commits `e1312e3` (data) e
   `5fd0eab` (repo), pushados.

## Armadilha registrada (nova)

`orbit-upload-lote.py` faz `autor=nome` e o `upload()` monta
`f"{autor} - {titulo}"` **só quando os dois estão presentes**; com `titulo=None`
usa `nome = autor` (= o stem inteiro). Funciona porque o stem já é
`"Autor - Titulo"`, mas é frágil: se o stem não seguir esse formato, o livro
entra com autor errado. Para filas novas, preferir `orbit-subir-livro.py`
(título e autor explícitos).

## Pendente

- BookOrbit estava **offline às 03:58** (health 000). Os 17 sobem sozinhos a
  partir das 05:00 BRT.
- Memos: nota do Edersheim **não postada** (fora da janela). O
  `scripts/postar-fichas-memos.py` tenta IPv6 → IPv4 → hostname; rodar dentro
  da janela.
