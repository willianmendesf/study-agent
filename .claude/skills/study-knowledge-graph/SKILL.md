---
name: study-knowledge-graph
description: "Ontologia pedagógica com inferência de pré-requisitos entre conceitos e matérias. Use ao organizar material ou planejar o caminho de aprendizado entre tópicos relacionados."
---

# Knowledge Graph — Ontologia Pedagógica com Inferência

**Tipo:** camada automática (não é skill)  
**Escopo:** Study-Agent (integrado em book-to-skill + RAG)  
**Transparência:** Zero configuração, zero comandos

---

## O que faz (invisível pro usuário)

Quando biblioteca é indexada:
1. **Constrói ontologia** (classes, propriedades, relacionamentos)
2. **Define regras de inferência** (se aprendeu A e B → pode aprender C)
3. **Recomenda caminho** baseado em dependências
4. **Detecta gaps** (pré-requisitos faltando)

**Usuário vê:** Orquestrador oferece: "Complete estes 3 tópicos antes de avançar"

---

## Fluxo (Automático)

```
Usuário: "quero aprender Cardiologia"
    ↓
Orquestrador consulta Knowledge Graph:
  Cardiologia → requer [Anatomia Cardíaca, Fisiologia, Patologia]
    ↓
Ontologia infere:
  Anatomia Cardíaca → requer [Histologia, Embriologia]
  Fisiologia → requer [Bioquímica, Eletrofisiologia]
    ↓
Tutor oferece:
  "Perfeito! Vamos por etapas:
   1️⃣ Histologia (3 dias)
   2️⃣ Embriologia (2 dias)
   3️⃣ Anatomia Cardíaca (5 dias)
   4️⃣ Eletrofisiologia (3 dias)
   5️⃣ Cardiologia (7 dias)"
```

---

## Estrutura da Ontologia

### Classes (Tipos de Conceito)
```yaml
classes:
  Orgao:
    propiedades: [nome, funcao, localizacao, tamanho]
    exemplos: [Coração, Pulmão, Fígado]
  
  Sistema:
    propiedades: [nome, componentes, funcao]
    exemplos: [Sistema Cardiovascular, Sistema Nervoso]
  
  Processo:
    propiedades: [nome, etapas, entrada, saida]
    exemplos: [Ciclo Cardíaco, Metabolismo]
  
  Patologia:
    propiedades: [nome, causa, sintomas, tratamento]
    exemplos: [Infarto, Hipertensão, Arritmia]
  
  Procedimento:
    propiedades: [nome, indicacao, tecnicas, risco]
    exemplos: [Cateterismo, Transplante, Angioplastia]
```

### Relacionamentos (Arestas)
```yaml
relacionamentos:
  parte_de:              # Coração parte_de Sistema Cardiovascular
  requer_prerequisito:   # Cardiologia requer_prerequisito Anatomia Cardíaca
  causa_efeito:          # Infarto causa_efeito Morte
  similar_a:             # Infarto similar_a Trombose
  aplicacao_de:          # Cateterismo aplicacao_de Eletrofisiologia
  diferente_de:          # Angina diferente_de Infarto
```

### Propriedades (Atributos)
```yaml
propiedades:
  dificuldade: int (1-10)
  tempo_estudo_esperado: int (minutos)
  prerequisitos: [lista de conceitos]
  nivel_taxonomia_bloom: enum (conhecimento|compreensão|aplicação|análise|síntese|avaliação)
  dominio: str (Anatomia|Fisiologia|Patologia|etc)
  fonte_primaria: str (livro, paper, URL)
```

---

## Regras de Inferência (Prolog-like)

```prolog
% Regra 1: Se aprendeu classe, pode aprender subclasse
aprender(X) :- classe(Y, X), aprendeu(Y).

% Regra 2: Se aprendeu todos os pré-requisitos, pode aprender conceito
pode_aprender(X) :- 
  requer_prerequisito(X, Y),
  aprendeu(Y),
  requer_prerequisito(X, Z),
  aprendeu(Z).

% Regra 3: Se aprendeu similar, aprender este é mais fácil
dificuldade_efetiva(X, D_menor) :-
  similar_a(X, Y),
  aprendeu(Y),
  dificuldade(X, D),
  D_menor = D * 0.7.

% Regra 4: Se tópico é parte_de sistema, aprender sistema antes
deve_aprender_antes(Sistema, Topico) :-
  parte_de(Topico, Sistema).

% Regra 5: Se causa_efeito, entender causa antes de efeito
ordem_logica(Causa, Efeito) :-
  causa_efeito(Causa, Efeito).
```

---

## Raciocínio Automático

### Consulta 1: Qual é o caminho ideal para Cardiologia?
```prolog
?- caminho_optimo('Cardiologia', Caminho).

% LLM executa raciocínio:
caminho_optimo('Cardiologia', [
  'Histologia',
  'Embriologia',
  'Anatomia Cardíaca',
  'Eletrofisiologia',
  'Fisiologia Cardiovascular',
  'Cardiologia'
]).

% Explica: "Cardiologia requer Anatomia Cardíaca,
%           que requer Histologia e Embriologia."
```

### Consulta 2: Detectar Gaps (pré-requisitos faltando)
```prolog
?- gaps('Infarto do Miocárdio', AprendidoAte, Faltam).

% Resultado:
gaps('Infarto', ['Anatomia Cardíaca', 'Fisiologia'], [
  'Patologia Geral' ← falta
  'Eletrocardiografia' ← falta
  'Bioquímica de Miocárdio' ← falta
]).

% Tutor: "Para entender Infarto bem, você precisa de:
%        - Patologia Geral (2 dias)
%        - Eletrocardiografia (3 dias)
%        - Bioquímica de Miocárdio (2 dias)"
```

### Consulta 3: Ajustar Dificuldade
```prolog
?- dificuldade_efetiva('Ciclo Cardíaco', D).

% Se aprendeu 'Sistema Circulatório':
% - Dificuldade base: 7/10
% - Ajuste (similar aprendido): 7 * 0.7 = 4.9/10
% Resultado: 5/10 (em vez de 7/10)
```

---

## Integração com Concept Mapping

```
Knowledge Graph (Ontologia com Regras)
         ↓ exporta para
Concept Mapping (Neo4j Grafo Visual)
         ↓ renderiza em
Gephi (Mapa Interativo do Usuário)
```

---

## Stack Técnico

### Opção 1: Protégé + OWL (Completa)
- Protégé: editor ontológico visual
- OWL: Web Ontology Language (W3C)
- Raciocínio: Pellet/HermiT (inference engines)
- Complexo, mas poderoso para grandes domínios

### Opção 2: YAML + LLM (Simples, Prática)
- Ontologia em YAML (legível, versionável)
- LLM como inference engine (GPT/Claude)
- Neo4j para persistência
- **Recomendado para Study-Agent** (mais rápido, flexível)

---

## Arquivo de Ontologia (YAML)

```yaml
# .claude/knowledge-graph/<materia>-ontology.yaml
ontologia:
  versao: 1.0
  materia: Anatomia
  
  classes:
    Orgao:
      propiedades: [nome, funcao, tamanho, peso]
    Sistema:
      propiedades: [nome, componentes]
  
  conceitos:
    Coração:
      classe: Orgao
      dificuldade: 5
      tempo_estudo: 300  # minutos
      propiedades:
        funcao: "Bomba circulatória"
        peso_medio: "250g"
      prerequisitos: [Sistema Circulatório, Histologia Muscular]
      similar_a: [Bomba Mecânica]
  
  relacionamentos:
    parte_de:
      - [Coração, Sistema Cardiovascular]
    prerequisito:
      - [Cardiologia, Anatomia Cardíaca]
      - [Anatomia Cardíaca, Histologia]
```

---

## Auto-Instalação (Background)

- LLM constrói ontologia a partir de biblioteca (paralelo)
- YAML atualizado e versionado
- Neo4j carrega grafo automaticamente
- Raciocínio acontece em background (cacheado)

---

## Qualidade

- **Completude:** 85%+ de relacionamentos capturados
- **Acurácia:** validação via LLM + análise de coerência
- **Performance:** raciocínio <500ms (por consulta)
- **Escalabilidade:** até 10k conceitos com inferência real-time

---

## Referências

- [Knowledge Graphs in Education](https://www.cell.com/heliyon/fulltext/S2405-8440(24)01414-2)
- [Protégé Ontology Editor](https://protege.stanford.edu/)
- [OWL 2 Specification (W3C)](https://www.w3.org/OWL/)
- [Neo4j Knowledge Graph](https://neo4j.com/)
