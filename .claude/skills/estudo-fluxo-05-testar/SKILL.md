---
name: estudo-fluxo-05-testar
description: "Etapa 5: avalia o conhecimento consolidado do aluno — delega a geração real da prova/simulado para `study-gerar-provas-simulados` (Modo Prova ou Modo Jogo, com pergunta padrão texto×H5P). Use quando o aluno quer ser testado ou fazer prova."
---

# estudo-fluxo-05-testar

**Etapa 5 do Fluxo de Aprendizado: Testar**

Gera simulados e provas para avaliar o conhecimento consolidado do aluno.

## Entrada
- Materiais indexados
- Conceitos estudados
- Número de questões
- Tipo de prova (múltipla escolha, aberta, mista)

## Processo
1. Seleciona tópicos do material (via `estudo-fluxo-02-organizar` / biblioteca indexada)
2. **Executa via `study-gerar-provas-simulados`** — é essa skill que de fato gera a prova/simulado
   (Modo Prova sério ou Modo Jogo gamificado) e, por padrão, pergunta a interface (texto no chat ou
   H5P clicável no navegador — ver `study-gerar-provas-simulados/SKILL.md → §Interface`). Este arquivo
   só resolve a **etapa do fluxo** (05-testar); a geração de fato NUNCA roda solta aqui — sempre delega.
3. Questões passam por `study-assessment-validator` (rigor, mesmo no Modo Jogo)
4. Aluno responde (no chat ou no H5P, conforme escolhido)
5. Corrige, classifica por conceito, identifica lacunas
6. Agenda revisão dos pontos fracos via `study-spaced-repetition-fsrs`

## Saída
- Prova completa com respostas
- Score/percentual
- Análise de acertos/erros
- Recomendações de revisão
- Histórico de testes

## Persona Padrão
Quizzer — cria questões, corrige, oferece feedback pedagógico

Usa checklists do Quizzer em `checklists-revisao.md`
