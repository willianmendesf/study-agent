---
name: study-memos-sync
description: Envia planos de estudo, resumos de leitura, mapas conceituais textuais, listas de tópicos e relatórios para o Memos (memos.ison-duck.ts.net), onde o aluno lê pelo app. Use quando o usuário disser "manda pro memos", "envia pro memos", "posta no memos", "quero ler no app", ou após gerar qualquer conteúdo textual de estudo (plano, resumo, relatório). NÃO envia gráficos/imagens, PDFs crus, _corrupted, _incoming, _extracted, dumps > 100 KB, nem decisões/memórias/logs (esses ficam só no data/).
---

# study-memos-sync

Skill que posta **material de estudo consolidado** no **Memos** (servidor pessoal
`memos.ison-duck.ts.net`), onde o William lê no app mobile/desktop.

> **Regra do William (2026-11-05):** o Memos é a **biblioteca de leitura**.
> Entra material consolidado (plano, resumo, ficha, mapa, guia, devocional,
> exegese, índice, simulado). **NUNCA** entra decisão, diagnóstico de bug, log de
> pipeline, relato de commit, conversa de turno ou memória do agente — isso fica
> só em `data/` e vai só para o commit.
> Fonte de verdade: `data/perfil/memorias/memos-curadoria.md`.

---

## Quando usar

- Usuário pedir: "manda pro memos", "envia pro memos", "posta no memos",
  "quero ler no app", "sincroniza com memos".
- Após gerar conteúdo textual de estudo (ver "O que enviar").
- **Curadoria** (re-tag, dedup, limpeza): `scripts/curador-memos.py`.

## O que enviar

**SIM (texto, leitura comum no app):**

- Planos de estudo gerados (`plano-de-estudo-<tema>.md`)
- Resumos de leitura (`resumo-<livro>.md`)
- Mapos conceituais textuais (Mermaid → markdown tableado, não imagem)
- Fichas de leitura e fichas 8-pastas
- Listas de tópicos estruturadas
- Relatórios de quiz/prova (sem revelar gabarito — ver "Armadilha do gabarito")
- Índices e referências de módulos
- Devocionais, exegeses, guias de bolso

**NÃO:**

- Decisões, logs, diagnóstico de bug, conversa, memória do agente
- Gráficos (PNG, SVG, Mermaid renderizado) — o Memos não renderiza bem
- PDFs crus (binário)
- `_corrupted/`, `_incoming/`, `_extracted/`, `_to_organize/` (áreas técnicas)
- Dumps > 100 KB (o limite efetivo do Memos é **108.192 bytes**)
- Credenciais, tokens, paths absolutos sensíveis

## Taxonomia de tags (VALIDADA — 2026-11-05 20:30)

**UM eixo só: `#trilha`.** Mais o marcador `#study-agent`. Nada mais.

**Por que 1 eixo:** o **título do memo já diz a forma** — "AULA 20", "Devocional 13",
"Gabarito Quiz M1", "Plano de leitura". Taggear por forma é redundante com o título.
O que o título **não** diz é **a trilha** — a que assunto o material pertence.
É aí que a tag ganha utilidade: "onde está o material da prova?", "onde está a aula 15?".

> **Histórico:** a taxonomia anterior tinha 5 eixos (`estudo/`, `tipo/`, `fonte/`,
> `livro/`, `serie/`, `persona/`) e gerou **44 tags distintas** em 142 memos.
> `estudo/teologia` estava em 81 dos 142 → não filtrava nada. Trocada por 8 trilhas
> com **cobertura 143/143 (100%)**. Plano: `data/estudos/notas/memos-curadoria/plano-tags-memos.md`.

| tag | o que entra |
|---|---|
| `#devocional` | devocional diário — Salmos, Provérbios, adoração e confissão |
| `#exegese` | estudo bíblico — exegese, Etapa 0/1, contextualização, guias |
| `#aulas-portugues` | trilha de Português — aula 01→20 |
| `#plano-estudo` | planos, grades, roadmaps, roteiros (EBD/EBDI, currículo) |
| `#estudo-ipb` | preparação p/ a prova — comitê, autoavaliação, relatórios, questões |
| `#simulados` | as provas em si — para **fazer** |
| `#rampa-leitura` | rampa de ficção — o que ler, em que ordem |

**Exemplo real:**
```
#study-agent #exegese
```

**O que NÃO vai para o Memos (decisão do William, 2026-11-05):**
- **Gabarito de prova.** O gabarito fica com o IAM (`data/estudos/exercicios/gabaritos/`).
  O Memos tem a **prova, sem resposta**. O IAM corrige e informa o que errou e como acertar.
  → **NUNCA postar gabarito.** NUNCA postar `<details>Gabarito</details>`.
- Decisão · plano de curadoria/organização · diagnóstico de bug · log de pipeline ·
  relato de commit · conversa de turno · memória do agente.
  (Isso fica no `data/` e vai só para o commit.)

**NÃO USE:**

- Tags genéricas tipo `mes-2026-10`, `nota-de-estudo`, `tipo-plano`
- **Tags numéricas** (`182`, `140`, `16`, `31`) — ids de lista de aquisição. O
  Memos extrai hashtag de **qualquer** linha do corpo, então `#182` no meio de
  uma frase vira tag. Escreva `nº 182`.
- Tags técnicas de perfil/orquestrador (regras do kairos, checklists) — não
  pertencem ao Memos
- Tags repetidas em quase todas as memos (perde poder de filtragem)

**Regra de ouro da classificação:** a **tag antiga é mais confiável que o texto**.
O texto só entra como fallback, e só o título + 3 primeiras linhas (para não
classificar por menção casual a outro livro).

## Formato do memo

- **Título** (`# ` na primeira linha) — claro, sem emoji decorativo
- **Corpo** — markdown limpo, sem paths absolutos, sem códigos de erro, sem YAML bruto
- **Tags** — hashtag no fim do corpo, em uma linha só
- **Visibilidade** — PRIVATE por padrão

## Armadilhas do Memos (testadas de verdade — 2026-11-05)

| armadilha | comportamento real | o que fazer |
|---|---|---|
| **`tags` não é campo editável** | `PATCH {"tags": [...]}` → `invalid update path: tags` | re-tagar = **reescrever o `content`** com a linha de hashtags nova |
| **o uid tem sufixo completo** | `memos/3ER2zYRdjebVPMZirzG8G5` → usar `3ER2zYRdjebVPMZirz` dá 404 | usar o `name` **sem** o prefixo `memos/`, e com o sufixo inteiro |
| **o path não repete `memos/`** | `/api/v1/memos/memos/<uid>` → 404 | o path é `/api/v1/memos/<uid>` |
| **hashtag em qualquer linha vira tag** | `bloco **#182**` → tag `182`; `(#gama)` → tag `gama`; `#mu/nu` → tags `mu` **e** `mu/nu` | no corpo, `#` só pode ser título markdown. Use `nº 182` |
| **linha de tags antiga no meio do corpo** | continua gerando tags para sempre | remover **todas** as linhas de tags, não só a última |
| **`<details>` não renderiza** | o `<details><summary>Gabarito</summary>` vira texto puro → **o gabarito aparece** | **NUNCA poste gabarito.** Ele fica no `data/estudos/exercicios/gabaritos/` e o IAM corrige |
| **"✅" na linha da opção** | marca a resposta **na prova**, fora de qualquer `<details>` | limpar o "✅" de toda linha `- X) ... ✅` |
| **"✅" decorativo** | `✅` também é usado como "presente/OK" (`✅ No acervo`, `✅ Metadados`, `1:1-4 ✅`) | **NÃO remova às cegas** — quebra catálogo e comentário bíblico. Remova só o `✅` que está em linha de alternativa de prova |
| **tabela-resposta** `\| # \| Resposta \| …` | sobrevive à extração (não está dentro de `<details>`) | mover a tabela para o memo do gabarito |
| **`pageSize=200` estoura o timeout** | 45s → 0 bytes no tailnet | usar `pageSize=50` |
| **`pageToken` sem URL-encoding** | `invalid page token: illegal base64 data` | `quote(token, safe='')` |
| **a tag-pai é criada sozinha** | `#estudo/literatura` → tags `estudo` + `estudo/literatura` | não postar `estudo` à mão |
| **o Memos é compartilhado** | há memos de outro usuário/projeto na mesma instância | nunca re-taguear, nunca apagar memo de outro `creator` |

**Memos liga das 05:00 às 23:00 BRT** (fora disso dá timeout — não é falha de DNS).
Listagem completa (~387 memos) leva **~70s** → rodar em **background**, nunca no
`exec` (que corta em 60s).

## Configuração

URL + PAT ficam em `data/config-backup/memos/memos.env` (chmod 600, versionável no `data/`).

```
data/config-backup/memos/memos.env:
  MEMOS_URL=http://memos.ison-duck.ts.net/
  MEMOS_PAT=memos_pat_...
```

A skill **lê** esse arquivo; nunca imprime o PAT; nunca escreve o PAT em log.

## Uso

### Postar um arquivo .md como memo

```bash
bash .claude/skills/study-memos-sync/bin/memos-post.sh \
  --file "data/estudos/notas/ficcao-rampa-leitura/06-plano-consolidado.md" \
  --visibility PRIVATE \
  --tags "study-agent,rampa-leitura"
```

### Dry-run (não posta, só mostra o JSON)

```bash
bash .claude/skills/study-memos-sync/bin/memos-post.sh --dry-run --file "..."
```

### Curadoria (o Bibliotecário é o dono do Memos)

```bash
python3 scripts/curador-memos.py --auditar          # só relata
python3 scripts/curador-memos.py --aplicar          # re-tagueia (só do Study-Agent)
python3 scripts/curador-memos.py --dedup --limpar    # apaga cópias e lixo técnico
```

**Backup antes de qualquer escrita:**
`data/perfil/bibliotecario/backups-memos/memos-<data>.json`

## API Memos

Endpoint: `POST {MEMOS_URL}/api/v1/memos`

Headers:
- `Authorization: Bearer $MEMOS_PAT`
- `Content-Type: application/json`

Body (POST):
```json
{
  "content": "# título\n\ncorpo markdown aqui...\n\n#study-agent #exegese",
  "visibility": "PRIVATE"
}
```

Resposta (201 Created):
```json
{
  "id": 123,
  "name": "memos/123",
  "content": "...",
  "visibility": "PRIVATE",
  "creator": "users/...",
  "createTime": "..."
}
```

## Travas

- **PAT em log?** Nunca. Script usa `set +x`; erros vão pra stderr sem o valor.
- **Confirmação antes de postar**: a skill **não confirma** — é parte do fluxo do
  orquestrador. Se o usuário quiser confirmar antes, use `--dry-run`.
- **Deduplicação**: a skill não dedupa. Use `scripts/curador-memos.py --dedup`.
- **Rate limit**: Memos não documenta limite público, mas use com bom senso.
- **Tempo de resposta**: o tailnet é lento — a listagem de 380 memos leva ~30 s.
  Use `--max-time 90` no curl, não 25.

## Troubleshooting

| Erro | Causa | Solução |
|---|---|---|
| `401 Unauthorized` | PAT inválido/expirado | Rotacionar em Settings → My Access Tokens → Revoke + novo; atualizar `memos.env` |
| `Connection refused` / timeout | URL errada, VM off, ou **fora da janela 05-23h BRT** | `curl -v http://memos.ison-duck.ts.net/`; checar `TZ=America/Sao_Paulo date` |
| `JSON parse error` | Memos retornou HTML (proxy/login page) | Verificar URL sem trailing slash |
| `404` no PATCH | uid truncado ou `memos/` repetido no path | `/api/v1/memos/<uid>` com o sufixo completo |
| `invalid update path: tags` | tentando editar o campo `tags` | reescrever o `content` com hashtags novas |
| Arquivo > 100 KB | conteúdo grande demais | quebrar em seções; ou só guardar em KB local |

## Rotação do PAT

`Settings → My Access Tokens → Revoke` + criar novo. Atualizar `data/config-backup/memos/memos.env` e comitar.

Recomendado: rotacionar pelo menos 1× ao ano, ou imediatamente se exposto em chat/log.
