---
name: study-spaced-repetition-fsrs
description: "Calcula agenda de revisão espaçada otimizada (algoritmo FSRS) com base no histórico de acertos/erros. Use após testes para agendar a revisão dos pontos fracos."
---

# FSRS — Spaced Repetition Otimizada

**Tipo:** camada automática (não é skill)  
**Escopo:** Study-Agent (integrado em estágio 05-testar)  
**Transparência:** Zero configuração, zero comandos

---

## O que faz (invisível pro usuário)

Quando Quizzer gera questões no estágio 05-testar:
1. **Algoritmo FSRS** calcula próxima revisão ótima
2. **20-30% menos revisões** que SM-2, mesma retenção
3. **Prioriza** conceitos com maior probabilidade de esquecimento
4. **Adapta-se** ao histórico de acerto/erro do aprendiz

**Usuário vê:** Questões mais inteligentes, menos repetições desnecessárias

---

## Fluxo (Automático)

```
Usuário responde questão no estágio 05-testar
    ↓
Quizzer registra:
  - conceito
  - acertou/errou
  - tempo decorrido desde última revisão
    ↓
FSRS calcula:
  - probabilidade de retenção (0-1)
  - dias até próxima revisão ótima
  - dificuldade do conceito (fácil/médio/difícil)
    ↓
Orquestrador agenda próxima revisão
    ↓
Usuário: "Ótimo, próxima semana revisamos este tópico"
```

---

## Estratégia vs SM-2

```
SM-2 (clássico):
  Cada conceito tem intervalo fixo
  Resultado: muitas revisões desnecessárias (70% desperdício)

FSRS (moderno):
  Treina modelo estatístico em SEUS dados de review
  Prevê: "você vai esquecer este conceito em 5.2 dias"
  Resultado: 20-30% menos revisões, mesma retenção
```

---

## Integração com Study-Agent

### Em config.yaml
```yaml
spaced_repetition:
  algorithm: "fsrs"  # antes: "sm-2"
  model_file: "data/rag/fsrs-model.pkl"  # treinado com histórico do usuário
  target_retention: 0.90  # 90% de retenção
  easy_bonus: 1.3        # conceitos fáceis revisam menos
  hard_penalty: 0.6      # conceitos difíceis revisam mais
```

### No estágio 05-testar
```
Quizzer gera questões baseado em:
  1. Próximas revisões (FSRS calcula)
  2. Weak points (conceitos <70% acerto)
  3. Difficulty adaptativo (fácil→médio→difícil)
  4. Variação de tipo (múltipla, ensaio, código)
```

---

## Auto-Instalação (Background)

- LLM instala `fsrs-py` (pip, ~5MB)
- Treina modelo com histórico do aprendiz (paralelo, automático)
- Próximas vezes: instantâneo (modelo cached)

---

## Qualidade

- **Retenção:** 90% (ajustável)
- **Diminuição de reviews:** 20-30% (medido em histórico)
- **Idiomas:** agnóstico (funciona com qualquer conceito)
- **Overhead:** zero (cálculo <1ms por questão)

---

## Referência

- [FSRS - Open Source Project](https://huggingface.co/open-spaced-repetition)
- Paper: "A Large Scale Evaluation of FSRS over 500+ million Anki reviews"
- Adotado por Anki 23.10+
