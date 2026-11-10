# 2026-11-10 — Rodada diária de aquisição (Bibliotecário) 06:30 UTC

**Pedido (cron 06:30 UTC):** rodar `rodada-diaria.sh` (fases 0+1+2) e reportar:
quantos materiais baixados, quais gaps fechados, quantos pendentes, resultado do lint;
se o lint acusar erro novo, corrigir a causa.

## Resultado medido

| item | valor |
|---|---|
| materiais baixados | **0** |
| gaps fechados | **0** (nenhum gap pendente medido) |
| gaps pendentes | **0** nas 13 áreas |
| lint | **0 erro(s) novo(s)**, 4 conhecidos no baseline, 1 aviso — **exit 0** |
| acervo | 1.150 `.md` · 1.357 materiais catalogados nas KBs |
| duração | 06:32:56 → 06:37:00 UTC |

**Nenhuma correção foi necessária**: o lint saiu com exit 0 e 0 erros novos. O único
aviso (tags do Mnemós sem KB no pool) é conhecido e de baixo impacto.

## Por que 0 downloads — DUAS causas independentes (não uma só)

**1. Saturação real do acervo (a causa legítima).** A FASE 1 mede os gaps com
`gaps-pendentes-rotina.py`, que é leitura local e **não gasta cota**. Verificado
com `--json`: `areas: {}`, `saturados: [13 áreas]`.

Prova de que a saturação é genuína e não lista de candidatos vazia:
- as 13 áreas têm **50 candidatos no total**, todas com lista **não-vazia**;
- o acervo indexado tem 1.489 títulos + 1.149 assinaturas;
- `Livros bíblicos SEM comentário: 0`.

Ou seja: o acervo **atingiu o mínimo definido** em todas as áreas. A regra do
script já é a correta — não gastar cota contra alvo saturado (foi o BUG I/N de
2026-10-29/31).

**2. z-library INALCANÇÁVEL (impediria qualquer download).** Testado com o endpoint
real de busca (`POST /eapi/book/search`, o mesmo critério que o `zlib-api.py` usa):

| domínio | resultado |
|---|---|
| z-lib.gd (canônico) | **000** — TCP *Connection refused* em 79.124.59.190 |
| z-lib.sk | 307 (DiamWall) |
| z-lib.se / .li | 000 (TLS handshake não completa) |
| z-lib.co | 404 no path do eAPI (frontend real, API em outro path) |

Nenhum domínio devolve `success:1`. A descoberta de domínio do `zlib-api.py`
caiu no fallback `DOMAINS[0]` (= `z-lib.gd`, que está recusando conexão) — por
isso `zlib-api.py limits` reporta "sem resposta (rede/timeout)" nas 8 contas.
**Não é cota esgotada: é rede/serviço fora do ar.**

A internet geral está OK (google 200) e o SearXNG local (192.168.15.41) está
também sem rota — a rede local está parcialmente caída.

## Pendentes que sobraram (nenhum é desta rodada)

- **`_incoming/`: 13 arquivos** (12 do z-library + `Sangue-Bom-Flannery-OConnor.bin`).
  O reenvio ao BookOrbit está falhando com `No route to host` (192.168.15.26 sem rota).
  Os 12 zlib-* já dão **409 "already exists"** no Orbit (foram enviados em rodada
  anterior) — os arquivos locais são duplicatas que nunca são apagadas.
  `orbit-estado.json` = `erro_verificacao`.
- **Catálogo de compras: 275 obras** — 246 `sem_link`, 21 `a_comprar`, 8 `nao_comprar`.
  As 246 sem link dependem do SearXNG (que está sem rota) e da Amazon.
- **4 erros conhecidos no baseline do lint** (não são novos): 2 KBs inexistentes
  (`kb-pendencias-gaps.yaml`, `kb-relacoes-mapa.yaml`), 1 path de especialista
  (`bibliotecario-autoaperfeicoamento.md`), 1 path de estudo
  (`exegese-romanos-3-21-26-hermes.md`).

## Observações de higiene

- As 85 KBs modificadas pela rodada têm diff **apenas de `atualizado_em`** — nada
  mais mudou. 85 inserções / 85 remoções, 0 arquivos novos.
- `data/` está limpo e pushado (`1e45d0f data: cota diaria 2026-11-10`), sem
  commits pendentes.
- O job do picoclaw `fed05ac460f0a3d5` (06:30 UTC) é o que disparou este turno.
  A **rodada de ficção** (00:15 UTC) também rodou hoje com 0 downloads pelo mesmo
  motivo (z-library fora do ar), registrada em `rodada-ficcao-2026-11-10.log`.

## Lição

**"0 downloads" tem duas causas possíveis e elas precisam ser separadas:**
saturação legítima (a saúde da biblioteca) vs. serviço fora do ar (falha).
Reportar só "0 baixados" seria enganoso. A verificação que separa as duas é:
rodar o helper de medição com `--json` (confirma saturação) **e** testar o
endpoint real de busca nos domínios (confirma rede). Ambas foram feitas.
