# Gate Interativo — Criar Biblioteca

## Protocolo

Usar `AskUserQuestion` para coletar metadados da biblioteca de forma progressiva e intuitiva.

### Stage 1: Nome e Escopo

```
Pergunta 1:
  question: "Qual o **nome** da nova biblioteca?"
  type: text
  placeholder: "Ex: Anatomia Humana — Estrutura Óssea"

Pergunta 2:
  question: "Qual o **escopo** desta biblioteca?"
  type: choice (single)
  options:
    [1] Global — compartilhada em todo o framework
    [2] Skill-específica — vinculada a uma etapa
    [3] Persona-específica — vinculada a uma persona
    [4] Materia-específica — vinculada a um domínio
  default: Global
```

### Stage 2: Referência de Escopo (condicional)

Se escolha != Global, perguntar pela referência:

```
Se Skill:
  question: "Qual **skill**?"
  type: choice (single)
  options: [estudo-fluxo-01-descobrir, ..., estudo-fluxo-06-dominio]

Se Persona:
  question: "Qual **persona**?"
  type: choice (single)
  options: [Professor, Tutor, Coach, Mentor, Quizzer, Expert]

Se Materia:
  question: "Qual **materia**?"
  type: choice (single)
  options: [Anatomia, Fisiologia, Historia, Programacao, Custom]
  (se Custom, perguntar nome customizado)
```

### Stage 3: Descrição

```
Pergunta:
  question: "**Descrição** (breve, 1-2 linhas)?"
  type: text
  placeholder: "Referências sobre sistema esquelético..."
```

### Stage 4: Fontes (repetitivo)

```
Pergunta inicial:
  question: "Adicionar **fontes** agora?"
  type: choice (single)
  options: [Sim, Não]

Se Sim:
  Loop até "Não adicionar mais":
    1. Tipo de fonte?
       type: choice (single)
       options: [PDF, Markdown, URL, Dataset]
    
    2. Path ou URL?
       type: text
       (validar: arquivo existe? URL é válida?)
    
    3. Já foi **indexada** semanticamente?
       type: choice (single)
       options: [Sim, Não]
    
    4. Adicionar outra fonte?
       type: choice (single)
       options: [Sim, Não]
```

### Stage 5: Tags

```
Pergunta:
  question: "**Tags** (categorias, separadas por vírgula)?"
  type: text
  placeholder: "esqueleto, osteologia, estrutura, básico"
```

### Stage 6: Confirmação e Indexação

```
Resumo:
  Nome: ...
  Escopo: ...
  Fontes: {N}
  Tags: ...
  
Pergunta:
  question: "Deseja **indexar** esta biblioteca agora? (vai gerar embeddings + extrair conceitos)"
  type: choice (single)
  options: [Sim, Não]
  
Se Sim:
  → disparar KnowledgeBase para indexar
  → escrever em .claude/rules/knowledge-base/<biblioteca-id>/
```

## Validação

| Campo | Regra |
|---|---|
| **Nome** | obrigatório, 3–100 caracteres, único por escopo+ref |
| **Escopo** | obrigatório, um de: global, skill, persona, materia |
| **Scope_ref** | obrigatório se escopo != global; deve existir em config.yaml |
| **Descrição** | opcional, 0–500 caracteres |
| **Fontes** | opcional, mas se vazio alertar "biblioteca sem fontes não será útil" |
| **Fonte.path_or_url** | se PDF/Markdown: arquivo deve existir; se URL: deve ser válida |
| **Tags** | opcional, 0–10 tags separadas por vírgula |

## Erros Comuns

| Erro | Ação |
|---|---|
| Nome duplicado em mesmo escopo+ref | alertar: "já existe biblioteca com esse nome aqui; use outro nome ou edite a existente" |
| Arquivo não encontrado | alertar: "PDF/Markdown não encontrado em {path}; verificar caminho" |
| URL inválida | alertar: "{url} não é uma URL válida" |
| Escopo_ref não existe | alertar: "Skill/Persona/Materia {ref} não existe em config.yaml" |

## Saída

Após validação com sucesso:

1. **Gerar ID da biblioteca** — formato: `{escopo}-{ref}-{contador:03d}`
   - Exemplos:
     - `global-referencias-001`
     - `skill-estudo-fluxo-03-aprender-002`
     - `persona-Professor-001`
     - `materia-Anatomia-003`

2. **Criar entrada em config.yaml**
   ```yaml
   libraries:
     {escopo}:
       {ref}: [
         {
           name: "...",
           scope: "...",
           scope_ref: "...",
           description: "...",
           sources: [...],
           tags: [...],
           created_at: "ISO-datetime",
           created_by: "usuario",
           metadata: { ... }
         }
       ]
   ```

3. **Confirmar ao usuário**
   ```
   ✅ Biblioteca criada com sucesso!
      ID: {id}
      Nome: {nome}
      Escopo: {escopo}/{ref}
      Fontes: {N}
      Tags: {tags}
   
   📚 Próximos passos:
      • Usar esta biblioteca no estágio correspondente
      • Indexar semanticamente (gerar embeddings)
      • Adicionar mais fontes conforme necessário
   ```

4. **Se escolheu indexar:**
   - Disparar KnowledgeBase (skill `study-indexar-conhecimento`)
   - Gerar embeddings, extrair conceitos, ligar a estágios
   - Escrever em `.claude/rules/knowledge-base/{id}/`
