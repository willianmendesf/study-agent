---
name: study-rag-local
description: "Indexação semântica local (busca por similaridade) sobre os materiais do usuário, com citação de fonte. Use para responder perguntas baseadas no material já indexado."
---

# RAG Local (Automático)

**Tipo:** camada automática (não é skill)  
**Escopo:** Study-Agent (integrado em Orquestrador)  
**Transparência:** Zero configuração, zero comandos

---

## O que faz (invisível pro usuário)

Quando biblioteca é adicionada:
1. **Extração automática**: `book-to-skill` extrai conceitos
2. **Indexação automática**: ChromaDB indexa semanticamente (background)
3. **Busca automática**: Orquestrador consulta RAG durante respostas
4. **Citações automáticas**: Respostas incluem fonte

**Usuário vê:** Orquestrador responde citando "segundo Gray's Anatomy..."

---

## Fluxo (Automático)

```
Usuário: "quero estudar anatomia"
    ↓
study-setup-orquestrador → seleciona biblioteca Gray's Anatomy
    ↓
book-to-skill → extrai 1200 conceitos (automático)
    ↓
RAG local → gera embeddings + indexa (background)
    ↓
Usuário: "o que é cardiopatia?"
    ↓
Orquestrador → "Deixa eu buscar..."
    ↓
RAG busca TOP-5 conceitos similares
    ↓
Orquestrador responde: "Segundo Gray's Anatomy, cardiopatia é..."
```

---

## Nenhum Comando

Não há comandos. Tudo é automático.
- Biblioteca adicionada? → RAG indexa nos bastidores
- Usuário pergunta? → RAG busca automaticamente
- Resposta inclui fonte? → Automático

---

## Estrutura de Dados

### Input: Conceitos (do book-to-skill)

```json
{
  "biblioteca_id": "grays-anatomy-001",
  "materia": "Anatomia",
  "conceitos": [
    {
      "id": "conceito-001",
      "titulo": "Sistema Cardiovascular",
      "texto": "O sistema cardiovascular é responsável por transportar sangue...",
      "fonte": "Gray's Anatomy, Capítulo 5, Página 234",
      "tags": ["coração", "sangue", "circulação"]
    },
    {
      "id": "conceito-002",
      "titulo": "Coração",
      "texto": "O coração é um órgão muscular que funciona como bomba...",
      "fonte": "Gray's Anatomy, Capítulo 5, Página 245",
      "tags": ["coração", "anatomia", "órgão"]
    }
  ]
}
```

### Storage: ChromaDB (local)

```
data/rag/
└── chroma.db (persistent SQLite database)
    └── collections:
        └── "estudo-anatomia" (embeddings + metadata)
            └── documents: ["Sistema Cardiovascular", "Coração", ...]
            └── embeddings: [[0.21, 0.45, ...], [0.32, 0.54, ...], ...]
            └── metadatas: [{"biblioteca_id": "grays-001"}, ...]
```

---

## Busca Semântica

```python
# Consulta
query = "como funciona o coração?"

# Resultado
[
  {
    "id": "conceito-002",
    "titulo": "Coração",
    "score": 0.92,  # similaridade
    "texto": "O coração é um órgão muscular que funciona como bomba...",
    "fonte": "Gray's Anatomy, Capítulo 5, Página 245"
  },
  {
    "id": "conceito-001",
    "titulo": "Sistema Cardiovascular",
    "score": 0.85,
    "texto": "O sistema cardiovascular é responsável por transportar sangue...",
    "fonte": "Gray's Anatomy, Capítulo 5, Página 234"
  }
]
```

**Orquestrador usa isso:**
```
Professor: "O coração é um órgão muscular que funciona como bomba... [Gray's Anatomy, Cap. 5]
E o sistema cardiovascular como um todo é responsável por transportar sangue... [Gray's Anatomy, Cap. 5]"
```

---

## Instalação

```bash
pip install chromadb sentence-transformers
```

**Modelos:**
- `sentence-transformers/all-MiniLM-L6-v2` (padrão, rápido, 22MB)
- `sentence-transformers/all-mpnet-base-v2` (qualidade premium, 430MB)

---

## Configuração

`.claude/skills/study-rag-local/config.yaml`:

```yaml
chromadb:
  path: ".claude/rag"           # persistent storage
  collection_prefix: "estudo"   # nome de coleções

embeddings:
  model: "all-MiniLM-L6-v2"     # modelo padrão
  dimension: 384                # tamanho do vetor
  device: "cpu"                 # ou: cuda

search:
  top_k: 5                      # resultados por busca
  score_threshold: 0.5          # mínimo de similaridade
  
batch:
  chunk_size: 512               # tokens por documento
  overlap: 50                   # tokens de sobreposição
```

---

## Workflow Completo

### 1. Indexação (automática após library-setup)

```bash
# study-gerenciar-bibliotecas cria biblioteca
/study-gerenciar-bibliotecas criar
  → Nome: "Gray's Anatomy"
  → Escopo: global
  → Arquivo: grays-anatomy.pdf

# book-to-skill extrai
  → 1200 conceitos extraídos

# study-rag-local indexa
  → Gera embeddings (1200 vetores de 384 dims)
  → Armazena em ChromaDB
  → "✓ Biblioteca indexada: 1200 conceitos"
```

### 2. Consulta (durante aprendizado)

```python
# Orquestrador faz pergunta
query = "me explica sobre o coração"

# RAG busca
top_5 = rag_local.buscar(query, top_k=5)

# Resultado inclui fonte
# Orquestrador responde citando: "segundo Gray's Anatomy..."
```

---

## Performance

| Operação | Tempo |
|---|---|
| Indexar 1000 docs | ~30-60s |
| Busca (top-5) | ~50-100ms |
| Usar modelo `all-mpnet-base-v2` | ~2x mais lento, melhor qualidade |

**Otimizações:**
- Batch indexing (não doc-a-doc)
- Caching de embeddings
- Índices pré-computados

---

## Integração com Orquestrador

```python
# No study-orquestrador
def responder_com_rag(pergunta: str, persona: str):
    # Busca conceitos relevantes
    conceitos = rag_local.buscar(pergunta, top_k=5)
    
    # Constrói prompt com fontes
    prompt = f"""
    Pergunta: {pergunta}
    
    Conceitos relacionados:
    {"\n".join([f"- {c['titulo']}: {c['texto'][:200]}... [Fonte: {c['fonte']}]" for c in conceitos])}
    
    Persona: {persona}
    Responda usando os conceitos acima como base.
    """
    
    # LLM responde
    return llm(prompt)
```

---

## Limpeza e Manutenção

```bash
# Ver estatísticas
/study-rag-local stats

# Remover biblioteca do RAG
/study-rag-local remover --biblioteca-id "grays-anatomy-001"

# Rebuild completo
/study-rag-local rebuild --modo paralelo --workers 4

# Backup periódico
/study-rag-local exportar --arquivo ~/.backup-rag-$(date +%Y%m%d).json
```

---

## Relacionados

- `study-gerenciar-bibliotecas` — cria bibliotecas
- `book-to-skill` — extrai conceitos
- `study-orquestrador` — consome RAG para responder
- `study-audio-capture` — transcrições também indexadas
