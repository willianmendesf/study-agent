# Rodada diária de aquisição de FICÇÃO — 2026-11-19

## Comando
`data/perfil/bibliotecario/rodada-ficcao.sh --max 12`

## Estado na largada
- Catálogo: **94 obras · 94 adquiridas · 0 pendentes** → a rodada não tinha o que baixar.
- Cota do z-library: 72 downloads disponíveis (8 contas).

## O que foi feito (não aceitar "0 baixados" como resultado)
Aplicada a instrução permanente do William (2026-11-18): **"sempre amplie o catálogo"**.
O catálogo foi ampliado de 94 → **114 obras**, com 20 alvos **medidos** contra o acervo
(`data/biblioteca/**`) antes de entrar — nenhum deles existia.

Eixos novos:
1. **Cânone brasileiro** (prova de Literatura IPB — a lista muda todo ano, o Manual 2027
   ainda não existe): Quincas Borba · Helena · Esaú e Jacó · O Alienista · Senhora ·
   O Guarani · O Cortiço · O Ateneu · São Bernardo · Angústia · A Paixão segundo G.H. ·
   Macunaíma · Sagarana · Noite na Taverna.
2. **Realismo português**: O Primo Basílio · Os Maias.
3. **Clássicos curtos** (degraus baixos da rampa): O Velho e o Mar · A Metamorfose.
4. **Ficção cristã** (a estante do William tem zero): O Grande Divórcio ·
   Cartas de um Diabo a seu Aprendiz.

## Resultado: 19 obras novas

| # | Obra | Autor | Arquivo (.md) |
|---|---|---|---|
| 1 | A Metamorfose | Franz Kafka | alemão/A-Metamorfose-Franz-Kafka.md |
| 2 | A Paixão segundo G.H. | Clarice Lispector | brasileira/A-Paixao-segundo-GH-Clarice-Lispector.md |
| 3 | Cartas de um Diabo a seu Aprendiz | C. S. Lewis | ingles/Cartas-de-um-Diabo-a-seu-Aprendiz-C-S-Lewis.md |
| 4 | Helena | Machado de Assis | brasileira/Helena-Machado-de-Assis.md |
| 5 | Macunaíma | Mário de Andrade | brasileira/Macunaima-Mario-de-Andrade.md |
| 6 | O Alienista | Machado de Assis | brasileira/O-Alienista-Machado-de-Assis.md |
| 7 | O Cortiço | Aluísio Azevedo | brasileira/O-Cortico-Aluisio-Azevedo.md |
| 8 | O Grande Divórcio | C. S. Lewis | ingles/O-Grande-Divorcio-C-S-Lewis.md |
| 9 | O Primo Basílio | Eça de Queiroz | portugues/O-Primo-Basilio-Eca-de-Queiroz.md |
| 10 | O Velho e o Mar | Ernest Hemingway | anglo-saxoes/O-Velho-e-o-Mar-Ernest-Hemingway.md |
| 11 | Os Maias | Eça de Queiroz | portugues/Os-Maias-Eca-de-Queiroz.md |
| 12 | Quincas Borba | Machado de Assis | brasileira/Quincas-Borba-Machado-de-Assis.md |
| 13 | Angústia | Graciliano Ramos | brasileira/Angustia-Graciliano-Ramos.md |
| 14 | Esaú e Jacó | Machado de Assis | brasileira/Esau-e-Jaco-Machado-de-Assis.md |
| 15 | Noite na Taverna | Álvares de Azevedo | brasileira/Noite-na-Taverna-Alvares-de-Azevedo.md |
| 16 | O Ateneu | Raul Pompeia | brasileira/O-Ateneu-Raul-Pompeia.md |
| 17 | O Guarani | José de Alencar | brasileira/O-Guarani-Jose-de-Alencar.md |
| 18 | São Bernardo | Graciliano Ramos | brasileira/Sao-Bernardo-Graciliano-Ramos.md |
| 19 | Sagarana | João Guimarães Rosa | brasileira/Sagarana-Joao-Guimaraes-Rosa.md |

Todas convertidas em `.md`, catalogadas na `kb-literatura` e enviadas ao BookOrbit
(`orbit: ok` no estado). **Verificação de integridade:** 19/19 com 0 byte nulo,
0 traceback, contagem de linhas coerente (101 KB–1,3 MB).

## Bugs/armadilhas do dia
1. **`Sagarana` falhou na 1ª tentativa** ("download falhou") na 1ª conta e o pipeline
   pulou para a 2ª via; baixou no ad-hoc com outra conta (`zlib-api.py download
   <id> <hash> zlib8`). Lição: falha de download em 1 conta não é falha da obra —
   rodar `--titulo` força nova tentativa com as outras contas.
2. **O catalogador decide a PASTA pela pasta do arquivo**: Sagarana caiu em `outros/`
   (pasta default do ad-hoc). Movido para `brasileira/`, com `caminho_md` corrigido
   na KB **e** no `pipeline-estado.json` (`md` e `caminho_md`).
3. **BookOrbit 429** a partir do 3º/4º login em minutos — esperar 30–60 s entre lotes.
   `GET /api/v1/libraries/1/books` → **404** (não existe); o caminho é
   `GET /api/v1/books/search?q=` e `GET /api/v1/libraries` (traz `bookCount`).
4. **`São Bernardo` não aparece na busca do BookOrbit** (`Bernardo`, `São Bernardo`,
   `Graciliano` → nada), embora o estado diga `orbit: ok`. Provável metadado do EPUB
   sem o título no `dc:title`. Pendente de conferência no app.

## Pendências
- `São Bernardo` (Graciliano) — conferir no app do BookOrbit; se estiver como
  `_unorganized`, o metadado precisa ser reescrito (`scripts/renomear-metadata-ebook.py`)
  **antes** de subir — a conta `study-agent` não tem permissão para corrigir nem apagar
  livro já subido.
- `_incoming/` tem 20 arquivos antigos que o cron de reenvio tenta subir a cada 15 min e
  recebe **409** (já existem no acervo). Não é erro, mas polui o log (~4 MB/dia).
  Limpeza exige aprovação do William.
- Catálogo agora 114/114 adquirido → a próxima rodada volta a dar 0. Ampliar de novo
  (Sagarana era o último; sugestões: Grande Sertão: Veredas, Iracema já existe,
  Os Sertões, Memórias de um Sargento de Milícias, A Escrava Isaura).

## Lint
`study-lint: 0 erro(s) novo(s), 4 conhecido(s) no baseline, 1 aviso(s)` — rodado 3x
(antes do commit, depois da movimentação do Sagarana e no fecho).

## Commits
- `data`: `21ae51a` (19 obras + KBs) · `7d59c12` (Sagarana movido, estado + KB)
- repo: `306e9f2` (catalogo-ficcao 94→114)
