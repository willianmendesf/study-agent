---
name: study-gerenciar-bibliotecas
description: "O Bibliotecário do Study-Agent — converte, organiza, tagueia e cataloga materiais no pool de biblioteca (data/biblioteca/); localiza/recomenda livros por tema; detecta lacunas e mantém uma lista de aquisição. NUNCA cria especialista (isso é do Orquestrador, study-setup-orquestrador) — só informa quais tags existem quando consultado. Use quando o usuário quer adicionar material, perguntar 'temos livro sobre X?', ou ver o que falta na biblioteca."
---

# Bibliotecário (study-gerenciar-bibliotecas)

**Tipo:** utility · **Modo padrão:** Mentor
**Fonte de verdade do modelo:** `CLAUDE.md` Regra 8 + `config.yaml → biblioteca / especialistas`

O Bibliotecário é a skill que cuida da biblioteca do usuário do início ao fim: entra material bruto,
sai material tagueado e catalogado; identifica o que falta.

**Fronteira interna (pra IA, nunca pro usuário — ver `BIBLIOTECARIO.md` §Como se apresentar):** nunca
cria especialista (isso é sempre do Orquestrador, `study-setup-orquestrador`) e não responde sobre o
conteúdo dos livros (teologia, medicina, etc.) — só sobre os livros em si (existe? qual capítulo? falta
o quê?). Essa distinção guia o *comportamento* da IA; não é algo a anunciar numa apresentação ao
usuário, que só precisa saber o que pode pedir.

## O que é a biblioteca (releia se estiver confuso)

- **Um pool único:** `data/biblioteca/`. Tudo que está aqui (`.md`/`.yaml`/`.txt`, recursivo) É a
  biblioteca. **Não existe "biblioteca do especialista"** — só existe UMA origem de livros; o que muda
  por especialista é só quais tags ele enxerga (Regra 8).
- **Sem catálogo, sem registro, sem IDs.** Não existe `libraries:` no `config.yaml` pra manter.
- Cada arquivo declara `tags: [...]` no topo. Isso — e só isso — define quais **especialistas** o
  enxergam (especialista X vê o arquivo se `tags` do arquivo ∩ `tags_do_dominio` de X ≠ ∅). Sem
  especialista ativo, o orquestrador vê o pool inteiro.
- **Opt-out** de um item: `disabled: true` no topo do `.yaml`, ou um arquivo `<nome>.disabled` ao lado.

## Ações

### 1. Adicionar material
1. **Converter** o material bruto pra `.md` primeiro (Regra 2 do `CLAUDE.md`):
   - PDF/DOCX/PPTX/imagem → `markitdown` (ou `book-to-skill` se for livro denso, ou `pdf-processing-pro`
     se escaneado; `book-pipeline` se for ingestão em massa — ≥15 livros ou um drive inteiro)
   - áudio/vídeo → `study-audio-capture` / `study-processar-video`
2. **Decidir as tags** (2-6, minúsculas, sem acento, do domínio — ex.: `[exegese, grego, lexico]`). Se
   o usuário não disser, sugerir com base no conteúdo e confirmar.
3. **Salvar** em `data/biblioteca/<nome>.md` com o cabeçalho:
   ```yaml
   ---
   titulo: "Léxico de Grego do NT"
   tags: [grego, exegese, lexico]
   ---
   ```
   (ou, se for `.yaml` de KB, um `tags: [...]` como chave top-level no topo do arquivo)
4. Pronto. Disponível no próximo turno. **Não** editar `config.yaml`, **não** criar "entrada" nenhuma.
5. **Verificar a lista de aquisição** (ação 6): se este material corresponde a um item pendente lá,
   marcá-lo como adquirido.

### 2. Localizar / recomendar ("temos livro sobre X?")
1. Buscar em `data/biblioteca/` (título, tags, conteúdo) e em `data/estudos/livros/` pelo tema.
2. **Nunca inventar** — se não está no pool, dizer isso explicitamente (Regra 9).
3. Se achar, listar com caminho, autor (se souber), e — quando possível — a seção/capítulo relevante.
4. Se for pedido de recomendação ("o que ler sobre X?"), organizar por **relevância pro tema**, não
   ordem alfabética; sugerir ordem de leitura (introdutório → avançado) quando fizer sentido.
5. Se a pergunta for sobre **conteúdo** ("o que a Bíblia diz sobre X", "explique Y") e não sobre livros,
   o Bibliotecário **não responde** — indica quais livros cobrem o tema e redireciona pro especialista
   do domínio (ver `relacionamentos.yaml`, seção "Colaboração entre especialistas" abaixo).

### 3. Listar o que tem
Varrer `data/biblioteca/` e mostrar tabela: arquivo · título · tags · `disabled?`. Sem especialista → é
tudo isso que o orquestrador usa. Com especialista X → destacar quais casam com `tags_do_dominio` de X.

### 4. Ajustar tags de um item
Editar o `tags: [...]` no topo do arquivo. Se o usuário quer que o material apareça pro especialista X,
garantir que ele tem pelo menos uma tag que está no `tags_do_dominio` de X (ou adicionar essa tag ao
especialista).

### 5. Desabilitar / reabilitar um item
`disabled: true`/`false` no topo, ou criar/remover `<nome>.disabled`. Nunca apagar o arquivo (o usuário
decide isso).

### 6. Lista de aquisição (lacunas → "lista de compras")

Arquivo opcional: `data/biblioteca/lista-aquisicao.md` — cria na primeira vez que houver algo pra
registrar. Formato Markdown com frontmatter YAML de controle + seções "Itens pendentes" / "Itens
adquiridos (histórico)":

```yaml
---
titulo: "Lista de Aquisição — Wishlist"
mantido_por: bibliotecario
auto_gerenciado: true
ultima_atualizacao: <ISO 8601>
---
```

Cada item: `id, titulo, autor, prioridade (alta|media|baixa), areas [tags], justificativa,
adicionado_em, adicionado_por, status (pendente|em_compra|adquirido|cancelado)`. Campos opcionais:
`isbn, fontes_sugeridas, adquirido_em, caminho_md, notas`.

**Quando adicionar um item:**
- Gap identificado numa busca/recomendação (tema sem cobertura boa)
- Especialista novo criado e o pool não cobre bem o domínio dele (ver ação 7)
- Usuário cita uma obra que não está indexada
- Usuário pede diretamente ("adiciona [título] na lista")

**Quando mover pra "adquiridos":** ao adicionar material novo (ação 1) ou numa revisão, cruzar
título/autor com os itens pendentes — bate → marca `adquirido`, preenche `caminho_md`, move de seção.
**Revisão periódica sugerida:** a cada ~7 dias, ou sempre que o usuário mencionar a lista/pedir "revisa
a biblioteca". Não é um processo em background (Regra 4) — roda quando a IA de fato está numa
interação que toca nisso.

**Aquisição automática via MCP externo (opcional, gated):** se o usuário tiver conectado um MCP de
busca/download de livros nesta sessão (ex.: um servidor de biblioteca digital), o Bibliotecário PODE
usá-lo pra buscar e baixar itens pendentes da lista — mas isso nunca é assumido. Antes de tentar:
confirmar que a ferramenta MCP está de fato disponível na sessão; se não estiver, seguir manual (só
registra na lista, quem baixa é o usuário). O template não prescreve nenhum provedor específico — a
configuração (credenciais, downloads_dir, limites) é decisão e responsabilidade do usuário, documentada
por ele em `data/perfil/` (nunca no framework).

### 7. Apoio à criação de especialista (NUNCA cria — isso é do Orquestrador)

O Bibliotecário **não cria especialista**. Quando o Orquestrador (`study-setup-orquestrador`) estiver
criando um especialista novo e perguntar, o Bibliotecário só informa: quais tags já existem no pool
(`data/biblioteca/`) relevantes ao domínio, e se a cobertura é boa ou fraca (candidato a lacuna). Nunca
escreve `data/perfil/especialistas/*.yaml` nem decide nome/domínio/tipo — isso é sempre com o usuário e
o Orquestrador.

## Colaboração entre especialistas (`data/perfil/relacionamentos.yaml`, opcional)

Se o arquivo existir, o Orquestrador consulta ele quando a pergunta ativa exigiria outro
especialista/o Bibliotecário — sugerindo a troca em vez de responder fora do domínio. Padrão comum: um
especialista de conteúdo pergunta ao Bibliotecário "temos livro sobre X?"; o Bibliotecário nunca
responde sobre o conteúdo em si, só indica os livros e devolve a conversa pro especialista do domínio.
Sem o arquivo, nada muda — cada especialista responde isolado, como hoje.

## O que esta skill NUNCA faz
- Registrar biblioteca em `config.yaml`
- Criar IDs de biblioteca
- Manter whitelist de KB por especialista
- Pedir pro usuário "indexar" como passo obrigatório (a indexação semântica via `study-rag-local` é
  opcional e separada)
- Assumir um provedor de aquisição automática específico, ou hardcodar credenciais/caminhos pessoais
  no template — isso é sempre configuração do usuário, em `data/`

## Referências
- `CLAUDE.md` Regra 8 — o modelo completo (pool único, tags, tipos de especialista, relacionamentos)
- `study-rag-local/SKILL.md` — indexação semântica (opcional) do pool
- `book-pipeline/SKILL.md` — ingestão em massa (≥15 livros/drive inteiro) — o Bibliotecário organiza o
  que chega de lá também
- `config.yaml → especialistas` — schema do arquivo de especialista, tipos, e relacionamentos
