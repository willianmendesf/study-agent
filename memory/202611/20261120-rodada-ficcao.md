# Rodada de ficção — 2026-11-20

**Comando:** `data/perfil/bibliotecario/rodada-ficcao.sh --max 12`
**Resultado:** **16 obras adquiridas** (12 pela via primária z-library + 4 pela 2ª via libgen)
**Lint:** 0 erro novo (4 conhecidos no baseline)

## 1. O achado que mudou o dia: catálogo saturado

A primeira execução voltou **0 baixados / 0 falhas** — não era bug, era
**saturação real**: as 114 obras do `catalogo-ficcao.yaml` estavam todas
adquiridas e com arquivo íntegro no disco (verificado uma a uma).

Aplicada a regra permanente do William (2026-11-18): *rodada saturada não
encerra o dia — amplia o catálogo*. Medi o acervo (1.335 `.md` em
`data/biblioteca/**` + 2.279 títulos das KBs) contra 149 candidatos e achei
**130 obras de ficção ausentes**.

**Catálogo: 114 → 236 obras** (147 alta, 89 média/baixa), em
`scripts/gerar-catalogo-ficcao.py` (bloco "AMPLIACAO 2026-11-20").

## 2. As 16 obras baixadas

| Obra | Autor | Via |
|---|---|---|
| Memorial de Aires | Machado de Assis | zlib |
| A Mão e a Luva | Machado de Assis | zlib |
| Casa de Pensão | Aluísio Azevedo | zlib |
| Capitães da Areia | Jorge Amado | zlib |
| Dona Flor e Seus Dois Maridos | Jorge Amado | zlib |
| Corpo de Baile | João Guimarães Rosa | zlib |
| As Meninas | Lygia Fagundes Telles | zlib |
| Amor de Perdição | Camilo Castelo Branco | zlib |
| Ensaio sobre a Cegueira | José Saramago | zlib |
| A Cartuxa de Parma | Stendhal | zlib |
| Cândido | Voltaire | zlib |
| Antígona | Sófocles | zlib |
| As Cidades Invisíveis | Italo Calvino | zlib |
| Admirável Mundo Novo | Aldous Huxley | zlib |
| Carta ao Pai | Franz Kafka | zlib |
| A Insustentável Leveza do Ser | Milan Kundera | zlib |

Todas verificadas: **0 bytes nulos, 0 tracebacks**, entre 868 e 6.598 linhas
de prosa real. Todas em PT-BR.

## 3. Pendências

1. **BookOrbit fora do ar** — `No route to host` (192.168.15.26) durante toda a
   rodada. Os 16 ebooks ficaram em `data/biblioteca/_incoming/` e serão
   reenviados pelo cron `reenvio-orbit-automatico.sh` (a cada 15 min) quando o
   serviço voltar. Fila total: **37 arquivos**.
2. **10 obras falharam no download** (retry automático amanhã): Ficções,
   Fogo Morto, Gabriela Cravo e Canela, Hamlet, Ilíada, Lavoura Arcaica,
   Livro do Desassossego, Lucíola, Léxico Familiar, Macbeth.
3. **96 obras do catálogo novo ainda não tentadas** — entram nas próximas
   rodadas por prioridade (max 12/dia).
4. **Acervo de ficção dividido em 2 KBs** (defeito estrutural, não corrigido):
   `pipeline-aquisicao.py` cataloga em `kb-literatura.yaml` (129 materiais) e
   `pipeline-biblio.py` em `kb-literatura-mundial-classica.yaml` (63). As 12
   obras da via primária de hoje foram para a primeira; as 4 da 2ª via, para a
   segunda. Ambos têm tags de literatura, então a busca acha — mas o mesmo
   diretório está partido em duas bases. **Decisão do William antes de unificar.**
5. **Cota z-library**: 73 downloads disponíveis na largada; ~13 consumidos.

## 4. Ambiente

- `z-lib.gd` respondeu (domínio ativo detectado em runtime).
- `libgen.li` OK (2ª via, sem cota).
- `192.168.15.26` (BookOrbit) sem rota durante toda a rodada.
