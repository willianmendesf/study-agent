---
name: study-assessment-validator
description: "Valida questões de avaliação em duas passagens (gera mais do que o pedido, depois revisa e filtra) antes de entregar. Use sempre que qualquer skill for gerar questões de prova/quiz/simulado."
---

# Assessment Validator — Validação Dupla de Questões

**Tipo:** skill real (invocada como sub-passo — ver `CLAUDE.md` Regra 1)
**Escopo:** Study-Agent — usada por `estudo-fluxo-05-testar` e `study-gerar-provas-simulados`
**Trigger:** sempre que Quizzer (ou qualquer persona) gera questões de avaliação

---

## O que faz

Ao gerar questões, a IA faz **duas passagens sobre o próprio trabalho** (não dois serviços
externos — é a mesma IA rodando a skill, em dois papéis sequenciais):

1. **Passagem 1 (Gerador)**: gera questões alinhadas ao learning outcome — gera **mais** do que o
   pedido (ex.: pedir 5 → gerar 7), para ter margem de rejeição.
2. **Passagem 2 (Validador)**: relê cada questão como se fosse um revisor cético, aplicando os
   critérios de §Validação Dupla — rejeita as que não atingem o score mínimo.
3. **Categoriza** por tipo cognitivo (Bloom).
4. Se sobrarem menos questões que o pedido, volta à Passagem 1 (até 3 rounds; depois entrega o que
   tem, avisando o usuário quantas ficaram abaixo do pedido).

**Resultado:** questões sem ambiguidade, sem pista óbvia na alternativa, alinhadas ao que deveriam testar.

---

## Fluxo

```
Quizzer: "Vou gerar 5 questões sobre Ciclo Cardíaco"
    ↓
Passagem 1 (Gerador):
  Gera 7 questões (mais do que o pedido)
  Output: [Q1, Q2, Q3, Q4, Q5, Q6, Q7]
    ↓
Passagem 2 (Validador — a mesma IA, papel de revisor):
  Avalia cada questão:
  ✓ Q1 (97% qualidade, mantém)
  ✗ Q2 (62% qualidade, resposta ambígua, rejeita)
  ✓ Q3 (94% qualidade, mantém)
  ✓ Q4 (96% qualidade, mantém)
  ✗ Q5 (71% qualidade, pista no enunciado, rejeita)
  ✓ Q6 (98% qualidade, mantém)
  ✓ Q7 (95% qualidade, mantém)
    ↓
Resultado: 5 questões aceitas [Q1, Q3, Q4, Q6, Q7]
    ↓
Usuário recebe questões garantidamente de qualidade
```

---

## Validação Dupla — Critérios

### LLM-1: Gerador
```yaml
gerar_questao:
  entrada:
    - learning_outcome: "definir ciclo cardíaco"
    - tipo_cognitivo: "conhecimento" (Bloom: 1/6)
    - conceitos: [sístole, diástole, válvulas]
    - dificuldade: 5/10
  
  output:
    questao: "Qual é a ordem correta das fases do ciclo cardíaco?"
    opcoes:
      a: "Sístole → Diástole → Repouso"
      b: "Diástole → Sístole → Repouso"
      c: "Sístole → Repouso → Diástole"
      d: "Diástole → Repouso → Sístole"
    resposta_correta: "b"
    explicacao: "A diástole (preenchimento) precede a sístole (contração)"
    fonte: "Gray's Anatomy, Cap. 5"
```

### LLM-2: Validador
```yaml
validar_questao:
  criterios:
    - clareza (0-100):
        "O enunciado é claro e sem ambiguidade?"
        [critério: 90+]
    
    - acuracia (0-100):
        "A resposta correta é definitivamente correta?
         As outras são definitivamente erradas?"
        [critério: 95+]
    
    - fairness (0-100):
        "Nenhuma pista no enunciado/opções?
         Nenhuma opção mais óbvia que legítima?"
        [critério: 90+]
    
    - nivel_cognitivo (0-100):
        "A questão atende ao nível Bloom esperado?"
        [critério: 85+]
    
    - alinhamento_learning_outcome (0-100):
        "Realmente testa o learning outcome?
         Não testa algo colateral?"
        [critério: 90+]
  
  score_final:
    media = (clareza + acuracia + fairness + nivel + alinhamento) / 5
    aceita = True se media >= 92
```

---

## Tipos Cognitivos (Bloom's Taxonomy)

### Nível 1: Conhecimento (Fácil)
- **Tipo:** Múltipla escolha, Verdadeiro/Falso
- **Verbo:** Definir, listar, nomear, identificar
- **Exemplo:** "O coração tem quantas câmaras?"
- **Tempo:** 30-60s

### Nível 2: Compreensão (Fácil-Médio)
- **Tipo:** Múltipla escolha, resposta curta
- **Verbo:** Explicar, descrever, comparar, classificar
- **Exemplo:** "Explique por que a sístole precisa da contração?"
- **Tempo:** 1-2min

### Nível 3: Aplicação (Médio)
- **Tipo:** Problema, caso clínico, código
- **Verbo:** Aplicar, resolver, construir, demonstrar
- **Exemplo:** "Se a pressão sístole estiver elevada, qual seria o resultado?"
- **Tempo:** 2-5min

### Nível 4: Análise (Médio-Difícil)
- **Tipo:** Estudo de caso, diagrama, argumentação
- **Verbo:** Analisar, diferenciar, relacionar, organizar
- **Exemplo:** "Diferencie infarto anterior de infarto posterior pelos sintomas"
- **Tempo:** 5-10min

### Nível 5: Síntese (Difícil)
- **Tipo:** Ensaio, projeto, pesquisa
- **Verbo:** Combinar, criar, planejar, desenhar
- **Exemplo:** "Desenhe um protocolo de tratamento para insuficiência cardíaca"
- **Tempo:** 15-30min

### Nível 6: Avaliação (Muito Difícil)
- **Tipo:** Debate, crítica, defesa de posição
- **Verbo:** Avaliar, criticar, justificar, julgar
- **Exemplo:** "Critique a efetividade do tratamento X vs Y baseado em evidências"
- **Tempo:** 30-60min

---

## Progressão de Dificuldade (Conforme Progresso)

```
Sessão 1 (Conhecimento Inicial):
  ├─ Nível 1: Conhecimento (2 questões)
  ├─ Nível 2: Compreensão (2 questões)
  └─ Nível 3: Aplicação (1 questão)
  
Sessão 5 (Consolidação):
  ├─ Nível 2: Compreensão (1 questão)
  ├─ Nível 3: Aplicação (2 questões)
  ├─ Nível 4: Análise (1 questão)
  └─ Nível 5: Síntese (1 questão)
  
Sessão 10 (Mastery):
  ├─ Nível 4: Análise (2 questões)
  ├─ Nível 5: Síntese (2 questões)
  └─ Nível 6: Avaliação (1 questão)
```

---

## Integração com Learning Outcomes

### Mapeamento Automático
```yaml
learning_outcomes:
  - titulo: "Definir ciclo cardíaco"
    nivel_bloom: 1  # Conhecimento
    conceitos: [sístole, diástole, válvulas]
    questoes_geradas: 5
    questoes_aceitas: 5
    taxa_acerto: 0.85
  
  - titulo: "Explicar mecanismo de contração cardíaca"
    nivel_bloom: 2  # Compreensão
    conceitos: [sarcômero, troponina, tropomiosina]
    questoes_geradas: 4
    questoes_aceitas: 3
    taxa_acerto: 0.72  # ← baixa, revisar conceitos
  
  - titulo: "Diagnosticar tipo de arritmia de ECG"
    nivel_bloom: 4  # Análise
    conceitos: [ECG, ritmo, onda P, QRS]
    questoes_geradas: 3
    questoes_aceitas: 3
    taxa_acerto: 0.61  # ← muito baixa, adelantar revisão
```

---

## Armazenamento de Questões Validadas

```yaml
# .claude/assessments/<materia>-questoes-validadas.yaml
questoes:
  - id: "cardio-001"
    learning_outcome: "Definir ciclo cardíaco"
    tipo_cognitivo: "conhecimento"
    nivel_bloom: 1
    dificuldade_efetiva: 3  # 1-10
    enunciado: "Qual é a ordem correta das fases...?"
    opcoes: [a, b, c, d]
    resposta_correta: "b"
    explicacao: "A diástole precede a sístole..."
    fonte: "Gray's Anatomy, Cap. 5"
    validacao:
      clareza: 95
      acuracia: 98
      fairness: 92
      alinhamento: 94
      score_final: 94.75
      status: "aceita"
      data_validacao: "2026-02-01T10:30:00Z"
    estatisticas:
      vezes_usada: 12
      taxa_acerto_geral: 0.85
      taxa_acerto_por_persona:
        Professor: 0.88
        Coach: 0.82
        Quizzer: 0.86
```

---

## Retry

- As duas passagens rodam **sequenciais** (a mesma IA não pode se auto-validar em paralelo consigo mesma)
- Se uma questão for rejeitada, a IA gera substituta focada no mesmo learning outcome
- Loop: gera → valida → aceita/rejeita → substitui — até 3 rounds
- Depois de 3 rounds, entrega o que tem e avisa quantas ficaram abaixo do pedido (nunca inventa
  quantidade fictícia)

---

## Qualidade & Confiabilidade

- **Taxa de Aceitação:** 70-80% (1 rejeitada a cada 5 geradas)
- **Score Mínimo:** 92/100 (tolerância zero para ambiguidade)
- **Validação Dupla:** redundância = qualidade garantida
- **Feedback Loop:** questões com baixo acerto revisadas
- **Rastreabilidade:** cada questão com auditoria completa

---

## Referências

- [AI-Generated Exams Quality Assurance](https://arxiv.org/html/2508.08314v1)
- [Quality Validation of AI Questions](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC11854382/)
- [Bloom's Taxonomy - Learning Outcomes](https://en.wikipedia.org/wiki/Bloom%27s_taxonomy)
- [Learning Outcomes Assessment](https://www.disco.co/blog/best-ai-quiz-assessment-generators-2026)
