# Rodada de ficção — 2026-11-14 (07:15 UTC / 04:15 BRT)

## Resultado

**0 livros baixados · 0 falhas · cota intacta (80 de 80 disponíveis, 8 contas × 10).**

Não é falha: o catálogo está **94/94 adquirido**. A rodada não tinha o que fazer.

Rodei duas vezes para confirmar (a do cron das 00:16 UTC e uma manual às 07:15 UTC) —
as duas com o mesmo resultado: `=== 0 adquirido(s), 0 falha(s) ===` e a 2ª via
(libgen, sem cota) saindo com `exit 1` = "rodou OK, nada a baixar".

## Prova de que a saturação é real (não sensor quebrado)

1. `pipeline-aquisicao.py --status` → **94 no catálogo · 94 adquiridos · 0 pendentes**.
2. `pipeline-estado.json` → **101 itens, 100% com status `adquirido`, 0 falhas**.
3. **Integridade de cada arquivo, um a um** (não confiei no campo do estado):
   94/94 com arquivo existente, 0 bytes nulos, 0 traceback de extração.
4. **Cota real medida** (`zlib-api.py limits`): 8 contas × 10 = **80 downloads livres**.
   Se fosse cota, o número seria 0.
5. **Domínio ativo:** `z-lib.gd` respondeu (busca real OK) — não é serviço fora do ar.

## O que ficou pendente

### 1. 🚨 O catálogo precisa crescer — é o gargalo agora
O catálogo tem 94 obras e **todas** foram adquiridas. Para a rodada voltar a render,
o caminho é **ampliar o catálogo** (`estante-william.yaml` + `lista-aquisicao.md` →
`scripts/gerar-catalogo-ficcao.py`). Não há código a mudar.

### 2. Gap real fora do catálogo: **O Nome da Rosa** (Umberto Eco)
A lista `#141` marca como pendente, mas a obra **nunca entrou no catálogo** (0
ocorrências de "Eco"/"Umberto" no YAML). É o único item da rampa #140-#144 que
está genuinamente faltando.

### 3. 18 arquivos na `_incoming/` (71 MB) esperando o BookOrbit
O BookOrbit (192.168.15.26) está **sem rota** hoje (`curl` → Errno 113, 150
ocorrências no log de reenvio). O cron de reenvio automático (15 min) segue
tentando e sai com `erro_verificacao`. Assim que a LXC voltar, sobe sozinho.
Identifiquei os EPUBs pelo `dc:title`: Casa das Sete Torres, Outra Volta do
Parafuso, Escola de Mulheres, Consciência de Zeno, A Religiosa, Divina Comédia
(edição bilíngue), Teeteto, + Reformed Ethics vol. 2 (Bavinck).

### 4. 2 `.md` de bytes nulos ainda no disco (aguardando o OK do William)
`outros/idiota-fiodor-dostoievski.md` (1,64 MB, 1.642.640 nulos) e
`outros/anna-karenina-liev-tolstoi.md` (1,92 MB, 1.917.410 nulos). Os **arquivos
bons** existem (`dostoievski/O-Idiota-...`, `tolstoi/Anna-Karenina-...`) e a KB já
aponta para eles. Os nulos estão órfãos — apagar exige aprovação.

### 5. *O Caso Final de Sherlock Holmes* (1927) segue sem tradução PT-BR
Medido em 2026-11-07 (8 buscas no z-library, só EN/ES/FR/IT). Recomendação mantida: pular.

## Lint

`study-lint.py` → **0 erro(s) novo(s)**, 4 conhecidos no baseline, 1 aviso
(`esp:mnemos:tags-sem-kb` — tags sem KB no pool, pré-existente).

## Estado do acervo

1.589 documentos no índice · 692.240 trechos · 2.351 MB.
