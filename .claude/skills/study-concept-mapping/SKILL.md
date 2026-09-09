---
name: study-concept-mapping
description: "Gera mapa conceitual visual do tópico (pré-requisitos, relações entre conceitos, estrutura). Use ao descobrir um tópico novo ou organizar material complexo."
---

# Concept Mapping — Mapeamento Conceitual Automático

**Tipo:** camada automática (não é skill)  
**Escopo:** Study-Agent (integrado em estágio 01-descobrir + 02-organizar)  
**Transparência:** Zero configuração, zero comandos

---

## O que faz (invisível pro usuário)

Quando biblioteca é adicionada ou tópico é iniciado:
1. **Extrai conceitos** do RAG + materiais
2. **Detecta relacionamentos** (pré-requisito, causa-efeito, similaridade)
3. **Visualiza grafo** de tópicos
4. **Sugere caminho** de aprendizado baseado em dependências

**Usuário vê:** Mapa visual: "começa por A e B, então aprende C, D"

---

## Fluxo (Automático)

```
Usuário: "vou estudar Anatomia Cardiovascular"
    ↓
book-to-skill extrai conceitos + relações:
  {
    "Coração": {
      "pré-requisitos": ["Sistema Circulatório"],
      "aplicações": ["Cardiologia", "Cirurgia Cardíaca"],
      "similar_a": ["Bomba Mecânica"]
    }
  }
    ↓
Concept Mapping cria grafo Neo4j:
  Nó: "Coração" (properties: tipo=órgão, dificuldade=5/10)
  Aresta: "pré-requisito" → "Sistema Circulatório"
  Aresta: "aplicação" → "Cardiologia"
    ↓
Gephi renderiza visualmente:
  [Sistema Circulatório]
          ↓
      [Coração] ← → [Bomba Mecânica]
          ↓
    [Cardiologia] [Cirurgia]
    ↓
Tutor (estágio 01): "Deixa eu desenhar para você entender melhor"
    ↓
Usuário: [vê mapa interativo com nós e arestas]
```

---

## Estrutura do Grafo

### Nós (Conceitos)
```yaml
concept:
  id: "coração-001"
  titulo: "Coração"
  definição: "Órgão muscular que funciona como bomba"
  fonte: "Gray's Anatomy, Cap. 5"
  dificuldade: 5/10
  domínio: "Anatomia"
  tags: [órgão, cardiovascular, músculo]
```

### Arestas (Relacionamentos)
```yaml
relationships:
  prerequisito:
    - "Coração" ← "Sistema Circulatório"
    - "Coração" ← "Histologia Muscular"
  
  causa_efeito:
    - "Coração Saudável" → "Circulação Adequada"
  
  similaridade:
    - "Coração" ≈ "Bomba Mecânica" (analogia)
  
  aplicacao:
    - "Coração" → "Cardiologia"
    - "Coração" → "Cirurgia Cardíaca"
```

---

## Visualizações (por estágio)

### Estágio 01-Descobrir (Tutor)
- **Mapa geral:** todos os conceitos + relações
- **Destaque:** nó raiz (tópico principal)
- **Interativo:** clicar → ver detalhes de cada conceito
- **Sugestão:** "comece por estes 3 pré-requisitos"

### Estágio 02-Organizar (Professor)
- **Hierarquia:** pré-requisitos acima, aplicações abaixo
- **Clustering:** conceitos similares próximos
- **Cores:** por domínio ou dificuldade
- **Metadados:** quantidade de documentos por conceito

### Estágio 03-Aprender (Professor)
- **Foco progressivo:** destacar cada conceito conforme ensinado
- **Breadcrumb:** mostrar "você está aqui no mapa"
- **Conexões:** destacar como este tópico se liga ao anterior

### Estágio 05-Testar (Quizzer)
- **Gaps visuais:** conceitos com <70% acerto destacados em vermelho
- **Sugestão:** "você dominou A, B, C; revise D antes de avançar"

---

## Stack Técnico

### Neo4j (Graph Database)
- Armazena grafo conceitual persistentemente
- Queries: "qual caminho de A até B com N saltos?"
- Inferência: "se aprendeu A, B, C pode aprender D?"

### Gephi (Visualização)
- Renderiza grafo com layout força
- Detecta comunidades (clusters de conceitos)
- Exporta para SVG/JSON

### Arquivo Persistente
- `data/concept-maps/<materia>-graph.yaml`
- Versionado no git (auditável)
- Atualizado a cada nova biblioteca

---

## Auto-Instalação (Background)

- LLM instala `neo4j-python-driver` + `gephi` wrapper
- Primeira vez: criar banco local (Neo4j Community Edition)
- Background: indexar grafo em paralelo

---

## Integração com RAG

```python
# Quando RAG indexa novo conceito:
concept = {
    "título": "Coração",
    "texto": "...",
    "fonte": "Gray's Anatomy"
}

# Concept Mapping extrai relações via LLM:
relationships = llm_extract_relationships(concept)
# Output: [pré-requisito: Sistema Circulatório, ...]

# Adiciona ao Neo4j:
graph.create_node(concept)
for rel in relationships:
    graph.create_edge(concept, rel.target, rel.type)
```

---

## Qualidade

- **Completude:** grafo abrange 90%+ das relações
- **Acurácia:** validação manual + LLM confirm
- **Performance:** queries <100ms
- **Escalabilidade:** até 50k conceitos sem degradação

---

## Referências

- [Neo4j Community Edition](https://neo4j.com/)
- [Gephi - Graph Visualization](https://gephi.org/)
- [Knowledge Graphs in Education](https://www.cell.com/heliyon/fulltext/S2405-8440(24)01414-2)
