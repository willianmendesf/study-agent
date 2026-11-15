# Rodada de ficção — 2026-11-15 (07:15 UTC / 04:15 BRT)

## Resultado

**0 livros baixados · 0 falhas · cota intacta (70 de 80 disponíveis: zlib=0, zlib2..8=10 cada).**

Não é falha de rede nem de sensor: o **catálogo está 94/94 adquirido**. A rodada
não tinha o que baixar. Mesma situação de 2026-11-14 — o gargalo agora é o
tamanho do catálogo, não o pipeline.

Rodou 2x (cron 00:16 UTC + manual 07:15 UTC), mesmo resultado.

## Prova de que a saturação é real (não sensor quebrado)

1. `pipeline-aquisicao.py --status` → **94 no catálogo · 94 adquiridos · 0 pendentes**.
2. `pipeline-estado.json` → 101 itens, 100% `adquirido`.
3. **Integridade arquivo a arquivo** (não confiei no campo do estado): 94/94 com
   arquivo existente, **0 bytes nulos, 0 traceback** de extração.
4. **z-library no ar:** `POST https://z-lib.gd/eapi/book/search` → `{"success":1}`
   (teste real de busca). Domínio ativo: `z-lib.gd`.
5. **Cota real:** 70 downloads livres → se fosse cota, seria 0.

## Bug corrigido neste turno (estado × arquivo)

4 obras da **migração de 2026-11-07** estavam com `md: "acervo:"` (vazio) — o
migrador não gravou o caminho:

| slug | arquivo real |
|---|---|
| `A-Capital-Eca-de-Queiroz` | `literatura-mundial-classica/portugues/A-Capital-Eca-de-Queiroz.md` |
| `Os-Misterios-de-Poe-Edgar-Allan-Poe` | `.../portugues/Poe-Edgar-Allan-Os-Misterios-de-Poe.md` |
| `A-volta-de-Sherlock-Holmes-Arthur-Conan-Doyle` | `.../portugues/Doyle-A-Volta-de-Sherlock-Holmes.md` |
| `O-ultimo-adeus-de-Sherlock-Holmes-Arthur-Conan-Doyle` | `.../portugues/Doyle-O-Ultimo-Adeus-de-Sherlock-Holmes.md` |

Os 4 arquivos estavam **íntegros** (767 KB / 2,3 MB / 654 KB / 350 KB, 0 nulos,
0 traceback). Só o ponteiro do estado estava vazio → qualquer auditoria por
`caminho_md` acusaria "arquivo sumido" falso. Corrigido; auditoria re-rodada:
**94/94 com estado E arquivo válidos**.

**Regra durável:** auditoria de acervo deve aceitar `md` **e** `caminho_md`
(o pipeline grava `md` na linha 1310 e o `caminho_md` só em downloads novos;
a migração de acervo deixou `md: "acervo:"` vazio). Slug canônico = o do
`pipeline-aquisicao.py` (via `importlib`), nunca reimplementado.

## Pendente

1. **Catálogo precisa crescer** — 94/94 é o teto. Para a rodada voltar a render:
   `estante-william.yaml` + `lista-aquisicao.md` → `scripts/gerar-catalogo-ficcao.py`.
2. **Gap real fora do catálogo: *O Nome da Rosa* (Umberto Eco)** — 0 ocorrências
   de "Eco"/"Umberto" no YAML. Único item da rampa #140-#144 genuinamente faltando.
3. **BookOrbit (192.168.15.26) SEM ROTA** — `curl` → HTTP 000 / Errno 113.
   **18 arquivos (71 MB)** na `_incoming/` esperando. O cron de reenvio (15 min)
   segue tentando e sai com `erro_verificacao`. Sobe sozinho quando a LXC voltar.
4. **2 `.md` de bytes nulos** seguem no disco (órfãos, KB já aponta para os bons):
   `outros/idiota-fiodor-dostoievski.md` (1,64 MB) e
   `outros/anna-karenina-liev-tolstoi.md` (1,92 MB). **Apagar exige OK do William.**
5. ***O Caso Final de Sherlock Holmes* (1927)** — sem tradução PT-BR (medido em
   2026-11-07). Recomendação mantida: pular.

## Lint

`study-lint.py` → **0 erro(s) novo(s)**, 4 conhecidos no baseline, 1 aviso
pré-existente (`esp:mnemos:tags-sem-kb`).

## Commit

`40c6e78` (repo `data/`) — estado + caminho_md das 4 obras. Pushado.
