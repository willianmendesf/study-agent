# 2026-11-24 — Rodada de ficção (execução manual 07:15 UTC / 04:15 BRT)

## Comando
`data/perfil/bibliotecario/rodada-ficcao.sh --max 12`

## Resultado
- **2 obras baixadas** nesta execução, ambas pela **2ª via (biblio/libgen, sem cota)**:
  - *As Naus* — António Lobo Antunes → `data/biblioteca/literatura-mundial-classica/portugues/As-Naus-Antonio-Lobo-Antunes.md` (361 KB, 56.273 palavras, 0 nulos, 0 traceback)
  - *Satiricon* — Petrônio → `.../antigos/Satiricon-Petronio.md` (364 KB, 57.889 palavras, 0 nulos, 0 traceback)
  - Ambas catalogadas na `kb-literatura-mundial-classica`.
- **14 obras no total do dia**: as 12 da rodada automática das 00:17 UTC (Mensagem, O Barão nas Árvores, Budapeste, O Asno de Ouro, Quarup, Se um Viajante numa Noite de Inverno, Recordações da Casa dos Mortos, Tieta do Agreste, Ubirajara, Viagens na Minha Terra, A Morte de Virgílio, A Normalista) + as 2 desta execução.

## Estado dos serviços (medido)
- **z-library: ACESSO NEGADO** — `POST https://z-lib.gd/eapi/book/search` → `{"success":0,"error":"Access denied"}` HTTP 400. Todos os domínios sem resposta. Não é cota: é bloqueio de acesso (3ª ocorrência: 23/11 à noite, 24/11 madrugada e 24/11 manhã).
- **BookOrbit (192.168.15.26): FORA** — `/api/v1/health` → HTTP 000, `URLError 113 No route to host`. As 2 obras ficam em `_incoming/` (`As-Naus...epub`, `Satiricon...pdf`) para o cron de reenvio (15 min) subir quando voltar.
- Nota: às 00:17 o Orbit **estava no ar** (bookId 2288 para A Normalista, 1393 livros).

## Pendente (10 obras no catálogo; 226/236 adquiridas)
A Pele (Malaparte) · América (Kafka) · Eugênio Oneguin (Púchkin) · Sonhos de uma Noite de Verão (Shakespeare) · Til (Alencar) · Um Copo de Cólera (Nassar) · Zero (Loyola Brandão) · A Regenta (Clarín) · Fortunata e Jacinta (Galdós) · Tristram Shandy (Sterne).

## Lint
`study-lint.py` → **0 erros novos** (4 conhecidos no baseline, 1 aviso `esp:mnemos:tags-sem-kb`).
