---
name: study-gerar-provas-simulados
description: "Gera provas sérias (Modo Prova, fiel a um exame real) ou gamificadas (Modo Jogo: quiz cronometrado, streak, flashcard battle). Use quando o usuário quer fazer prova, simulado, ou revisar de forma lúdica."
---

# Gerar Provas e Simulados — Modo Prova + Modo Jogo

**Tipo:** skill real (invocada via `CLAUDE.md` Regra 1)
**Escopo:** Study-Agent — evolução de `estudo-fluxo-05-testar` com formatos gamificados
**Persona padrão:** Quizzer (avaliação rigorosa) — pode alternar para Coach nos modos-jogo (motivação)
**Depende de:** `study-assessment-validator` (qualidade das questões), `study-spaced-repetition-fsrs` (agenda de revisão pós-prova)

---

## Objetivo

Gerar avaliações a partir do material indexado, em dois registros:

1. **Modo Prova** — simulado sério, fiel ao formato do exame real do usuário (concurso, vestibular, certificação)
2. **Modo Jogo** — mesma banca de questões, mecânica lúdica (estilo apps de quiz/flashcard gamificado) para reduzir a fricção de revisar

**Nunca** o modo-jogo troca rigor por diversão — a geração de questão passa pelo `study-assessment-validator` de qualquer forma. O que muda é só a **interface/mecânica de interação**, não a qualidade da questão.

---

## Entrada

- Materiais indexados (via `estudo-fluxo-02-organizar`) ou tópicos explícitos
- Formato de prova (se o usuário tem um exame-alvo: número de questões, tipo, tempo — replicar)
- Modo desejado (perguntar se não estiver claro — ver §Seleção de modo)
- Nível de dificuldade / estágio do aluno (consultar `data/perfil/aprendizado-meta.yaml` se existir)

---

## Modo Prova (simulado sério)

1. Gera questões via `study-assessment-validator` (Bloom, learning outcomes, score ≥92)
2. Replica o formato do exame-alvo se o usuário descreveu um (nº de questões, tempo, peso, tipo de item)
3. Aplica: aluno responde tudo, só vê resultado ao final (simula condição real de prova)
4. Corrige, gera relatório por conceito (não só nota geral — mapeia **onde** errou)
5. Passa erros para `study-spaced-repetition-fsrs` (agenda a revisão dos pontos fracos)

Saída: `data/estudos/exercicios/<tema>/simulado-<data>.md` com gabarito comentado + análise de lacunas.

---

## Modo Jogo — mecânicas disponíveis

Ofereça como opção (não force) — pergunte a preferência quando o usuário pedir "revisar de um jeito mais leve/divertido":

| Mecânica | Como funciona | Quando encaixa |
|---|---|---|
| **Quiz cronometrado** | X segundos por questão, pontos decrescem com o tempo | revisão rápida, "aquecimento" |
| **Modo sobrevivência (streak)** | erra uma, acaba a rodada; cada acerto sobe a dificuldade | consolidar confiança em tópico já estudado |
| **Batalha de flashcard** | par de conceitos, aluno escolhe qual responde primeiro/melhor | revisão de definições/termos |
| **Torneio por bloco** | divide o material em blocos temáticos, cada bloco = 1 "fase"; "boss" final mistura tudo | fechamento de matéria antes de prova grande |
| **Modo dupla (par ou trio)** | dois participantes revezam perguntas (se o estudo for em grupo) | estudo colaborativo |

> Referência de mecânica (não integração literal — study-agent roda via chat/markdown, não é uma
> plataforma web hospedada): projetos como [ClassQuiz](https://github.com/mawoka-myblock/ClassQuiz) e
> [Rahoot](https://github.com/RahootProjects/rahoot) (alternativas open-source ao Kahoot) mostram
> mecânicas de quiz ao vivo com pontuação/tempo — útil como inspiração de design, não como dependência.

### Execução do modo-jogo (via chat, sem plataforma externa)

Todo modo-jogo roda **na conversa**: a IA apresenta uma questão por vez, aplica a mecânica (timer
narrado, contagem de streak, pontuação visível), e ao final resume o placar — sem precisar de app
externo. Se o usuário tem `study-analytics-dashboard`, registra o resultado lá também.

---

## Seleção de modo

Se o usuário só disse "me testa" ou "quero praticar", pergunte com `AskUserQuestion` (ou direto no
texto, se contexto já sugerir): "Simulado sério (como a prova real) ou modo jogo (mais leve, com
pontuação/streak)?" — default para **Modo Prova** se for a primeira vez com o tópico (é o que
`estudo-fluxo-05-testar` já fazia); default para **Modo Jogo** se for revisão de algo já estudado
(baixo risco, foco em retenção).

---

## Integração

- **Geração de questão** → `study-assessment-validator` (sempre, nos dois modos)
- **Agenda de revisão pós-erro** → `study-spaced-repetition-fsrs`
- **Registro de progresso** → `study-analytics-dashboard`
- **Exportar simulado para imprimir/entregar** → `study-exportar-documento` (`.docx`/`.pdf`)

## Saída

```
data/estudos/exercicios/<tema>/
├── simulado-<data>.md        ← Modo Prova: gabarito + análise de lacunas
└── jogo-<mecanica>-<data>.md ← Modo Jogo: placar + questões usadas
```

## Persona

**Quizzer** no Modo Prova (rigor, feedback pedagógico objetivo). **Coach** pode assumir a narração do
Modo Jogo (motivação, celebração de streak) — ver `study-orquestrador` para a troca de persona.
