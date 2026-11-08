---
data: 2026-11-08
hora: 06:30-07:05 BRT
tipo: rodada-bibliotecario
---

# Rodada diaria de aquisicao — 2026-11-08 06:30 BRT

**Pedido (cron `fed05ac460f0a3d5`):** rodar `rodada-diaria.sh` (fases 0+1+2) e reportar
materiais baixados, gaps fechados, pendentes e lint. Corrigir erro novo de lint.

## Resultado

| item | valor |
|---|---|
| Materiais baixados | **0** (13 gaps medidos: 0 pendentes — cota preservada) |
| Gaps fechados | **0** (nenhum gap de area/comentario pendente) |
| Pendentes | **0** |
| Acervo | 1144 `.md` / 1351 materiais catalogados |
| Lint | **0 erro novo**, 4 conhecidos no baseline, 1 aviso |

**Por que 0 download:** os 13 gaps tematicos estao **saturados** — verifiquei os 50
candidatos um a um, e todos os 50 casam com arquivo real no acervo (`ja_no_acervo`
devolve caminho existente). Nao e dedup mascarando: e falta real de material novo.
Cota do z-library: 80/80 disponiveis (8 contas x 10), resetada a meia-noite UTC.

## Os 3 BUGS DE CAUSA (corrigidos, nao no sintoma)

### 1. `perfis.md` APAGADO pelo probe de permissao (o lint acusou)
O lint da rodada acusou `ERRO esp:bibliotecario:path:data/perfil/perfis.md
(especialista cita arquivo inexistente)`. Causa: em `scripts/liberar-permissoes.sh`,
o loop de verificacao usava **`data/perfil/perfis.md` (arquivo REAL)** como alvo de
`touch` + `rm -f`. Cada execucao do script APAGAVA o indice de especialistas.
**Regra: NUNCA usar arquivo real como alvo de probe.** Todo alvo e um `.probe`
descartavel; arquivo real so e conferido com `test -w`, sem tocar.
Corrigido + validado (rodei o script 3x, o arquivo sobreviveu).

### 2. FASE 2 crashava com `PermissionError`
`liberar-permissoes.sh` chownava so os **subdiretorios** (`data/biblioteca/*/`). Os
arquivos soltos na **raiz** (`canones-referidos-listas-leitura.md`,
`catalogo-compras.md`, `lista-aquisicao.md`) ficavam `root:root` — e o
`catalogar-automatico.py` morria ao ler um deles. A FASE 2 era um no-op silencioso.
Corrigido com `find ... -maxdepth 1 -type f -exec chown`.

### 3. Documentos de trabalho catalogados como se fossem livros
Com o bug 2 corrigido, o catalogador passou a ver 3 "livros orfaos" — mas eram
**documentos de trabalho do agente** (`catalogo-compras.md`, `triagem-aquisicao.md`,
`canones-referidos-listas-leitura.md`), e entraram na KB com
`formato_original: pdf/epub` — mentira no catalogo.
Corrigido: so material dentro de uma **subcategoria tematica** e livro
(`len(parts) <= len(BIB.parts) + 1` → pula). Revertidas as 3 entradas falsas
(`kb-fragmentos-livros` de 103 → 100 volumes).

## Bug que ja estava corrigido (confirmado)
O `NameError: ACCOUNTS` (que matava a FASE 1 desde 2026-11-05) segue corrigido —
rodei o gap `ingles` na mao e ele termina limpo ("0 adquirido", 5 candidatos
saturados).

## Licao
**"Rodada terminou com 0" pode ser o resultado correto — ou um no-op silencioso.**
A distincao se faz rodando a fase isolada e olhando o log, nao o resumo. Foi
exatamente assim que os 3 bugs apareceram: o log dizia "FIM" em todos os casos.

## Commits
- `4b2c29c` (data) — 3 bugs de causa + 88 arquivos · pushado
- `1f90df6` + `f190e32` (repo) — probe destrutivo + bit de execucao · pushados
