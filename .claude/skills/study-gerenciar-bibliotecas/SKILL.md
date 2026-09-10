---
name: study-gerenciar-bibliotecas
description: "Adiciona, organiza, lista e etiqueta materiais no pool de biblioteca (data/biblioteca/). Não registra nada em lugar nenhum — só converte, salva na pasta e põe as tags. Use quando o usuário quer adicionar material de estudo, ver o que já tem na biblioteca, ou ajustar tags/especialistas."
---

# Gerenciar Biblioteca

**Tipo:** utility
**Modo padrão:** Mentor
**Fonte de verdade do modelo:** `CLAUDE.md` Regra 8 + `config.yaml → biblioteca / especialistas`

## O que é a biblioteca (releia se estiver confuso)

- **Um pool único:** `data/biblioteca/`. Tudo que está aqui (`.md`/`.yaml`/`.txt`, recursivo) É a biblioteca.
- **Sem catálogo, sem registro, sem IDs.** Não existe `libraries:` no `config.yaml` pra manter.
- Cada arquivo declara `tags: [...]` no topo. Isso — e só isso — define quais **especialistas** o enxergam
  (especialista X vê o arquivo se `tags` do arquivo ∩ `tags_do_dominio` de X ≠ ∅). Sem especialista ativo,
  o orquestrador vê o pool inteiro.
- **Opt-out** de um item: `disabled: true` no topo do `.yaml`, ou um arquivo `<nome>.disabled` ao lado.

## Ações

### 1. Adicionar material
1. **Converter** o material bruto pra `.md` primeiro (Regra 2 do `CLAUDE.md`):
   - PDF/DOCX/PPTX/imagem → `markitdown` (ou `book-to-skill` se for livro denso, ou `pdf-processing-pro` se escaneado)
   - áudio/vídeo → `study-audio-capture` / `study-processar-video`
2. **Decidir as tags** (2-6, minúsculas, sem acento, do domínio — ex.: `[exegese, grego, lexico]`). Se o
   usuário não disser, sugerir com base no conteúdo e confirmar.
3. **Salvar** em `data/biblioteca/<nome>.md` com o cabeçalho:
   ```yaml
   ---
   titulo: "Léxico de Grego do NT"
   tags: [grego, exegese, lexico]
   ---
   ```
   (ou, se for `.yaml` de KB, um `tags: [...]` como chave top-level no topo do arquivo)
4. Pronto. Disponível no próximo turno. **Não** editar `config.yaml`, **não** criar "entrada" nenhuma.

### 2. Listar o que tem
Varrer `data/biblioteca/` e mostrar tabela: arquivo · título · tags · `disabled?`. Sem especialista → é
tudo isso que o orquestrador usa. Com especialista X → destacar quais casam com `tags_do_dominio` de X.

### 3. Ajustar tags de um item
Editar o `tags: [...]` no topo do arquivo. Se o usuário quer que a KB apareça pro especialista X, garantir
que ela tem pelo menos uma tag que está no `tags_do_dominio` de X (ou adicionar essa tag ao especialista).

### 4. Desabilitar / reabilitar um item
`disabled: true`/`false` no topo, ou criar/remover `<nome>.disabled`. Nunca apagar o arquivo (o usuário
decide isso).

### 5. Criar um especialista
1. Perguntar: nome (slug), título, domínio, como o usuário vai chamá-lo (`quando_ativar`), e as
   `tags_do_dominio` (as tags de biblioteca que ele cobre).
2. Escrever `data/perfil/especialistas/<nome>.yaml` com o schema de `config.yaml → especialistas.schema`.
3. Não precisa mexer em biblioteca nenhuma — as KBs que já têm tag casando já aparecem pra ele.

## O que esta skill NUNCA faz
- Registrar biblioteca em `config.yaml`
- Criar IDs de biblioteca
- Manter whitelist de KB por especialista
- Pedir pro usuário "indexar" como passo obrigatório (a indexação semântica via `study-rag-local` é
  opcional e separada)

## Referências
- `CLAUDE.md` Regra 8 — o modelo completo
- `study-rag-local/SKILL.md` — indexação semântica (opcional) do pool
- `config.yaml → especialistas` — schema do arquivo de especialista
