# 2026-11-09 — Rodada de FICÇÃO: 0 livros + 4 bugs de causa (z-library fora do ar)

## Pedido (cron)
Rodar `data/perfil/bibliotecario/rodada-ficcao.sh --max 12` e reportar baixados / quais /
pendente. Se o lint acusar erro novo, corrigir a causa.

## RESPOSTA CURTA
**0 livros baixados.** Não foi falta de cota: **o z-library está fora do ar** e
**4 bugs** faziam a rodada morrer/mendar. Tudo corrigido na causa e commitado.

---

## O que realmente aconteceu

### 1. A primeira rodada printou uma MENTIRA
```
cota por conta: zlib=0, zlib2=0, zlib3=0, zlib4=0, zlib5=0, zlib6=0, zlib7=0, zlib8=0
!! cota esgotada em todas as contas — nada a baixar agora
```
As 8 contas "sem cota" era **falha de rede**: `z-lib.gd` não responde.

### 2. Estado da rede medido (07:15-07:50 UTC)
| alvo | estado |
|---|---|
| `z-lib.gd` (79.124.59.190) | **timeout em 45 s** — confirmado por 2 caminhos (curl + web_fetch) |
| `z-lib.se` / `z-lib.li` / `zlib.cz` | respondem, mas o eAPI **não** (307 DiamWall / challenge JS "verificando seu navegador") |
| Internet aberta (google/example/pypi) | **200 — a rede da LXC está OK** |
| `192.168.15.26` (BookOrbit), `.41` (SearXNG), `.201` (Librarium) | **SSH e HTTP FALHOU — a frota de LXC está toda fora** |
| `192.168.15.54` (Heimdall) | **OK** |
| Tailscale: `ebooks`, `librarium`, `phreshos`, `tools` | **offline (last seen 1-5d)** |

→ Não é o z-library só: **a infraestrutura inteira do William está fora do ar**.
O `reenvio-orbit-automatico.sh` (cron de 15 min) também falha:
`URLError [Errno 113] No route to host` → os 12 arquivos em `_incoming/` estão
travados na fila.

---

## 🐛 4 BUGS REAIS (corrigidos na causa, não no sintoma)

### Bug 1 — O CRON ESTAVA MORTO desde 2026-11-08 (e nenhum alarme disparou)
`crontab` chama o wrapper **direto**:
```
15 0 * * * /home/willian/study-agent/scripts/rodada-bibliotecario.sh 12 2 >> ...
```
O commit `3dda684` (2026-11-07 07:16) **removeu o bit de exec**:
```
old mode 100755
new mode 100644
```
Resultado no log: `/bin/sh: 1: .../rodada-bibliotecario.sh: Permission denied`
— **1 linha, no fim, que ninguém leu**. O log de 2026-11-08 tem só essa linha.

**Correção (dupla):**
1. `git update-index --chmod=+x scripts/rodada-bibliotecario.sh` (100755 no índice).
2. **crontab agora chama `bash <script>`** → imune a essa classe de falha.
   Verificado: com o arquivo em `600`, `bash <script>` roda; direto, dá Permission denied.

**Lição:** *um `git commit` pode mudar o modo do arquivo e matar um cron em
silêncio.* O bit de exec precisa ser conferido junto com o conteúdo.

### Bug 2 — DOMÍNIO HARDCODED no pipeline
`scripts/pipeline-aquisicao.py` tinha `DOM = "z-lib.gd"` fixo (linha 51), em 3
call sites (`cota`, `busca`, `baixa`). O `zlib-api.py` já tinha descoberta de
domínio — o pipeline não.

**Correção:** `_dominio_vivo()` descobre em runtime, **mesma política do
`zlib-api.py`**: só vale o domínio que devolve `success:1` numa **busca real**
(o `z-lib.sk` responde 307 → DiamWall; `zlib.cz` responde 200 mas é challenge
JS — ambos rejeitados). 18 candidatos, cache do probe (1 vez por processo).

### Bug 3 — "COTA" vs "REDE" (o bug que produziu a mentira)
`cota()` fazia *"resposta inválida ⇒ 0"*. Isso **confundia duas coisas**:
(a) conta sem cota e (b) z-library fora do ar. Em (b) as 8 contas davam 0 e a
rodada abortava como se a cota tivesse sido gasta.

**Correção:** `cota()` devolve `(cota, erro)`; o erro distingue
`"z-library inacessivel (sem resposta)"` de `"sem cota"`. O abort por cota
só acontece se **nenhum** erro for de rede. E, se o probe de domínio já provou
que o z-library está fora, o pipeline **não sonda as 8 contas** (30 s cada =
4 min de espera) — aborta na hora com a mensagem verdadeira.

### Bug 4 — A VIA SEM COTA MORRE JUSTAMENTE QUANDO PRECISA
`pipeline-biblio.py` (libgen/Anna's — a via que existe **para** quando o
z-library falha) chamava `zlib-api.py limits` com `timeout=120` e o
`TimeoutExpired` **não era tratado** → traceback → a 2ª via morria no dia em
que era necessária.

**Correção:** timeout e qualquer exceção → cota 0 com aviso, e a via **segue**.
Verificado: rodou até o fim, buscou no libgen e **rejeitou 2 candidatos em
inglês** ( Ulysses para "Retratos"; Good Country People para "Sangue Bom") pelo
guard de conteúdo — ou seja, a via funciona.

### Bug 5 (extra) — GUARDA DE RETRY ETERNA
O comentário dizia *"já falhou uma vez: não repete **no mesmo dia**"*, mas o
código **não comparava a data**. Qualquer falha (inclusive de rede) travava a
obra **para sempre**. As 46 falhas do catálogo estavam travadas desde 2026-11-06
(33 em 06/11, 9 em 07/11, 2 em 08/11, 2 em 09/11).

**Correção:** só bloqueia se a tentativa for **do mesmo dia** e não for falha
de rede.

**Verificado:** com o estado real, dos 46 pendentes → **44 liberados** (todos
os 36 de rede inclusos) e **2 mantidos** (`Retratos`, `Sangue Bom` — falharam
hoje e não são falha de rede).

---

## 📊 Estado medido do catálogo (94 obras)
- **55 adquiridas** · **46 pendentes**
- Das 46 pendentes, **36 são falha de REDE** (domínio), não problema da obra:
  | motivo | n |
  |---|---|
  | rede/domínio (`download falhou: download falhou`) | **36** |
  | conversão: conteúdo divergente (título não aparece no texto) | 5 |
  | download: nenhum link | 2 |
  | sem candidato acima do limiar | 2 |
  | conversão sem .md | 1 |
- **As 36 de rede destravaram sozinhas** com o Bug 5 — assim que o z-library
  voltar, voltam a ser tentadas.

### Os 6 casos que precisam de decisão humana
| obra | problema |
|---|---|
| Histórias Extraordinárias (Poe) | título não aparece no texto do EPUB |
| O Homem que foi Quinta-feira (Chesterton) | idem (o EPUB é **em inglês** — "The Man Who Was Thursday") |
| Uma História de Duas Cidades (Dickens) | idem |
| A Casa dos Espelhos (Woolf) | sem EPUB — precisa de outro formato |
| Retratos (Joyce) | sem EPUB — idem |
| Sangue Bom (Flannery O'Connor) | conversão sem .md |

**Lição:** o guard `conteudo_confere()` está certo em rejeitar — o EPUB do
Chesterton e do Dickens são **traduções INGLSES** e a rampa é PT-BR. Não é bug
do guard; é falta da tradução PT.

---

## 📌 `_incoming/` — 12 arquivos presos (cota JÁ gasta)
```
As-Relacoes-Perigosas-Choderlos-de-Laclos.epub
fausto-goethe.pdf · zlib-1021315.pdf · zlib-118432194.pdf · zlib-29290336.pdf
zlib-11854218.epub · zlib-11854226.epub · zlib-120431946.epub · zlib-17392455.epub
zlib-23895908.epub · zlib-4777894.epub · zlib-5595223.mobi
```
O download **já consumiu cota** — não se perde, só espera o Orbit voltar.
`recuperar-pdfs-incoming.py --listar` mapeia 1 de 4 PDFs (o resto sem mapa).

## Commits
- `b16bed3` (repo) — 4 bugs + bit de exec + crontab via `bash` → **pushado**
- `60e7e69` (data) — estado da rodada → **pushado**
- Lint: **0 erro novo** (4 conhecidos no baseline, 1 aviso)

## Pendente (depende do William / da infra)
1. **Z-library voltar** → rodar de novo; as 36 pendentes de rede destravam.
2. **Frota de LXC voltar** (BookOrbit 26, SearXNG 41, Librarium 201) → o
   reenvio automático (cron de 15 min) retira os 12 arquivos de `_incoming/`.
3. **6 obras** da tabela acima precisam de tradução PT-BR ou de outro formato.
