---
name: study-memos-sync
description: Envia planos de estudo, resumos de leitura, mapas conceituais textuais, listas de tópicos e relatórios para o Memos (memos.ison-duck.ts.net), onde o aluno lê pelo app. Use quando o usuário disser "manda pro memos", "envia pro memos", "posta no memos", "quero ler no app", ou após gerar qualquer conteúdo textual de estudo (plano, resumo, relatório). NÃO envia gráficos/imagens, PDFs crus, _corrupted, _incoming, _extracted, dumps > 200 KB.
---

# study-memos-sync

Skill que posta conteúdo de estudo (planos, resumos, mapas textuais, relatórios) no **Memos** (servidor pessoal `memos.ison-duck.ts.net`), onde o aluno lê no app mobile/desktop.

## Quando usar

- Usuário pedir: "manda pro memos", "envia pro memos", "posta no memos", "quero ler no app", "sincroniza com memos".
- Após gerar conteúdo textual de estudo (ver "O que enviar").
- Orquestrador, ao final de fluxo de estudo (futuro): chama automaticamente.

## O que enviar (regra geral)

**SIM (texto, leitura comum no app):**

- Planos de estudo gerados (`plano-de-estudo-<tema>.md`)
- Resumos de leitura (`resumo-<livro>.md`)
- Mapas conceituais textuais (Mermaid → export pra markdown tableada, não a imagem)
- Listas de tópicos estruturadas
- Anotações pessoais de aula/aula-show
- Relatórios de quiz/prova (sem revelar gabarito)
- Índices e referências de módulos
- Flashcards em texto (frente/verso)

**NÃO:**

- Gráficos (PNG, SVG, Mermaid renderizado) — Memos não renderiza bem e o app mobile é ruim com imagens
- PDFs crus (binário)
- `_corrupted/`, `_incoming/`, `_extracted/`, `_to_organize/` (são áreas técnicas, não conteúdo final)
- Dumps > 200 KB (Memos não é substituto de KB; serve pra leitura leve)
- Credenciais, tokens, paths absolutos sensíveis

## Formato do memo

- **Título** (`# ` na primeira linha) — claro, com prefixo quando fizer sentido
  - Ex: `# estudo/hermeneia/1joao — Plano semana 3`
  - Ex: `# resumo: As Formas Elementares (Durkheim)`
- **Corpo** — markdown limpo, sem lixo (sem paths absolutos, sem códigos de erro, sem YAML bruto)
- **Tags** — via hashtag no final OU `;` na primeira linha (Memos aceita ambos)
  - Convenção: `#estudo/<especialista>/<modulo>` (ex.: `#estudo/hermeneia`, `#estudo/kairos`)
  - Adicionar `#study-agent` em todos os memos do flow
- **Visibilidade** — PRIVATE por padrão. O usuário muda no app se quiser público.

## Taxonomia de tags (regra aprendida 2026-10-01)

**Cinco eixos**, combináveis:

1. **`#grupo/<X>`** (sempre 1) — área ampla
   - `#grupo/estudo/teologia` — exegese, devocionais, hermenêutica, notas bíblicas
   - `#grupo/estudo/curriculo` — planos de curso/aula/programa (IPB Candidatura, seminário, EBD)
   - `#grupo/estudo/lingua` — gramática/sintaxe/redação
   - `#grupo/estudo/literatura` — teoria/crítica literária
   - `#grupo/gestao/tempo` — gestão pessoal (NÃO regras técnicas do kairos)

2. **`#tipo/<X>`** (sempre 1) — forma do conteúdo
   - `#tipo/plano` — plano de aula, plano de estudo, roadmap, descoberta
   - `#tipo/mapa` — mapa conceitual textual
   - `#tipo/exegese` — exegese de porção bíblica
   - `#tipo/devocional` — reflexão devocional
   - `#tipo/simulado` — prova/simulado
   - `#tipo/relatorio` — relatório de quiz/resultado
   - `#tipo/guia` — guia de bolso, manual
   - `#tipo/esboco` — esboço expositivo
   - `#tipo/indice` — índice, catálogo, grade curricular
   - `#tipo/nota` — nota livre, resumo de leitura, anotações

3. **`#fonte/<X>`** (opcional) — quando faz parte de um programa/curso estruturado
   - `#fonte/ipb-candidatura`
   - `#fonte/seminario-jmc`
   - `#fonte/ebd-ipbf`
   - `#fonte/hermeneia`

4. **`#livro/<X>`** (opcional) — livro bíblico sendo estudado
   - `#livro/oseias`
   - `#livro/1-joao`
   - `#livro/joao`
   - `#livro/romanos`

5. **`#modulo/<X>`** (opcional) — módulo do edital IPB
   - `#modulo/m1-portugues`
   - `#modulo/m2-redacao`
   - `#modulo/m3-literatura`
   - `#modulo/m4-ingles`
   - `#modulo/m5-simbolos`
   - `#modulo/m6-at`
   - `#modulo/m7-nt`
   - `#modulo/m8-revisao`

**NÃO USE:**
- Tags genéricas tipo `study-agent`, `mes-2026-10`, `tipo-plano`, `nota-de-estudo`
- Tags repetidas em quase todas as memos (perde poder de filtragem)
- Tags técnicas de perfil/orquestrador (regras do kairos, checklists do bibliotecário) — não pertencem ao Memos

**Exemplo real (memo "Exegese 1 João 2:12-17 — Hermes"):**
```
#grupo/estudo/teologia #tipo/exegese #livro/1-joao
```

## Configuração

URL + PAT ficam em `data/config-backup/memos/memos.env` (chmod 600, versionável no `data/`).

Estrutura:
```
data/config-backup/memos/memos.env:
  MEMOS_URL=http://memos.ison-duck.ts.net/
  MEMOS_PAT=memos_pat_...
```

A skill **lê** esse arquivo; nunca imprime o PAT; nunca escreve o PAT em log.

## Uso

### Postar um arquivo .md como memo

```bash
bash /home/opencode/study-agent/.claude/skills/study-memos-sync/bin/memos-post.sh \
  --file "data/estudos/plano-de-estudo-1joao.md" \
  --visibility PRIVATE \
  --tags "estudo/hermeneia,study-agent"
```

### Postar texto direto

```bash
bash /home/opencode/study-agent/.claude/skills/study-memos-sync/bin/memos-post.sh \
  --content "# Resumo: Durkheim cap. 7

Conteúdo do resumo aqui..." \
  --visibility PRIVATE \
  --tags "estudo/antropos,study-agent"
```

### Dry-run (não posta, só mostra o JSON que seria enviado)

```bash
bash /home/opencode/study-agent/.claude/skills/study-memos-sync/bin/memos-post.sh --dry-run --file "..."
```

## API Memos

Endpoint: `POST {MEMOS_URL}/api/v1/memos`

Headers:
- `Authorization: Bearer $MEMOS_PAT`
- `Content-Type: application/json`

Body (POST):
```json
{
  "content": "# título\n\ncorpo markdown aqui...",
  "visibility": "PRIVATE"
}
```

Body com resource list (para anexos futuros):
```json
{
  "content": "...",
  "visibility": "PRIVATE",
  "resources": []
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
- **Confirmação antes de postar**: a skill **não confirma** — é parte do fluxo do orquestrador. Se o usuário quiser confirmar antes, use `--dry-run` e peça confirmação explícita.
- **Deduplicação**: a skill não dedupa. Se rodar 2x com mesmo conteúdo, vai criar 2 memos. (Futuro: usar `POST /api/v1/memos:list` com filtro para checar antes.)
- **Rate limit**: Memos não documenta limite público, mas use com bom senso (não poste em loop).

## Troubleshooting

| Erro | Causa | Solução |
|---|---|---|
| `401 Unauthorized` | PAT inválido/expirado | Rotacionar em Settings → My Access Tokens → Revoke + novo; atualizar `memos.env` |
| `Connection refused` | URL errada ou VM off | `curl -v http://memos.ison-duck.ts.net/` |
| `JSON parse error` | Memos retornou HTML (proxy/login page) | Verificar URL sem trailing slash |
| Arquivo > 200 KB | Conteúdo grande demais | Quebrar em memos por seção; ou só guardar em KB local |

## Rotação do PAT

`Settings → My Access Tokens → Revoke` + criar novo. Atualizar `data/config-backup/memos/memos.env` e commitar.

Recomendado: rotacionar pelo menos 1× ao ano, ou imediatamente se exposto em chat/log.
