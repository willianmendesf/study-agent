# Rodada de ficção — 2026-11-13 (07:15 UTC / 04:15 BRT)

## Resultado

**0 livros baixados · 0 falhas · cota intacta (59 de 60 disponíveis).**
Não é falha: o catálogo está **94/94 adquirido**. A rodada não tinha o que fazer.

## Mas a rodada revelou 2 bugs reais + 3 arquivos corrompidos

### Bug 1 (grave, 4 rodadas mascaradas): `toks()` devolvia LISTA e matava a 2ª via

`scripts/pipeline-biblio.py` tem cópia própria de `toks()`, que devolvia
`list`. O score de `candidatos_ordenados` faz `alv_a & a` — interseção de
**conjuntos**, herdada do `pipeline-aquisicao.py` onde `toks()` devolve `set`.

Resultado: **`TypeError: unsupported operand type(s) for &: 'list' and 'list'`
em TODA chamada**, antes de avaliar o 1º candidato. A 2ª via (libgen, SEM
COTA) morria sempre — 4 rodadas seguidas com "2b indisponível":

| log | ocorrências de "2b indisponivel" |
|---|---|
| 2026-11-10 | 3 |
| 2026-11-11 | 5 |
| 2026-11-12 | 2 |
| 2026-11-13 | 1 |

A causa apareceu no log de 2026-11-11 (traceback) mas ninguém ligou os pontos
porque a mensagem final dizia "sem via alternativa" — como se a rede tivesse
caído. **Lição: mensagem genérica de erro engole bug de código.**

Corrigido: `toks()` devolve `set`. Validado com `candidatos_ordenados` real:
Retratos 1.42 (PT-BR) > Dubliners 1.02 (EN); Dom Quixote 5 candidatos PT.

**⚠️ ARMADILHA:** o `toks()` do `pipeline-biblio.py` tem assinatura
diferente do `pipeline-aquisicao.py` (este filtra `STOP` e usa
`re.findall`). Não são intercambiáveis cegamente — só o TIPO importa aqui.

### Bug 2: "2b indisponível" mentia em 4 situações diferentes

O `|| echo "2b indisponivel"` engolia: (a) baixou, (b) rodou OK e não havia
nada a baixar, (c) timeout, (d) erro real. Com catálogo saturado, (b) é o
caso normal — e era reportado como se a via estivesse quebrada. Agora o
`rodada-ficcao.sh` traduz o exit code (0 / 1 / 124 / outro).

### 3 arquivos corrompidos no acervo (achados pela auditoria do catálogo)

| arquivo | defeito | resolução |
|---|---|---|
| `Cervantes-Dom-Quixote.md` | 18 KB, **104 tracebacks** — não é o Quixote | **re-adquirido** (2,2 MB, 14.617 linhas, PT-BR) |
| `outros/anna-karenina-liev-tolstoi.md` | 1,9 MB de **bytes nulos** | KB + estado reapontados para `tolstoi/Anna-Karenina-Lev-Tolstoi.md` (bom) |
| `outros/idiota-fiodor-dostoievski.md` | 1,6 MB de **bytes nulos** | KB + estado reapontados para `dostoievski/O-Idiota-Fiodor-Dostoievski.md` (bom) |

O Dom Quixote foi baixado pela 2ª via recém-consertada (prova de que o fix
funciona) e subiu ao Orbit: **bookId 1849**, 1.347.088 bytes.

**Estado do catálogo após a correção: 94/94 com arquivo real, íntegro, 0 problemas.**

## Auditoria que vale repetir

Não confiar no campo `md`/`caminho_md` do estado — ele pode apontar para
arquivo que não existe ou que é lixo. O teste que funcionou:

```python
b = open(p,'rb').read()
b.count(0) > 1000                              # bytes nulos
b.decode('utf-8','ignore').count('Traceback (most recent call last)') > 0
```

E o **slug tem de ser o do `pipeline-aquisicao.py`** (`importlib`), não uma
reimplementação — o meu slug caseiro deu 94 "SEM-ESTADO" falsos.

## Pendente

1. **Catálogo saturado** — as 94 obras estão no acervo. Para a rodada voltar
   a render, é preciso **ampliar o catálogo** (`estante-william.yaml` +
   `lista-aquisicao.md` → `gerar-catalogo-ficcao.py`).
2. **2 arquivos de bytes nulos continuam no disco** (em `outros/`), agora
   órfãos: não são referenciados pela KB nem pelo estado. Apagar exige
   aprovação do William.
3. **O Caso Final de Sherlock Holmes (1927)** segue sem tradução PT-BR
   (8 buscas no z-library, só EN/ES/FR/IT).

## Lint

`study-lint: 0 erro(s) novo(s), 4 conhecido(s) no baseline, 1 aviso(s)` —
rodado 2x (antes e depois das correções).

## Commits

- `c414825` (repo study-agent): fix do `toks()`
- `cc89bf5` (data): Dom Quixote re-adquirido + KB + estado
- `0356834` (data): `rodada-ficcao.sh` traduz o exit code da 2ª via
