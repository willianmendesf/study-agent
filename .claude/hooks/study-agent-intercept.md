# Study-Agent Pre-Interaction — Detalhamento Técnico

> ⚠️ **Este arquivo NÃO é um hook técnico** (não é lido pelo motor de hooks do Claude Code —
> só `.claude/settings.json` é). É material de referência/pseudocódigo para a lógica de
> interceptação. **A regra que a IA de fato segue está em [`../../CLAUDE.md`](../../CLAUDE.md)
> (Regra 1)** — sempre carregado no contexto. Leia este arquivo para entender o *detalhe* da
> lógica descrita ali.

**Propósito:** Interceptar TODA pergunta/comando no Study-Agent e rotear via Orquestrador  
**Gatilho:** Sempre (antes de qualquer resposta) — via regra de `CLAUDE.md`, não hook de sistema  
**Invisível:** Não — mostra claramente qual skill foi acionada

---

## 🎯 Fluxo de Interceptação

```
[Usuário digita pergunta/comando]
    ↓
[Hook intercepta]
    ↓
Orquestrador analisa:
  1. Intenção (intent detection)
  2. Contexto (SessionContext)
  3. Knowledge Graph (pré-requisitos?)
  4. Persona ideal
  5. Skill apropriada
    ↓
[Mostra ao usuário]
  "🎓 Professor vai revisar seu plano com foco em validação de compreensão"
    ↓
[Executa skill + persona]
    ↓
[Resposta estruturada]
```

---

## 📋 Regras de Interceptação

### Detectar Intenção Automaticamente

| Pergunta | Intenção Detectada | Skill Roteada | Persona |
|---|---|---|---|
| "revise este plano" | `revisar-documento` | estudo-fluxo-03-aprender | Professor |
| "quero aprender Cardiologia" | `descobrir-novo-tópico` | estudo-fluxo-01-descobrir | Tutor |
| "exercício de..." | `praticar` | estudo-fluxo-04-praticar | Coach |
| "fiz a prova, como fui?" | `testar-avaliar` | estudo-fluxo-05-testar | Quizzer |
| "dominei, e agora?" | `validar-domínio` | estudo-fluxo-06-dominio | Expert |
| "adicione material" | `organizar` | study-gerenciar-bibliotecas | Professor |
| "?" ou "ajuda" | `menu-ajuda` | study-help | Tutor |
| "como funciona?" | `entender-sistema` | study-about | Mentor |

---

## 🔍 Pseudocódigo

```python
def study_agent_intercept(user_message):
    """
    Hook pré-resposta que intercepta toda mensagem.
    Retorna: (skill_name, persona, explicação)
    """
    
    # 1. Detectar intenção
    intent = detect_intent(user_message)
    #  → "descobrir", "aprender", "praticar", "testar", "dominar", "organizar"
    
    # 2. Consultar SessionContext
    session = load_session("data/perfil/aprendizado-meta.yaml")
    current_stage = session.get("fase_atual")
    
    # 3. Knowledge Graph: validar pré-requisitos?
    if intent == "descobrir":
        kg_check = query_knowledge_graph(user_message)
        #  → pré-requisitos faltando? sugerir caminho?
    
    # 4. Selecionar persona (baseado em intent + efetividade histórica)
    persona = select_persona(intent, session)
    
    # 5. Mapear skill
    skill = map_intent_to_skill(intent)
    
    # 6. Mostrar ao usuário
    header = f"🎓 {persona.emoji} {persona.name} vai te ajudar"
    subtext = f"Detecção: {intent} → {skill}"
    
    return {
        "skill": skill,
        "persona": persona,
        "header": header,
        "subtext": subtext,
        "run_skill": True  # Executar automaticamente
    }
```

---

## 📝 Exemplo Real

### Entrada
```
revise este plano de aula sobre 2 Coríntios
```

### Saída da Interceptação
```
🎓 Professor vai revisar seu plano
   └─ Detecção: revisar-documento → estudo-fluxo-03-aprender
   └─ Persona: Professor (didático, estruturado)
   └─ Foco: Feedback imediato, validação de compreensão
   └─ Referências: 8 princípios pedagógicos do Study-Agent
```

### Depois Executa
```
[Conteúdo da resposta do Professor, estruturado e com citações]
```

---

## 🚀 Ativação

Este hook ativa automaticamente quando:

1. ✅ `config.yaml → always_on_orquestrador: true`
2. ✅ SessionContext carregado (`data/perfil/aprendizado-meta.yaml` existe ou criado no setup)
3. ✅ Qualquer pergunta/comando no Study-Agent

---

## 🔧 Implementação

Hook é invisível para o usuário, mas sempre presente.

**Resultado esperado:**
- Usuário faz pergunta qualquer
- Orquestrador intercepta e roteia
- Skill certa + persona certa são acionadas
- Usuário VÊ qual foi acionado + por quê
- Resposta é estruturada e citada

---

## 📌 Notas

- Não trava o fluxo (análise é rápida)
- Detecta intent com alta confiança (regex + LLM leve)
- Se intent ambígua → mostra opções ("Você quer: (A) aprender (B) praticar?")
- SessionContext persiste entre mensagens (sem reset)
- Knowledge Graph consulta é opcional (fallback para criação on-demand)
