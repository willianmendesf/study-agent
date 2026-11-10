# 2026-11-10 — Rodada diária de aquisição de FICÇÃO (escala) — 04:15 BRT

**Pedido (cron):** rodar `data/perfil/bibliotecario/rodada-ficcao.sh --max 12` e
reportar quantos livros foram baixados, quais, e o que ficou pendente. Rodar cedo
(a cota do z-library reseta à meia-noite UTC = 21h BRT). Se o lint acusar erro
novo, corrigir a causa antes de encerrar.

## Resultado

| item | valor |
|---|---|
| livros baixados | **13** (meta era 12) |
| falhas | 6 (todas legítimas: conteúdo divergente, idioma não-PT, sem candidato) |
| lint | **0 erro(s) novo(s)**, 4 conhecidos no baseline, 1 aviso — **exit 0** |
| catálogo | 94 obras · **62 adquiridas** · 32 pendentes |
| fonte | **2ª via (libgen, SEM COTA)** — o z-library está fora do ar |

## O z-library está fora do ar (medido, não suposto)

Varri **70+ domínios** (z-lib.* e zlib.*) contra o endpoint REAL de busca
(`POST /eapi/book/search`, o mesmo critério do `_search_ok()` do `zlib-api.py`).
**Nenhum** devolveu `success:1`.

| domínio | resultado |
|---|---|
| z-lib.gd | 000 — *Connection refused* (79.124.59.190) |
| z-lib.se | 200 no `/` mas é um **domínio à venda** (parked, Spaceship) |
| z-lib.sk / .fm | 307 → DiamWall |
| z-lib.su | 301 → **zlib.by** (novo), mas 503 + proteção anti-bot no eAPI |
| z-lib.li / .rs / .es / .net | TLS/connection reset |
| z-lib.co / zlib.cc / zlib.net / zlib.org | 404 no path do eAPI |
| resto | NXDOMAIN |

A internet geral está OK (google 200) e o **libgen.li responde 200** — por isso a
rodada funcionou pela 2ª via.

⚠️ **Armadilha do `zlib-api.py`:** a descoberta de domínio cai no fallback
`DOMAINS[0]` (= `z-lib.gd`) quando nenhum responde. Aí `limits` reporta
"sem resposta (rede/timeout)" nas 8 contas — **parece cota esgotada, mas é rede**.
Separar as duas causas ANTES de reportar é regra (ver MEMORY.md 2026-11-10).

## 🐛 BUG DE CAUSA — a 2ª via travava o catálogo inteiro

**Sintoma:** a rodada rodou e processou **ZERO itens**, com `baixados: 0 · falhas: 0`.
Não era cota, não era rede.

**Causa raiz:** `scripts/pipeline-biblio.py` (a 2ª via, SEM COTA) **nunca recebeu**
a correção de **2026-11-09** que o `pipeline-aquisicao.py` (via primária) ganhou.

```python
# ANTES (2ª via) — trava para SEMPRE
if st.get("tentado") and st.get("status") == "falhou" and not args.titulo:
    continue

# DEPOIS (alinhado com a via primária)
if tentativa == hoje and not falha_de_rede:
    continue
```

O `continue` sem comparar a **DATA** bloqueava a obra para sempre: as **46
falhas** do catálogo estavam travadas desde **2026-11-06** e nenhuma voltaria a
ser tentada — nem pela 2ª via, que não gasta cota. **41 obras nunca tinham sido
tentadas** e a rodada as ignorava em silêncio.

**Regra que emerge:** *quando uma correção é aplicada num pipeline, ela tem de
ser replicada nos pipelines irmãos que compartilham o mesmo arquivo de estado.*
O `pipeline-estado.json` é compartilhado pelos DOIS — um lê, outro escreve, e a
semântica do "já falhou" precisa ser a mesma nos dois lados.

**Verificação:** após o patch, a mesma rodada baixou 13 livros. Causa corrigida,
não sintoma.

## 🐛 2º BUG — `timeout` e `--max` da 2ª via cortavam a rodada

`rodada-ficcao.sh` rodava a 2ª via com `timeout 180` e `--max 6` fixo.

**Medido:** a 2ª via leva **~2 min por livro** (busca no libgen + download +
conversão + catálogo + reindexe). 180 s cortava no **3º livro**; `--max 6`
limitava a 6 mesmo com meta 12.

Corrigido: `MAX_BIB="$MAX"` (mesma meta da rodada) e
`TIMEOUT_BIB=$(( MAX * 600 ))` com teto de 60 min.

## Os 13 livros (todos com conteúdo real verificado + catalogados na KB)

| obra | autor | KB | palavras |
|---|---|---|---|
| Contos | Edgar Allan Poe | anglo-saxoes | 12.467 |
| Histórias Extraordinárias | Edgar Allan Poe | antigos | 66.155 |
| Contos | Guy de Maupassant | frances | 107.695 |
| Contos | Nikolai Gógol | russo | 115.385 |
| Contos | Katherine Mansfield | anglo-saxoes | 44.335 |
| Novelas Exemplares | Miguel de Cervantes | anglo-saxoes | 208.281 |
| Decamerão | Giovanni Boccaccio | frances | 29.164 |
| O Burguês Fidalgo | Molière | frances | 21.808 |
| O Falecido Mattia Pascal | Luigi Pirandello | italiano | 81.186 |
| O Grande Gatsby | F. Scott Fitzgerald | anglo-saxoes | 60.315 |
| O Mandarim | Eça de Queiroz | portugues | 20.172 |
| O Morro dos Ventos Uivantes | Emily Brontë | romantismo | 128.795 |
| O Pequeno Príncipe | Antoine de Saint-Exupéry | antigos | 20.542 |

**Verificação de integridade:** medí palavras + linhas com prosa real por
arquivo. Dois cautionary cases: o Poe (`Contos`) tem só 166 linhas mas 12.467
palavras (texto em parágrafos longos — legível); o Gogol e as Histórias
Extraordinárias trazem marcadores `part0001` **no meio do texto** (artefato do
EPUB) — o conteúdo segue íntegro.

## Pendências

**32 obras** no catálogo (de 94). Tipos de falha:

- **conteúdo divergente (6)** — o título da obra não aparece no texto extraído:
  Retratos (Joyce), A Casa dos Espelhos (Woolf), O Homem que foi Quinta-feira,
  Uma História de Duas Cidades (Dickens), Contos (Turgenev), O Pequeno Principe.
- **idioma não-PT (2)** — Cyrano de Bergerac (EN), O Poder e a Glória (ES).
- **sem candidato (3)** — Estado de Sítio e O Estrangeiro (Camus), O Problema
  da Dor (Lewis), O Conde de Abranhos e A Perdição (Eça).
- **conversão sem .md (3)** — O Estrangeiro, O Peregrino (Bunyan), Sangue Bom.
- **download falhou (16)** —Reply Major (Fitzgerald), Ortodoxia (Chesterton),
  Os Trabalhadores do Mar (Hugo), Pequenos Burgueses (Gorki), Tartufo (Molière),
  Tom Jones (Fielding), Werther (Goethe), e outros.

As 16 "download falhou" são **candidatos para a próxima rodada com o z-library
de volta** — o motivo é falha de download, não recusa de conteúdo.

## Pendências externas (NÃO desta rodada)

- **Rede local 192.168.15.x sem rota** — SearXNG (.41), BookOrbit (.26),
  Librarium (.201), Speaches (.140). O **reenvio ao BookOrbit falha** com
  `No route to host`; `orbit-estado.json` = `erro_verificacao`. Os 28 arquivos
  em `_incoming/` (incluindo os 13 ebooks de hoje) **não subiram ao app**.
  O cron de 15 min continua tentando sozinho quando a rede voltar.
- **Memos** — não testado neste turno (mesma rede local).

## Commits

- `4996cf5` (data) — 13 livros + KB + estado + `rodada-ficcao.sh`
- `358a4d7` (repo) — `scripts/pipeline-biblio.py`

Ambos pushados. Lint: 0 erro novo.
