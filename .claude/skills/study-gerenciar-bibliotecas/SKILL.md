---
name: study-gerenciar-bibliotecas
description: "Cria, edita, lista e organiza bibliotecas de conhecimento (materiais indexados) com gate interativo. Use quando o usuário quer adicionar, listar, ou indexar material de estudo recorrente."
---

# Skill: Gerenciar Bibliotecas

**Tipo:** utility  
**Escopo:** framework  
**Persona recomendada:** Mentor  

## Objetivo

Criar, editar, listar e organizar **bibliotecas de conhecimento** com gatekeeping interativo. Cada biblioteca pode ser:
- **Global** — compartilhada em todo o framework
- **Skill-específica** — vinculada a uma etapa (estudo-fluxo-NN)
- **Persona-específica** — vinculada a uma persona (Professor, Tutor, etc.)
- **Materia-específica** — vinculada a um domínio (Anatomia, Programação, etc.)

## Ações

### 1. Criar Biblioteca
**Comando:** `/study-gerenciar-bibliotecas criar`

**Gate interativo:**
1. Pergunta: "Qual o **nome** da nova biblioteca?"
2. Pergunta: "Qual o **escopo**?"
   - [1] Global
   - [2] Skill-específica
   - [3] Persona-específica
   - [4] Materia-específica

3. Conforme a escolha:
   - Se Skill: "Qual skill?"
   - Se Persona: "Qual persona?"
   - Se Materia: "Qual materia?"

4. Pergunta: "**Descrição** (breve)?"
5. Pergunta: "Adicionar **fontes**?" (PDF, Markdown, URL, Dataset)
   - Se sim: repetir até que o usuário diga "não"
   - Cada fonte: tipo + path/url + já indexada?

6. Pergunta: "**Tags** (categorias, separadas por vírgula)?"
7. **Resultado:** 
   - Cria entrada em `.claude/config.yaml` (seção `libraries.<escopo>.<ref>`)
   - Retorna confirmação com ID da biblioteca

### 2. Listar Bibliotecas
**Comando:** `/study-gerenciar-bibliotecas listar [escopo] [ref]`

**Exemplos:**
- `/study-gerenciar-bibliotecas listar` — todas as bibliotecas
- `/study-gerenciar-bibliotecas listar global` — só globais
- `/study-gerenciar-bibliotecas listar skill estudo-fluxo-03-aprender` — só da skill de aprender
- `/study-gerenciar-bibliotecas listar persona Professor` — só do Professor
- `/study-gerenciar-bibliotecas listar materia Anatomia` — só de Anatomia

**Resultado:** tabela com nome, escopo, # de fontes, data de criação

### 3. Adicionar Fonte a Biblioteca Existente
**Comando:** `/study-gerenciar-bibliotecas adicionar-fonte <biblioteca-id>`

**Gate:** perguntar tipo de fonte, path/url, se já foi indexada

### 4. Indexar Biblioteca (semântica)
**Comando:** `/study-gerenciar-bibliotecas indexar <biblioteca-id>`

**Ação:** disparar KnowledgeBase para gerar embeddings, extrair conceitos, ligar a estágios/personas

### 5. Editar Biblioteca
**Comando:** `/study-gerenciar-bibliotecas editar <biblioteca-id>`

**Gate:** listar campos (nome, descrição, tags, scope_ref) e perguntar qual mudar

### 6. Deletar Biblioteca
**Comando:** `/study-gerenciar-bibliotecas deletar <biblioteca-id>`

**Confirmação:** perguntar certeza antes de remover

---

## Integração com KnowledgeBase

Após criar/adicionar fonte, sugerir:
- "Deseja **indexar** esta biblioteca agora?" (gerar embeddings, extrair conceitos)

Indexação escreve em:
- `.claude/rules/knowledge-base/<biblioteca-id>/`
  - `embeddings.json` (estrutura semântica)
  - `concepts.json` (conceitos extraídos)
  - `links.json` (relações com estágios/personas/materias)

---

## Integração com Sessão

Se o aprendiz está em uma materia/skill/persona, sugerir:
- "📚 Você tem {N} bibliotecas disponíveis para {contexto}. Deseja usá-las agora?"

---

## Arquivo de Saída

Alterações salvas em:
- `.claude/config.yaml` (seção `libraries`)
- `.claude/rules/knowledge-base/<biblioteca-id>/` (se indexada)

---

## Exemplo de Fluxo

```
usuário: /study-gerenciar-bibliotecas criar

IA: Qual o nome da nova biblioteca?
usuário: Anatomia Humana — Estrutura Óssea

IA: Qual o escopo?
   [1] Global
   [2] Skill-específica
   [3] Persona-específica
   [4] Materia-específica
usuário: 4

IA: Qual materia?
   - Anatomia
   - Fisiologia
   - Historia
   - Programacao
   - Custom
usuário: Anatomia

IA: Descrição (breve)?
usuário: Referências técnicas sobre o sistema esquelético humano

IA: Adicionar fontes?
usuário: Sim

IA: Tipo de fonte?
   [1] PDF
   [2] Markdown
   [3] URL
   [4] Dataset
usuário: 1

IA: Path do PDF?
usuário: ~/docs/anatomia-ossos.pdf

IA: Já foi indexada semanticamente?
usuário: Não

IA: Adicionar outra fonte?
usuário: Sim

[repete...]

IA: Tags (categorias, separadas por vírgula)?
usuário: esqueleto, osteologia, estrutura, básico

✅ Biblioteca criada: "Anatomia Humana — Estrutura Óssea"
   ID: anat-estr-ossea-001
   Escopo: materia/Anatomia
   Fontes: 3
   Tags: esqueleto, osteologia, estrutura, básico
   
🔍 Deseja indexar esta biblioteca agora? (vai gerar embeddings + extrair conceitos)
```
