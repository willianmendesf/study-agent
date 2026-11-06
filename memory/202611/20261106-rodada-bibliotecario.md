# 2026-11-06 — 05:30-06:40 BRT — Rotina diaria de aquisicao: destravada + 4 bugs corrigidos

**Pedido do William (3 coisas):**
1. "o que precisa de mim?" (sobre a rodada parada)
2. "deixa programado as rodadas de aquisicoes automaticas"
3. "peca o bibliotecario rodar todo dia levantamento de novas aquisicoes"
4. "baixe os livros classicos, mesmo os que eu ja tiver fisico, isso sera util
   para caminhar comigo na leitura"

## O QUE FOI FEITO

### 1. CAUSA-RAIZ: o `data/` era root:root e o crontab roda como `willian`

**Achado principal.** O cron do `willian` disparava (journal mostra a sessao
aberta a cada 15 min), mas o log parava em 23:30 de 05/11 — a saida MORRIA
no `>>` para um arquivo root-only. **A rodada das 21h15 NUNCA rodou uma vez
 sequer.** 2.636 arquivos do `data/` eram root-owned; so' 1 era do `willian`.

**Correcao:** `scripts/liberar-permissoes.sh` (novo) — `chown -R` nos
diretorios de trabalho + `chmod 640` no YAML de credenciais. Testa escrita
real em 8 caminhos no fim. Rodado: **tudo gravavel**.

Armadilhas descubtas na volta:
- `data/perfil/` INTEIRO era root-only → o lint quebrava com
  `PermissionError` em `perfis.md`. Agora coberto recursivamente.
- `data/.indice/livros.db` (2,1 GB) → o `PRAGMA journal_mode=WAL` falhava
  com "readonly database" e a **BUSCA NOS LIVROS ficava fora do ar**.
- `data/perfil/perfis.md` desapareceu do disco durante a manha. Restaurado
  do git (`git show HEAD:perfil/perfis.md`) — **identico ao HEAD**, 223
  linhas, 22 especialistas (inclui `mnemos` e `dokimia`). Sem perda.

### 2. Rotina diaria UNIFICADA (5 fases)

`scripts/rodada-bibliotecario.sh` (novo) — era preciso porque a
`rodada-ficcao.sh` so' rodava a FASE 2; as outras fases viviam em scripts
separados e NENHUM funcionava (mesma causa de permissao).

| fase | o que faz |
|---|---|
| 1 | levantamento de gaps (nao gasta cota) |
| 2 | aquisicao de ficcao no z-library (8 contas, cota de 80/dia) |
| 3 | catalogo + reindexe + lint |
| 4 | reenvio dos ebooks ao BookOrbit (app de leitura) |
| 5 | notificacao no Telegram (so quando o total muda — sem spam) |

**Cron:** `15 0 * * *` = 00:15 UTC = **21:15 BRT** (15 min apos o reset da
cota do z-library, que e' a meia-noite UTC).
Arquivo: `scripts/crontab-bibliotecario.txt` (instalado no crontab real).

### 3. 4 BUGS CORRIGIDOS NA CAUSA (nao no sintoma)

**Bug A — a obra ERRADA era baixada.** O pipeline escolheu *"Pena Capital"*
(de Robert Wilson) em vez de *"A Capital"* (de Eça de Queiroz) para o
primeiro livro da rampa. Tres causas somadas:
1. a busca parava na **1a query** — que devolvia 30 resultados ruins
   (biografias, dicionarios) e a obra boa so' aparecia na variante
   "Queirós". Agora **acumula todas** as queries (buscar nao gasta cota).
2. o z-library indexa **"Eça de Queirós"**; o catalogo tem "Eça de Queiroz".
   Agora `variantes_autor()` gera as grafias (com/sem acento, invertida,
   so' o sobrenome).
3. o bonus de "titulo contido" (+0.22) valia o **mesmo** para "A Capital" e
   "Pena Capital" (substring). Agora o substring vale +0.08 e o **titulo
   exato** vale +0.30; autor totalmente ausente derruba o score (-0.40).

**Medido:** "Pena Capital" saiu de 1.14 → 0.74. "A capital! (Clássicos
Globo)" de Eça = 1.28. Escolha correta.

**Bug B — o rodizio drenava as contas em sequencia** (`zlib` → `zlib2` →
...), jogando as 80 cotas/dia numa rajada. Agora escolhe a conta com **mais
cota restante**.

**Bug C — upload ao Orbit travava 10 min por arquivo** (timeout 600s) com
o BookOrbit offline. Agora 45s, e o ebook fica na fila para o cron de 15 min.

**Bug D — a via alternativa (libgen) despejava traceback inteiro** no log,
enterrando o resultado real. Agora tolerante, timeout 180s, resumo em 1 linha.

### 4. Livros baixados HOJE (rodada real, 7 + 1)

**A Capital** (Eça de Queiroz) — 749 KB, 7.388 linhas, edicao critica de
Luiz Fagundes Duarte (Editora Globo, 2006), com notas ao texto. **Obra
UNICA**, nao antologia — serve de material de prova da IPB.

Mais 7 da estante fisica: A Casa das Sete Torres · Divina Comedia
(bilingue, traducao de Jose Pedro Xavier Pinheiro) · A Escola de Mulheres ·
A Morte em Veneza · A Outra Volta do Parafuso · A Religiosa · As Relacoes
Perigosas. **Todas com conteudo conferido** (7/7 integras).

`catalogo-ficcao.yaml`: **84 → 89 obras** (A Capital + 4 do Eça).

### 5. O que ainda NAO esta pronto

- **BookOrbit (LXC 26) esta OFFLINE** → os 9 ebooks estao na fila
  `data/biblioteca/_incoming/`. O cron de 15 min reenvia sozinho quando
  voltar. (NAO e' bug — a maquina esta desligada.)
- A nota da rampa no Memos ainda diz que A Capital so' existe em fisico.
  **Precisa atualizar** (o digital ja' esta no acervo).

## LiCao

> **O cron disparava e ninguem percebia.** O job estava "instalado", o
> journal mostrava a sessao aberta, o script existed, o plano estava feito.
> O que faltava era **permissao de escrita**. Um job que nao escreve log
> parece um job que nao roda — e nao e' verdade: roda e morre no primeiro
> redirect.
>
> **Regra:** depois de instalar um cron, o teste nao e' "o job existe" nem
> "o journal mostra a sessao". E' **"o arquivo de saida mudou de mtime"**.
> E se o job escreve no `data/`, o `data/` tem que ser gravavel pelo
> usuario do crontab — sempre.
