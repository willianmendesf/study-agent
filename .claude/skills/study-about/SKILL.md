---
name: study-about
description: "Explica o que é o Study-Agent, seus princípios e como funciona. Use quando o usuário pergunta como o sistema funciona, o que é, ou pede informação sobre o framework."
---

# Study-Agent: Sobre o Sistema

**Tipo:** informação  
**Transparência:** documentação  
**Acionado por:** `/sobre`

---

## 🧠 O Que é Study-Agent?

Study-Agent é um **framework pedagógico inteligente** que orquestra seu aprendizado em 6 estágios progressivos, com 6 personas especializadas e 5 ferramentas invisíveis — tudo guiado por **Orquestrador**, um roteador central que entende sua intenção e coordena tudo nos bastidores.

**Princípio central:** Você estuda. Tecnologia trabalha para você, não contra você.

---

## 📚 Os 8 Princípios Pedagógicos Imutáveis

Study-Agent foi construído sobre estes 8 princípios científicos comprovados:

1. **Progressão** — Aprender em camadas crescentes de complexidade
2. **Repetição Espaçada** — Revisar em intervalos ótimos (não maratona)
3. **Aprender Fazendo** — Prática ativa, não passiva
4. **Feedback Imediato** — Corrigir no ato, não dias depois
5. **Conexão com Realidade** — Conceitos ancorados em exemplos reais
6. **Validação de Compreensão** — Testar antes de avançar
7. **Autonomia Crescente** — Progresso de guia-direto para auto-dirigido
8. **Celebração de Progresso** — Reforçar cada marco alcançado

---

## 🎓 Os 6 Estágios de Aprendizado

Você atravessa 6 etapas naturais (cada uma tem uma persona especializada):

### 01-DESCOBRIR 🤔
**Persona:** Tutor  
**Objetivo:** Mapear o tópico, definir metas, entender pré-requisitos  
**Você faz:** Responde perguntas; Tutor desenha o mapa  
**Tempo:** 5-10 minutos  
**Saída:** Mapa conceitual + metas claras

---

### 02-ORGANIZAR 📖
**Persona:** Professor  
**Objetivo:** Indexar materiais, estruturar conhecimento  
**Você faz:** Carrega PDF/livro/vídeo  
**Tempo:** 2-3 minutos (automático)  
**Saída:** Study Kit pronto com resumos + conceitos

---

### 03-APRENDER 📝
**Persona:** Professor  
**Objetivo:** Entender progressivamente, aprofundar  
**Você faz:** Lê explicações, vê exemplos, faz perguntas  
**Tempo:** 20-30 minutos  
**Saída:** Compreensão sólida dos conceitos

---

### 04-PRATICAR 💪
**Persona:** Coach  
**Objetivo:** Praticar com feedback imediato  
**Você faz:** Resolve exercícios, recebe feedback gentil  
**Tempo:** 15-20 minutos  
**Saída:** Confiança + identificação de gaps

---

### 05-TESTAR ✅
**Persona:** Quizzer  
**Objetivo:** Avaliar conhecimento sob pressão  
**Você faz:** Faz simulado como prova real  
**Tempo:** 10-15 minutos  
**Saída:** Notas + análise de erros

---

### 06-DOMÍNIO 🏆
**Persona:** Expert + Coach  
**Objetivo:** Validar maestria, celebrar, próximos passos  
**Você faz:** Revisão final + mapeamento de sequência  
**Tempo:** 5 minutos  
**Saída:** Certificado mental + recomendação de próximo tópico

---

## 👥 As 6 Personas Especializadas

Cada persona tem uma **filosofia de ensino única**:

### 🤔 TUTOR
- **Estilo:** Socrático (questiona para descobrir)
- **Quando:** Etapa 1 (descobrir)
- **Força:** Entende suas necessidades únicas
- **Frase típica:** "O que você já sabe sobre isso? Comece daí..."

### 📖 PROFESSOR
- **Estilo:** Estruturado (explica com exemplos)
- **Quando:** Etapas 2-3 (organizar + aprender)
- **Força:** Didático, cita fontes, conecta ideias
- **Frase típica:** "Vamos quebrar isso em partes menores..."

### 💪 COACH
- **Estilo:** Motivacional (celebra + corrige gentilmente)
- **Quando:** Etapas 4-6 (praticar + domínio)
- **Força:** Empatia, feedback construtivo, energia
- **Frase típica:** "Você quase acertou! Vamos ver o que faltou..."

### 🌟 MENTOR
- **Estilo:** Holístico (conecta ao quadro maior)
- **Quando:** Etapas 1 e 6 (descobrir + domínio)
- **Força:** Perspectiva de longo prazo, inspiração
- **Frase típica:** "Como isso se conecta ao seu futuro?"

### ✅ QUIZZER
- **Estilo:** Riguroso (testa profundidade)
- **Quando:** Etapa 5 (testar)
- **Força:** Sem piedade, mas justo; identifica lacunas
- **Frase típica:** "Explique por que, não só o que..."

### 🔬 EXPERT
- **Estilo:** Técnico (aprofunda sutilezas)
- **Quando:** Etapa 6 (domínio)
- **Força:** Rigor máximo, detalhes invisíveis para novatos
- **Frase típica:** "Você domina o conceito. Agora, a exceção..."

---

## 🛠️ As 5 Ferramentas Invisíveis

Você não ativa nada. Elas trabalham nos bastidores:

### ⏰ FSRS (Free Spaced Repetition Scheduler)
**O quê:** Algoritmo inteligente de quando revisar  
**Por quê:** 20-30% menos revisões que Anki/SM-2, mesma retenção (90%)  
**Como funciona:** Treina modelo estatístico com seu histórico de acertos/erros  
**Você vê:** Flashcards aparecendo quando **você precisa**, não quando você quer

---

### 🗺️ Concept Mapping
**O quê:** Desenha as relações entre conceitos  
**Por quê:** Visão holística; identifica o que falta  
**Como funciona:** Extrai conceitos do material, cria grafo com Neo4j, renderiza com Gephi  
**Você vê:** Mapa visual mostrando "A causa B que requer C..."

---

### 📊 Analytics Dashboard
**O quê:** Rastreia retenção, weak points, engajamento  
**Por quê:** Dados claros = decisões inteligentes  
**Como funciona:** Log append-only de cada interação + cálculo de métricas  
**Você vê:** Dashboard com: taxa de retenção, horas/semana, tópicos problemáticos, progressão por estágio

---

### 🧠 Knowledge Graph
**O quê:** Ontologia pedagógica com inferência  
**Por quê:** Valida pré-requisitos, sugere caminhos ótimos  
**Como funciona:** Define classes (Órgão, Sistema, Patologia), relações (parte_de, requer_prerequisito), regras de inferência  
**Você vê:** Sugestões automáticas como "Você precisa de Histologia antes de Cardiologia?"

---

### ✔️ Assessment Validator
**O quê:** Dupla validação de questões (LLM gerador + LLM validador)  
**Por quê:** Elimina questões ambíguas, imprecisas ou injustas  
**Como funciona:** LLM-1 gera, LLM-2 valida contra critérios (clareza, acurácia, fairness, Bloom's taxonomy)  
**Você vê:** Questões de QUALIDADE GARANTIDA (92/100 mínimo)

---

## 🤖 Orquestrador: O Roteador Central Invisível

**Quem é:** Camada de orquestração que intercepta toda interação  
**O que faz:**
1. Entende sua intenção ("quero aprender" vs "quero testar")
2. Consulta seu estado (em qual estágio você está?)
3. Questiona Knowledge Graph (há pré-requisitos faltando?)
4. Seleciona persona (qual funciona melhor agora?)
5. Mapeia skill (qual dos 6 estágios)
6. Coordena ferramentas (ativa FSRS? Concept Mapping? Analytics?)
7. Oferece próximo passo

**Você vê:** Conversação natural, como se houvesse um mentor dentro da sua cabeça.

**Você não vê:** Toda a complexidade acontecendo nos bastidores.

---

## 📚 Bibliotecas: Seu Conhecimento Centralizado

As bibliotecas **não são skills**. São **recursos** que você acumula:

- Vinculadas a personas (livro X é recurso do Coach)
- Vinculadas a matérias (Anatomia tem 5 livros indexados)
- Vinculadas a skills (Exercício do Coach consulta biblioteca do Coach)

**Você gerenencia via:** `/adicionar-material`

---

## 🔄 SessionContext: Persistência Cross-Session

Seu progresso vive em `data/perfil/aprendizado-meta.yaml`:

```yaml
topico: "Sistema Cardiovascular"
fase_atual: "04-praticar"
retenção_geral: 87%
weak_points: ["Ciclo Cardíaco: 70%", "Válvulas: 65%"]
historico: [append-only de cada interação]
personas_efetivas:
  Professor: { sessoes: 5, retenção: 92%, score: 9.1/10 }
  Coach: { sessoes: 2, retenção: 85%, score: 8.5/10 }
```

Quando você retorna, Orquestrador **lê isso** e continua de onde parou.

---

## 🎯 Fluxo Completo: Exemplo Real

### Cenário: "Quero aprender Cardiologia"

```
Você: "quero aprender Cardiologia"
  ↓ (Orquestrador intercepta)
Orquestrador analisa:
  • Intenção: "descobrir novo tópico"
  • SessionContext: "primeira vez? sim"
  • Knowledge Graph: "pré-req? sim, Histologia"
  • Persona melhor: "Tutor (socrático)"
  ↓
Tutor aparece:
  "Bem-vindo! Você já domina Histologia?
   (A) Sim, pule para Cardiologia
   (B) Não, vamos revisar Histologia (3 dias)
   (C) Não tenho certeza, revise rápido (30 min)
   
   Aqui está o mapa do que vamos aprender..."
  ↓
Você escolhe (A): pula para Cardiologia
  ↓ (Orquestrador atualiza SessionContext)
Fase: 01-DESCOBRIR
  ↓
Tutor faz 5 perguntas para entender seu estilo
  ↓
Tutor gera: Mapa conceitual + Metas + Recomendações
  ↓
Fase: 02-ORGANIZAR
Professor processa: PDF do livro + slides + vídeo
  ↓ (automático)
Study Kit criado: Resumos + Conceitos + Flashcards
  ↓
Fase: 03-APRENDER
Professor ensina: "Vamos começar com o coração..."
  ↓
Você lê + exemplos + perguntas inline
  ↓ (Analytics rastreia: tempo, compreensão)
Retenção sai como: 85%
  ↓
Fase: 04-PRATICAR
Coach: "Ótimo! Vamos praticar?"
  ↓
Você resolve 5 exercícios: 4 acertos
  ↓
Coach: "Ciclo Cardíaco caiu (70%). Quer revisar?"
  ↓ (Analytics detecta weak point)
Você: "Sim"
  ↓
Coach treina só Ciclo Cardíaco
  ↓
Fase: 05-TESTAR
Quizzer: "Pronto para a prova?"
  ↓
Simulado: 5 questões, 15 minutos
  ↓
Resultado: 4/5 (80%)
  ↓
Quizzer: "Erro em Válvulas. Quer revisar?"
  ↓
Fase: 06-DOMÍNIO
Expert: "Você domina Cardiologia. O que vem agora?
   (A) Eletrocardiografia (related)
   (B) Patologia Cardíaca (aprofundamento)
   (C) Novo domínio (Pneumologia)?"
  ↓
SessionContext atualiza: "cardiologia: CONCLUÍDO"
```

**Tempo total:** ~4 horas  
**Retenção:** 90%+  
**Confiança:** 9/10

---

## 🏆 O Diferencial Study-Agent vs Outras Plataformas

| Aspecto | Thea Study | Anki | Quizlet | Study-Agent |
|---------|-----------|------|---------|---|
| Geração automática | ✅ | ❌ | ❌ | ✅✅ |
| Repetição espaçada | ✅ | ✅ | ❌ | ✅✅ (FSRS) |
| Personas múltiplas | ❌ | ❌ | ❌ | ✅✅ (6) |
| Concept Mapping | ❌ | ❌ | ❌ | ✅ |
| Knowledge Graph | ❌ | ❌ | ❌ | ✅ |
| Orquestração inteligente | ❌ | ❌ | ❌ | ✅ (Orquestrador) |
| Transparência completa | ⚠️ | ⚠️ | ⚠️ | ✅ (zero config) |
| Preço (aluno) | Grátis* | Grátis | Freemium | Grátis (open) |

---

## 🚀 Próximos Passos

### Para Começar **AGORA**:
```
/começar-novo-estudo
```

### Para Entender Comandos:
```
/ajuda
```

### Para Adicionar Material:
```
/adicionar-material
```

---

**Study-Agent: Estudar com Inteligência, Não com Força.** 🎓
