# Rodada diária de aquisição — 2026-11-23 (06:30 UTC)

## Resultado

| Item | Valor |
|---|---|
| Materiais baixados | **0** |
| Gaps fechados | **0** |
| Gaps pendentes | **0** (13/13 áreas saturadas) |
| Lint | **0 erro novo** (4 conhecidos, 1 aviso) |
| Cota z-library | **preservada** (nenhum download tentado) |

Log: `data/perfil/bibliotecario/logs/rodada-2026-11-23.log`

## Fase 0 — metadado

- acervo: 1426 `.md`
- materiais nas KBs: **1635** · descartados 0 · dup 0 · yaml_err 0
- `MATERIAIS COM PATH: 1635 | PROBLEMAS: 0`
- tagueados nesta rodada: 0 · já tinham tags: 1407 · blocos YAML reparados: 0
- sem tag inferível: **19** (estável desde 2026-11-12)

## Gap analysis

- Acervo: 1514 arquivos · 311 tags distintas · invisíveis 20 (1,3%)
- **13/13 áreas com LACUNA = 0** (hermenêutica 92/12 · teol. bíblica 35/10 ·
  teol. sistemática 194/12 · contexto 80/15 · línguas 34/10 · prática 211/15 ·
  filosofia 47/12 · pregação 20/8 · português 44/12 · inglês 9/4 ·
  metodologia 22/8 · discipulado 92/12 · comentários 122/25)
- **Livros bíblicos SEM comentário: 0**

## Fase 1 — aquisição

`gaps medidos (pendentes no acervo): 0` → nada a adquirir.

## Prova de que a saturação é legítima (regra de 2026-11-10)

1. **Os 59 candidatos** de `rodape.CANDIDATOS` testados um a um com
   `ja_no_acervo(c[0], c[1], ...)` → **59/59 já no acervo**. Lista não-vazia +
   sensor confirmando = saturação real, não sensor quebrado (BUG V2 fechado).
2. **Serviço no ar:** `POST https://z-lib.gd/eapi/book/search` com
   `message=calvin&limit=1` → `{"success":1,"books":[...]}`. Portanto 0
   downloads NÃO é serviço fora do ar.

## Fase 2 — catálogo + reindex + lint

- `.md` do acervo sem entrada em NENHUMA KB: **0** → acervo 100% catalogado
- lint: 0 erro novo, 4 conhecidos no baseline, 1 aviso
  (`esp:mnemos:tags-sem-kb` — tags `anotacoes`, `schema`, `mapa`,
  `sintese-pessoal`, `catalogo-de-leitura`, `philosophy-of-mind`)

## Ampliação do catálogo (instrução permanente de 2026-11-18)

Saturação = ordem para ampliar, não fim de rodada. **17 alvos novos medidos e
verificados** (não entram como fantasma — BUG X):

- `ja_no_acervo()` = False **E** busca real no eAPI devolveu a obra com autor batendo.
- Descartado 1 alvo: "Teologia Sistemática" (Strong) → **já está no acervo**
  (`teologia-sistematica/Teologia-Sistematica-Strong-Augustus-H-Strong.md`).

| Área | Alvos novos |
|---|---|
| teologia-biblica | Schreiner *New Testament Theology* · House *Old Testament Theology* · Vos *Biblical Theology* |
| hermeneutica | Goldsworthy *Gospel-Centered Hermeneutics* |
| critica-textual | Metzger *The Text of the New Testament* · Tov *Textual Criticism of the Hebrew Bible* |
| contexto-historico | Malina *The New Testament World* · Ferguson *Backgrounds of Early Christianity* |
| preaching | Chapell *Christ-Centered Preaching* |
| pastoral | Bridges *The Christian Ministry* · Tan *Shepherding God's People* |
| apologetica | Koukl *Tactics* · Craig *Reasonable Faith* |
| portugues | Cegalla *Novíssima Gramática* · Neves *Gramática de Usos do Português* · Pestana *A Gramática para Concursos* |
| metodologia | Minayo *Pesquisa Social* |

Catálogo: **59 → 76 candidatos** · **17 fora do acervo** (prontos para a
próxima rodada). Lint rodado de novo depois da edição: **0 erro novo**.

## Armadilhas medidas hoje

- O eAPI do z-library **não responde a GET** (`/eapi/book/search?message=` devolve
  corpo vazio → `json` falha). Precisa ser **POST** com
  `-d "message=...&limit=N"`. Mesma armadilha de 2026-11-05/11.
- `ja_no_acervo()` casa **título + sobrenome do autor**, mas é generoso: "Strong"
  casou "Teologia Sistemática" com o arquivo real do Strong — confirmação manual
  necessária antes de declarar alvo novo (é o BUG V2/W ao contrário).
