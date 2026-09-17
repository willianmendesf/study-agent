---
name: study-orquestrador
description: "Roteador central do Study-Agent: detecta a intenção da mensagem do usuário e mapeia para a skill + persona certa antes de qualquer resposta. Use no início de toda interação para decidir qual skill/persona deve responder."
---

# Study-Orquestrador — Roteador Central Inteligente

**Escopo:** Study-Agent (roda no início de TODA interação)
**Fonte de verdade:** `CLAUDE.md` Regra 1 (fluxo) + Regra 8 (biblioteca). Onde este arquivo divergir
delas, **valem elas** — este SKILL.md é detalhamento/pseudocódigo, pode ter partes de modelos antigos.

## Resumo do que resolver a cada turno

1. **Intenção** → skill (`estudo-fluxo-NN` ou `study-*`).
2. **Especialista ativo?** O usuário chamou um especialista (nome / apelido / "modo X" / tema declarado
   em `quando_ativar`)? Especialistas vivem em `data/perfil/especialistas/<nome>.yaml`.
3. **Biblioteca** (auto-descoberta por tag — NUNCA whitelist manual):
   - Sem especialista → o pool inteiro `data/biblioteca/` (menos os `disabled`).
   - Especialista X → só os arquivos cujas `tags` cruzam com `tags_do_dominio` de X.
4. **Modo de estudo** (Professor/Tutor/Coach/Mentor/Quizzer/Expert) — só o TOM/método da resposta,
   **nunca** muda a biblioteca. É ortogonal ao especialista.
5. **Lente de domínio**: se `data/perfil/orquestrador-global-profile.yaml → lente_de_dominio.ativa`,
   aplicar esse enquadramento em toda resposta do modo padrão.
6. **Manutenção periódica do bibliotecário** (checagem barata, TODO turno, mesmo sem o usuário chamar
   o bibliotecário): ler o frontmatter `ultima_autorrevisao` de
   `data/perfil/bibliotecario/bibliotecario-autoaperfeicoamento.md`. Se o arquivo não existir OU a data for ≥7 dias
   atrás, rodar o ciclo do bibliotecário (`autoaperfeicoamento_semanal` +
   `revisao_continua_especialistas`, ambos em `data/perfil/especialistas/bibliotecario.yaml`) como um
   passo silencioso DEPOIS de resolver o pedido do usuário — nunca atrasando/desviando a resposta ao
   usuário. Motivo: o bibliotecário só ativa quando chamado por nome/tema (Regra 1.2), mas o
   Orquestrador roda em toda mensagem — é ele quem garante que o ciclo periódico realmente aconteça,
   já que ninguém necessariamente vai "chamar o bibliotecário" na semana certa. Registrar sempre em
   `data/perfil/bibliotecario/bibliotecario-log.md` (ver `log_de_acoes_permanente` no perfil dele).

Mostrar o roteamento antes de responder: `🎓 <Modo> → <skill> (intent: <X> · biblioteca: <escopo>)`.

---

## O que faz (invisível pro usuário)

A cada interação do usuário:
1. **Entende intenção** (LLM analisa o que o aprendiz quer)
2. **Consulta estado** (SessionContext: qual estágio está? Qual persona usou por último?)
3. **Mapeia skill** (qual dos 6 estágios rodar? Qual dos 5 suporte?)
4. **Seleciona persona** (qual das 6 funciona melhor aqui?)
5. **Coordena ferramentas** (RAG? FSRS? Analytics? Knowledge Graph?)
6. **Oferece próximo passo** (sugestão inteligente do que fazer)

**Usuário vê:** Conversação natural, como se houvesse um mentor que entende tudo

---

## Fluxo (Invisível)

```
Usuário digita: "quero aprender Cardiologia"
    ↓ (Orquestrador intercepta)
Detecta intenção: "descobrir novo tópico"
    ↓
Consulta estado:
  • Primeira vez com este tópico? Sim
  • Há pré-requisitos não dominados? Sim (Histologia)
  • Última persona usada? Tutor (mas usuário quer aprender)
    ↓
Mapeia: Estágio 01-descobrir + Persona Tutor
    ↓
Coordena ferramentas:
  • Knowledge Graph: "Cardiologia pré-requisitos?"
  • Concept Mapping: "renderiza mapa?"
  • Analytics: "rastreia início"
    ↓
Oferece próximo passo:
  "Você quer começar com Histologia (pré-req) ou ir direto?"
    ↓
Usuário escolhe → Orquestrador redireciona (outra skill / estágio)
```

---

## Arquitetura: 5 Camadas de Decisão

### Camada 1: Intenção (Intent Detection)
```yaml
intent_patterns:
  descobrir:
    pattern: "quero aprender|novo tópico|comece|começar"
    skill: estudo-fluxo-01-descobrir
    persona: Tutor
  
  aprender:
    pattern: "explica|como funciona|qual é|me ensina"
    skill: estudo-fluxo-03-aprender
    persona: Professor
  
  praticar:
    pattern: "exercício|prática|treinar|fazer"
    skill: estudo-fluxo-04-praticar
    persona: Coach
  
  testar:
    pattern: "prova|teste|quiz|avaliar"
    skill: estudo-fluxo-05-testar  # sempre delega a geração real pra study-gerar-provas-simulados (Modo Prova/Jogo + pergunta texto×H5P)
    persona: Quizzer
  
  validar_dominio:
    pattern: "dominei|aprendi tudo|próximo|avançar"
    skill: estudo-fluxo-06-dominio
    persona: Expert
  
  gerenciar:
    pattern: "adiciona livro|carrega arquivo|biblioteca|arquivo"
    skill: study-gerenciar-bibliotecas
    persona: Professor
```

### Camada 2: Estado (SessionContext)
```yaml
consultar_estado:
  arquivo: "data/perfil/aprendizado-meta.yaml"
  campos:
    - topico_atual
    - estágio_atual
    - personas_usadas_historico
    - weak_points
    - retenção_geral
    - última_sessão
  
  exemplos_decisão:
    if estágio == "03-aprender" AND usuario_quer "testar":
      "Você já praticou (04)? Ou pula direto para teste?"
    
    if retenção < 0.70 AND usuario_quer "avançar":
      "Seus weak points: X, Y, Z. Quer revisar antes?"
    
    if primeira_vez_topico AND usuario_quer "testar":
      "Você não fez a prática ainda. Quer treinar primeiro?"
```

### Camada 3: Inteligência (`study-knowledge-graph` — implementação real, ver seu SKILL.md)

Se existir `data/knowledge-graphs/<materia>.yaml` para a matéria em jogo, consultar antes de
recomendar avançar:
```bash
python3 .claude/skills/study-knowledge-graph/query.py data/knowledge-graphs/<materia>.yaml gaps "<conceito>"
python3 .claude/skills/study-knowledge-graph/query.py data/knowledge-graphs/<materia>.yaml caminho "<conceito>"
python3 .claude/skills/study-knowledge-graph/query.py data/knowledge-graphs/<materia>.yaml dificuldade "<conceito>"
```
```yaml
exemplos:
  if usuario_quer "Cardiologia" AND gaps("Cardiologia") não vazio:
    recomendação: "Cardiologia — pré-requisitos faltando: <lista de gaps>"
    sugestão: "Completar esses antes ou assumir conhecimento?"

  if usuario_quer "Eletrocardiografia" AND gaps("Eletrocardiografia") vazio:
    recomendação: "Direto! Você tem tudo que precisa"
    próximo: "Vamos começar com Eletrocardiografia"
```
Sem o arquivo YAML da matéria, pular esta camada silenciosamente (não é obrigatória — só matérias
com pré-requisitos claros costumam ter ontologia registrada).

### Camada 4: Persona Seleção (Personalization)
```yaml
selecionar_persona:
  regras:
    - if (intenção == descobrir) → Tutor (socrático, questiona)
    - if (intenção == aprender) → Professor (explica com exemplos)
    - if (intenção == praticar) → Coach (motiva, feedback imediato)
    - if (intenção == testar) → Quizzer (riguroso, objetivo)
    - if (intenção == dominar) → Expert (valida, aprofunda)
    - if (intenção == gerenciar) → Professor (organiza, indexa)
  
  adaptação_ao_usuario:
    - if última_persona_efetiva == "Coach" AND retenção_alta:
      "Coach funcionou bem para você. Quer continuar com ele?"
    - if retry_mesmo_tópico == 3:
      "Vamos tentar outra abordagem. Expert pode ajudar com profundidade?"
```

### Camada 5: Orquestração de Ferramentas

Nomes exatos de skill (não abreviações) — todas reais e testadas, exceto onde marcado:
```yaml
coordenar_ferramentas:
  por_estágio:
    01-descobrir:
      - study-knowledge-graph: "gaps/caminho, só se data/knowledge-graphs/<materia>.yaml existir"
      - study-concept-mapping: "mermaid + comunidades, só se o tópico tiver várias relações"
      - study-analytics-dashboard: "registra início"

    03-aprender:
      - study-rag-local: "busca conceitos similares na biblioteca indexada"
      - study-concept-mapping: "reexibe o mapa já gerado, destacando o conceito atual"
      - study-analytics-dashboard: "rastreia engajamento"

    04-praticar:
      - study-analytics-dashboard: "detecta weak points"
      - Coach (modo de estudo, não skill): "oferece exercício"

    05-testar:
      - study-gerar-provas-simulados: "gera a prova/simulado (Modo Prova ou Modo Jogo)"
      - study-assessment-validator: "duplo: gera + valida cada questão"
      - study-h5p: "opcional — versão clicável/visual de uma mecânica do Modo Jogo"
      - study-spaced-repetition-fsrs: "calcula revisão ótima a partir dos erros"
      - study-analytics-dashboard: "registra resultado"

    06-dominio:
      - study-knowledge-graph: "confirma que os pré-requisitos do domínio foram cobertos"
      - study-concept-mapping: "mostra o mapa completo, tudo dominado destacado"
      - study-analytics-dashboard: "compila histórico"
```

---

## Exemplos de Roteamento Inteligente

### Cenário 1: Usuário Novo, Tópico Novo
```
Input: "Quero aprender Cardiologia"

Orquestrador analisa:
  ✓ Intenção: descobrir (novo tópico)
  ✓ Estado: primeiro estágio
  ✓ Pré-requisitos: Histologia falta
  ✓ Persona recomendada: Tutor

Output:
  Tutor: "Bem-vindo! Vejo que é novo em Cardiologia.
          Você já domina Histologia? (essencial)
          Quer: (A) Começar por Histologia? (3 dias)
                (B) Assumir que sabe e pular?
                (C) Revisar rápido de Histologia?
          
          Aqui está o mapa do que vamos estudar..."
```

### Cenário 2: Usuário Retornando, Sessão Anterior
```
Input: "Continuar"

Orquestrador analisa:
  ✓ SessionContext: última sessão em 03-aprender (Coração)
  ✓ Retenção: 78% (abaixo de 85%)
  ✓ Weak points: Ciclo Cardíaco (70%), Válvulas (65%)
  ✓ Persona anterior: Professor (funcionou bem: 82% retenção)

Output:
  Professor: "Bem-vindo de volta! Onde paramos?
              Sua retenção caiu de 85% para 78%.
              Vamos revisar os conceitos que esqueceu:
              • Ciclo Cardíaco (70%)
              • Válvulas (65%)
              
              Opções:
              (A) Revisar com Coach (prática)
              (B) Re-aprender com Professor (teoria)
              (C) Ir direto para Praticar (estágio 04)"
```

### Cenário 3: Usuário Pronto para Teste
```
Input: "Acho que já sei tudo. Quero prova"

Orquestrador analisa:
  ✓ Intenção: testar
  ✓ Estado: 03-aprender 95% completo
  ✓ Weak points: nenhum acima de 70%
  ✓ Caminho: 03 → 04-praticar → 05-testar
  ✓ Recomendação: Pular 04 (prática) se confiança alta

Output:
  Quizzer: "Suas métricas estão ótimas!
            Você saltou a prática, mas sua retenção é 92%.
            Vamos fazer a prova: 5 questões (15 min)
            
            Começamos?"
```

### Cenário 4: Usuário Quer Outra Abordagem
```
Input: "Não estou entendendo. Pode explicar de outro jeito?"

Orquestrador analisa:
  ✓ Intenção: re-aprender (mesmo tópico)
  ✓ Contexto: Professor usado 2x, retenção 65%
  ✓ Decisão: Trocar persona (Expert com profundidade? Mentor com visão maior?)
  ✓ Sugestão: Mentor (perspectiva holística) ou Coach (prática em vez de teoria)

Output:
  Mentor: "Entendo. Deixa eu contar uma história diferente.
           Sabe aquele professor que ensina pelo 'por quê'?
           Vamos começar pelo CONTEXTO histórico e real...
           
           [Abordagem completamente diferente]
           
           Agora faz sentido?"
```

---

## Persistência: SessionContext

```yaml
# Arquivo: data/perfil/aprendizado-meta.yaml
sessao:
  usuario_id: "aprendiz-001"
  topico: "Sistema Cardiovascular"
  
  # Trilha percorrida
  trilha:
    01-descobrir: { completo: "2026-02-01T10:00", persona: "Tutor" }
    02-organizar: { completo: "2026-02-01T10:18", persona: "Professor" }
    03-aprender: { em_progresso: 95%, persona: "Professor" }
    04-praticar: null
    05-testar: null
    06-dominio: null
  
  # Histórico de intencoes
  historico_intencoes:
    - "quero aprender cardiologia" → estágio 01, persona Tutor
    - "explica ciclo cardíaco" → estágio 03, persona Professor
    - "exercício de válvulas" → estágio 04, persona Coach (sugerido)
  
  # Personas efetivas
  persona_effectiveness:
    Professor: { sessoes: 2, retenção_média: 0.82, score: 9.2/10 }
    Coach: { sessoes: 0, sugerido: true }
  
  # Próximo passo recomendado (Orquestrador calcula)
  proximo_passo:
    sugestão: "ir para 04-praticar ou direto para 05-testar"
    razão: "retenção 92%, weak points nenhum"
    personas_opção: [Coach, Quizzer]
```

---

## Fluxo de Chamada (Ordem de Execução)

```python
def orquestrador_process(user_input):
    # 1. Detectar intenção
    intent = detect_intent(user_input)  # "aprender", "testar", etc
    
    # 2. Consultar estado
    session = load_session_context()  # SessionContext
    
    # 3. Inferência Knowledge Graph
    graph_recommendation = query_knowledge_graph(intent, session)
    
    # 4. Selecionar persona
    persona = select_persona(intent, session, graph_recommendation)
    
    # 5. Mapear skill
    skill = map_to_skill(intent, session)
    
    # 6. Orquestrar ferramentas
    tools = orchestrate_tools(skill, persona, session)
    
    # 7. Executar skill com persona + ferramentas
    result = run_skill(skill, persona, user_input, tools)
    
    # 8. Atualizar session (Analytics)
    update_session_context(result)
    
    # 9. Oferecer próximo passo
    next_step = suggest_next(result, persona, session)
    
    return result + "\n→ " + next_step
```

---

## Referências

- `config.yaml` → `orquestrador.enabled = true`
- `SessionContext` → `data/perfil/aprendizado-meta.yaml`
- Knowledge Graph → `data/knowledge-graphs/<materia>-ontology.yaml`
- Integrações → todas as 5 ferramentas + 6 estágios
