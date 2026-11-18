# Rodada de ficção — 2026-11-18 (07:15 UTC / 04:15 BRT)

## Resultado

**0 livros baixados · 0 falhas · cota quase intacta (77 de 80).**

Rodou 2x: cron do sistema às 00:16 UTC e manual às 07:15 UTC (`--max 12`).
Mesmo resultado nas duas. **Quinta rodada seguida** (14, 15, 16, 17 e 18/11)
sem download — o **catálogo está 94/94 adquirido**. Não é cota, não é rede,
não é sensor quebrado.

## Provas (medidas, não presumidas)

1. `pipeline-aquisicao.py --status` → **94 no catálogo · 94 adquiridos · 0 pendentes**.
2. `pipeline-estado.json` → 101 itens: **101 com `caminho_md` existente e íntegro**
   (0 bytes nulos, 0 traceback, 0 arquivo ausente). Auditado campo por campo.
3. **z-library no ar:** `POST https://z-lib.gd/eapi/book/search` → HTTP 200 +
   `{"success":1}`. `cota por conta: zlib=7, zlib2..8=10` → **77 livres**.
4. Etapa 2b (libgen, sem cota): **exit 1** = rodou OK, nada a baixar
   (tradução do exit code: `0`=baixou · `1`=OK sem candidato · `124`=timeout ·
   outro=erro real). **Não é erro.**
5. Cota gasta hoje: **3 downloads** (00:16 UTC, antes da rodada das 07:15) —
   não pela rodada de ficção (0 baixados), e sim pela rodada teológica/outra.

## O que ficou pendente

1. **Catálogo é o teto** — 94/94. Para a rodada voltar a render:
   `estante-william.yaml` (58) + `lista-aquisicao.md` → `scripts/gerar-catalogo-ficcao.py`.
   **Gaps reais fora do catálogo, medidos hoje:**
   - ***O Nome da Rosa* (Umberto Eco)** — o acervo só tem *Como se faz uma tese*.
   - **A Escravidão na História (Gurowski)** — único título da estante sem
     correspondência no acervo (além das coletâneas de Eça).
   - **Obras de Eça de Queiroz vols I–III** (estante, físicos) — o catálogo já
     cobre as obras isoladas (A Capital, A Perdição, Almas & C.ª, O Mandarim,
     O Conde de Abranhos); as coletâneas são redundância.
   - *No Caminho de Swann* **já está** no acervo como
     `proust/Em-Busca-do-Tempo-Perdido-I-Marcel-Proust.md` (530 ocorrências de
     "Swann") — não é gap.
2. **BookOrbit voltou a responder em HTTP** — `GET /api/v1/health` na porta 80
   → 200 (`database: up`), `bookCount` = **1229**. A porta **3000 não existe
   mais** (`connection refused`); o `ORBIT_URL` dos scripts é
   `http://192.168.15.26` (porta 80), então está correto.
   **Mas o upload continua falhando:** os **16 arquivos** em `_incoming/`
   voltaram **409 "file already exists"** na execução das 07:15 UTC — ou seja,
   **já estão todos no Orbit** e o arquivo local só não foi apagado. O cron
   idempotente repete o 409 a cada 15 min.
   *Nota:* os PDFs dão 409 como `_unorganized.pdf` (o Orbit ignora o nome do
   multipart e usa o `/Title` do PDF — sem metadado, todos colidem).
3. **22 obras com `orbit != ok`** no estado (`falhou`/`pulado`/`pendente`) —
   herdado das rodadas antigas; os arquivos `.md` estão no acervo, o que falta é
   o ebook original subir. Reenviar exige o original, e a maioria já saiu de
   `_incoming/`.
4. **2 `.md` de bytes nulos** seguem no disco (órfãos; a KB aponta para os bons):
   `outros/anna-karenina-liev-tolstoi.md` (1,92 MB, 1.917.410 nulos) e
   `outros/idiota-fiodor-dostoievski.md` (1,64 MB, 1.642.640 nulos).
   **Apagar exige OK do William.**
5. ***O Caso Final de Sherlock Holmes* (1927)** — segue sem tradução PT-BR.

## Lint

`study-lint.py` → **exit 0 · 0 erro(s) novo(s)**, 4 conhecidos no baseline,
1 aviso pré-existente (`esp:mnemos:tags-sem-kb` — tags sem KB no pool:
anotacoes, schema, mapa, sintese-pessoal, catalogo-de-leitura,
philosophy-of-mind). Nada a corrigir.

## Diff em `data/`

Só o índice de busca (5 arquivos reindexados da nota do Ryken) — nenhuma
alteração de conteúdo do acervo.
