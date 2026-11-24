# 2026-11-24 — Fila do BookOrbit travada em 409 + estado do pipeline mentindo

## O que o William pediu (literal)

> "baixe os livros em ingles, eu uso um tradutor, veja este que traduzi, ja subi no
> bookorbit: [file] — Está toda noite rodando rotina e tentando baixar livro que já
> baixou? Precisa revisar isso aí, não está marcando o que já foi baixado? Não está
> baixando nada?"

Três perguntas, três problemas diferentes. Todas as três eram reais.

## Resposta 1 — "baixe os livros em inglês, eu uso um tradutor"

Regra nova, aplicada nos DOIS pipelines:
- `pipeline-aquisicao.py`: `converte(..., permitir_en=True)` e `_gap_en = True`.
- `pipeline-biblio.py`: idem.
- O gate de ESPANHOL continua valendo (ES nunca entra — a rampa é PT-BR).

## Resposta 2 — "está rodando e tentando baixar o que já baixou?"

**Não no download** — o `status: adquirido` no `pipeline-estado.json` funciona
(0 títulos baixados 2x em todo o histórico do `rodada-log.jsonl`).

**SIM no UPLOAD ao BookOrbit.** `scripts/reenviar-incoming-orbit.py` tratava
**HTTP 409** ("A file named X already exists at the target location") como
**FALHA** e preservava o arquivo local → o cron de 15 min retentava os mesmos
23 arquivos **para sempre**. Medido: **17.999 linhas de 409** no
`orbit-reenvio.jsonl` e 8,5 MB de log, desde 2026-11-06, com **zero progresso**.

### Correções em `scripts/reenviar-incoming-orbit.py`

1. **409 = sai da fila.** Não é falha: o ebook já está no app (ou colidiu de nome).
   Vai para `_incoming/_revisar-409/`, preservado, com o nome que o Orbit tem.
   **Não apago**: 409 é colisão de NOME, não prova de que é o mesmo livro — medido:
   `A-Perdicao-Eca-de-Queiroz.epub` colide com "Coletânea de Contos de Eça de Queirós".
2. **400 "File contents do not match the .epub format" = sai da fila** →
   `_incoming/_rejeitados/`. Caso medido: `biblio-abfea1449c1f.epub` é, na
   verdade, um **PDF de 122 páginas** com extensão mentirosa.
3. **Sem nome = não tenta.** PDF/ebook sem metadado e com nome genérico
   (`zlib-1021315.pdf`, `fausto-goethe.pdf`) subia como `_unorganized` — e o
   BookOrbit aceita **UM** `_unorganized.pdf`; todos os outros dão 409 e nunca
   entram. Agora vai para `_incoming/_revisar-nome/` e é re-subido pelo
   `orbit-subir-livro.py` (metadado reescrito + nome "Autor - Título").
   Foi assim que **5 PDFs** estavam perdidos: Fausto, Eichrodt (Teologia do AT),
   1919 (John dos Passos), Tucídides e A Vida é Sonho.
4. `_meta_do_ebook()` passou a devolver **(título, autor)** — o título vai no
   `upload(..., titulo=)`, senão o BookOrbit nomeia pelo nome do arquivo.

**Resultado:** `_incoming/` zerado (23 → 0) e o cron de 15 min agora diz
"nada em _incoming/ para reenviar" em vez de spammar 23 falhas.

## Resposta 3 — "não está marcando o que já foi baixado?"

**Também real, e no campo `orbit`.** O `pipeline-estado.json` tinha **95 itens**
`status: adquirido` com `orbit != ok`. Amostra medida: **9 de 10 ESTAVAM no app**.
O ebook subia pelo cron de `_incoming/` depois de um upload que falhou, e ninguém
voltava ao estado.

### Novo script: `scripts/sincronizar-orbit-estado.py`

Lê o estado → busca o título em `GET /api/v1/books/search?q=` (só leitura) →
grava `orbit: "ok"` + `orbit_bookId`. Idempotente. Aceita título do frontmatter
do `.md` quando o estado é antigo e não tem o campo `titulo`.
**Resultado: 228/245 adquiridos agora com `orbit: ok`** (antes 168). Os 17 restantes
são obras que realmente não estão no app (ver abaixo).

### Fase 4.5 nova em `scripts/rodada-bibliotecario.sh`

Roda o sincronizador a cada rodada. Sem isso o estado volta a mentir.

### Bug irmão na notificação

`scripts/rodada-ficcao-notificar.py` contava só o campo **`data`**; o
`pipeline-biblio.py` (2ª via, a que mais baixa) grava **`quando`**. Resultado: a
rodada que baixou 12 obras anunciava *"sem mudança (0 == 0) — sem notificação"* e
o William nunca era avisado. Agora aceita os dois (`marca[:10] == hoje`).
Hoje: 22 adquiridos contados (antes: 0).

## "Não está baixando nada?" — medido

- **z-library FORA DO AR hoje**: `_dominio_vivo()` → `None`; eAPI devolve
  `{"success":0,"error":"Access denied"}`. **Cota OK não prova busca OK** (as 8
  contas reportam 10/10 — repetição da lição de 2026-11-23).
- **A 2ª via (libgen, sem cota) FUNCIONA.** Ela é que salvou a rodada: 12 obras
  pela via primária (quando o z-library respondeu de madrugada) + a 2ª via.
- Catálogo: **236 obras · 226 adquiridas · 10 pendentes**. Os 10 pendentes falham
  por motivo real (`sem candidato em zlib nem biblio`, `conversao: idioma-nao-pt`,
  `conversao: 3 candidatos tentados, nenhum converteu`). Não é o pipeline travado.

## Livros novos do caso "nunca houve bons momentos" (pedido anterior)

Baixados, convertidos, catalogados e **no BookOrbit**:

| Obra | Autor | bookId |
|---|---|---|
| *When Two Become One* | Christopher & Rachel McCluskey | 2299 |
| *Restoring the Pleasure* (3ª ed.) | Clifford & Joyce Penner | 2301 |
| *Come as You Are* | Emily Nagoski | 2295 |
| *Intended for Pleasure* | Ed Wheat | 2297 |
| *The Great Sex Rescue* | Sheila Wray Gregoire | 2291 |
| *The Sex-Starved Marriage* | Michele Weiner-Davis | 2269 |
| *Intimacy Ignited* | Dillow / Pintus | 2271 |

`kb-sexual` 10 → **12 volumes**. Nota `nunca-houve-bons-momentos-desde-o-casamento.md`
ganhou a seção **5.7** (os dois manuais clínicos que faltavam), com 18 citações
verificadas linha por linha. `lista-aquisicao.md` itens 188.3/188.4 fechados.

**Achado do McCluskey (`:414`)**: o caso de abertura é exatamente o caso em questão
— *"their concern was that Adrienne had never been able to achieve climax... (As a
general rule, if a person isn't sure, it's pretty certain the person has not.)"*.

**Achado do Penner (`:2481`)**: *"Start from the beginning and learn to touch...
Once you have confidence and pleasure, desire will surface rapidly."* — a instrução
literal para quem nunca começou.

**Mecanismo mais provável (Penner `:2345-2346`)**: *"Her lack of sexual desire was
diagnosed as secondary to inhibited sexual release. The graph of her sexual response
from the beginning of their sexual intercourse experiences to now would be gradually
declining until it was a flat line."*

## Armadilhas medidas hoje

- **`zlib-api.py search`**: a conta é **POSICIONAL depois da query**
  (`search "<q>" zlib --limit 5`).
- **`biblio-api.py download <md5>`** estoura o `exec` de 60 s em arquivo grande
  (2 MB levou ~2 min). Rodar com `nohup` e conferir o arquivo no fim — o download
  termina mesmo depois do timeout do comando.
- **O arquivo do Telegram se perde**: `media://14a02773-...` → `media store: unknown
  ref` (limpeza de mídia = 30 min). O livro traduzido que ele mandou **não pôde ser
  aberto** — precisa ser reenviado. Já havia o equivalente em PT no acervo
  (`Weiner-Davis-O-Casamento-Faminto-de-Sexo-PT.md`, veio pelo Telegram em 2026-11-24).
- **`git commit` no repo `study-agent`** levou junto `scripts/timoteo-etapa0-stats.py`,
  `tmp-conferir-oracao.py` etc. — arquivos tmp versionados por `git add -A scripts`.
  Não é bug, mas cuidado: `git add -A` num diretório com tmp pega tudo.

## Estado final

- `_incoming/`: **0 arquivos** (só 2 `.bin` órfãos: O Estrangeiro de Camus em .doc e
  Sangue Bom em RTF — precisam de conversão manual, não são ebook válido).
- `pipeline-estado.json`: 255 itens · 245 adquiridos · **228 com orbit ok**.
- lint: **0 erro novo** (4 conhecidos + 1 aviso `esp:mnemos:tags-sem-kb`).
- Commits: data `7961e9d` + `8590563` · repo `ea93133` + `7f6ec52`. Pushados.
