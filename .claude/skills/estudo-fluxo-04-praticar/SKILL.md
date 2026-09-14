---
name: estudo-fluxo-04-praticar
description: "Etapa 4: cria exercícios e atividades para o aluno praticar e consolidar aprendizado. Use quando o aluno quer praticar ou pede exercício."
---

# estudo-fluxo-04-praticar

**Etapa 4 do Fluxo de Aprendizado: Praticar**

Prática conversacional em loop curto — uma habilidade por turno, uma pergunta por turno,
gabarito só depois da tentativa. Não é prova nem simulado (isso é fluxo 05).

## Entrada
- Materiais indexados (do fluxo 02)
- Conceitos já aprendidos (do fluxo 03)
- Histórico de erros e habilidades praticadas (`data/perfil/aprendizado-meta.yaml`)
- Tipo de prática: conceitual, aplicação, raciocínio clínico, exegese, definição de termos, etc.

## Persona Padrão
**Coach** — motiva, celebra acertos, guia correções com gentileza.
Usa checklists de revisão do Coach em `checklists-revisao.md`.

## Fronteira com outros fluxos
- **Fluxo 05 (`estudo-fluxo-05-testar` / `study-gerar-provas-simulados`)** = prova completa,
  simulado com várias questões de uma vez, cronômetro, correção no final, relatório por conceito.
  Usa player / export `.docx`, não pergunta interativa.
- **Fluxo 03 (`estudo-fluxo-03-aprender`)** = explicar, aprofundar. Se o aluno erra o mesmo
  conceito 2x, volte pro 03 antes de continuar praticando.
- **Exportar lista de exercícios offline** → `study-exportar-documento` (gera `.docx` pra
  resolver no papel).

## Prática conversacional — ciclo obrigatório

Quando a intenção for praticar, siga **sempre** este ciclo, **uma habilidade por turno**:

1. **Consultar contexto**: ler `data/perfil/aprendizado-meta.yaml` (objetivo, nível, erros
   recentes, habilidades praticadas), o material indexado e o especialista ativo (se houver).
2. **Escolher UMA habilidade** para o turno — não misturar duas no mesmo exercício.
3. **Formular a questão** sem revelar resposta, dica decisiva nem palavra-chave do gabarito.
4. **Apresentar a questão** — escolha do mecanismo pela natureza da pergunta:
   - **Objetiva com alternativas diagnósticas** (cada alternativa errada representa uma
     confusão diferente) → usar a ferramenta nativa de pergunta interativa do agente
     runtime (`AskUserQuestion` no Claude Code; `question` no OpenCode). 3–5 alternativas.
     O usuário pode escolher uma opção ou digitar resposta pelo campo "Outro".
   - **Discursiva / aberta / exige explicação longa** → enviar a pergunta no chat normal
     e aguardar resposta textual.
5. **Avaliar a resposta** contra o gabarito **e** a justificativa. Classificar acerto/erro
   **e** o tipo de confusão se errou — não basta "errou", importa *por que* errou.
6. **Dar feedback imediato**: o que acertou, qual conceito faltou, explicação curta,
   referência ao material (citação da fonte, como exige o CLAUDE.md Regra 9).
7. **Registrar a tentativa** em `data/perfil/aprendizado-meta.yaml → historico` (ver formato
   abaixo).
8. **Escolher a próxima questão**: reforço (variação mais simples do mesmo erro), avanço
   (dificuldade maior) ou transversal (pular pra habilidade relacionada fraca).

Pare o ciclo só quando:
- o aluno pedir pra parar,
- a habilidade estiver consolidada (acerto consistente + auto-avaliação "sei"),
- ou após 3–5 itens da mesma habilidade → fazer síntese dos erros e empurrar pra FSRS.

## Formato de registro da tentativa

Cada turno grava um bloco assim no histórico do `aprendizado-meta.yaml` (YAML —
manter formato consistente na sessão):

```yaml
- timestamp: 2026-09-10T14:32:00-03:00
  session: 2026-09-10-fisiologia-ciclo-cardiaco
  materia: Fisiologia
  topico: Ciclo Cardíaco
  habilidade: fisiologia.ciclo-cardiaco.valvulas  # slug estável
  question_id: cc-valvulas-003                    # id interno, se houver banco
  tipo: objetiva | discursiva
  mecanismo: question | chat                       # qual ferramenta foi usada
  resposta_aluno: B                               # letra, texto livre, ou slug
  correta: false
  confusao: "Confundiu contração ventricular com gradiente de pressão valvar"
  evidencia: "data/biblioteca/kb-fisio-cardio.yaml §Gradiente de pressão"
  proxima_acao: reforco | avanco | transversal
```

Após 3–5 turnos da mesma habilidade: gravar **síntese dos erros** e empurrar os
conceitos fracos para `study-spaced-repetition-fsrs` (regra do fluxo 06).

## Critério para usar pergunta interativa vs. chat aberto

Use a pergunta interativa (Claude `AskUserQuestion` / OpenCode `question`) **só quando**
as alternativas erradas forem **diagnósticas** — cada distrator aponta uma confusão
diferente. Se as alternativas erradas são só "quase certas" sem revelar raciocínio,
use chat aberto: a justificativa escrita diz mais sobre a confusão do que a letra
marcada.

## Saída
- Tentativas registradas com diagnóstico de confusão (não só acerto/erro)
- Mapa de habilidades: dominadas / em reforço / não iniciadas
- Itens fracos empurrados para FSRS (próxima revisão agendada)
- Recomendações de revisão pra próxima sessão
