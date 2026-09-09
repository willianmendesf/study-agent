---
name: study-setup-orquestrador
description: "Configura o perfil global do usuário (domínio de estudo, personas favoritas, bibliotecas base). Use no primeiro uso real do Study-Agent, ou quando o usuário pede para reconfigurar/ver o perfil."
---

# Skill: Setup Orquestrador Global

**Tipo:** setup/configuração  
**Escopo:** framework  
**Persona:** Mentor  
**Chamado em:** Primeiro uso do Study-Agent (detecção automática)

---

## Objetivo

Criar e configurar o **Orquestrador Global Profile** — perfil macro que define:
- **Domínio de aprendizado** (Medicina, Programação, Psicologia, etc.)
- **Objetivo e contexto** do usuário
- **Personas especializadas** do domínio
- **Bibliotecas base** (referências principais)
- **Matérias sub-domínio** (disciplinas dentro do domínio)
- **Tone e estilo** de comunicação do Orquestrador

Esse perfil é **persistente** e reutilizado em todas as sessões futuras.

---

## Quando Disparar

### Automático
- Primeira sessão do Study-Agent (detecta ausência de `.claude/orquestrador-global-profile.yaml`)
- Sugestão: "Vamos configurar seu Orquestrador Global primeiro?"

### Manual
- `/study-setup-orquestrador reconfigurar` — alterar domínio/perfil existente
- `/study-setup-orquestrador visualizar` — ver perfil atual
- `/study-setup-orquestrador validar` — verificar completude do perfil

---

## Fluxo de Setup

### Stage 1: Escolher Domínio

**Pergunta:**
```
Qual é seu **domínio principal de aprendizado**?

[1] Medicina — formação médica, especialidades clínicas
[2] Programação — desenvolvimento de software, engenharia
[3] Psicologia — psicologia clínica, organizacional, pesquisa
[4] Administração — gestão, negócios, liderança
[5] Direito — formação jurídica, especialidades legais
[6] Educação — pedagogia, didática, aprendizado
[7] Saúde Pública — epidemiologia, políticas, gestão
[8] Outro — descrever
```

Resultado: `DOMINIO` = escolha do usuário

---

### Stage 2: Objetivo e Contexto

**Perguntas (2 AskUserQuestion):**

```
Pergunta A:
  question: "Qual é seu **objetivo principal** neste domínio?"
  type: text
  examples: ["Formar médico", "Dominar web dev", "Especializarse em terapia"]

Pergunta B:
  question: "Em que **contexto** você está aprendendo?"
  type: choice
  options:
    [1] Formação acadêmica (graduação/pós)
    [2] Especialização profissional
    [3] Autodidata (aprendizado independente)
    [4] Profissional em prática
```

Resultado: `OBJETIVO`, `CONTEXTO`

---

### Stage 3: Personas do Domínio

**Pergunta:**
```
Qual persona é sua **primária** neste domínio?

[1] Professor — explica conceitos com profundidade
[2] Tutor — questiona, guia descoberta socrática
[3] Coach — motiva, celebra, dá feedback
[4] Mentor — perspectiva holística, visão futura
[5] Quizzer — cria questões rigorosas
[6] Expert — valida conhecimento técnico

(Você pode escolher mais de uma — primária + secundária)
```

Resultado: `PERSONAS_PRIMARIA`, `PERSONAS_SECUNDARIA` (opcional)

---

### Stage 4: Bibliotecas Base do Domínio

**Pergunta:**
```
Quais são as **referências principais** do seu domínio?

(Exemplos)
— Medicina: Gray's Anatomy, Guyton Fisiologia, Robbins Patologia
— Programação: Clean Code, Design Patterns, CLRS Algoritmos
— Psicologia: DSM-5, Terapias Cognitivo-Comportamentais, Neurocognição

Descreva até 5 referências fundamentais (uma por linha):
```

Resultado: array de `BIBLIOTECAS_BASE`

**Ação subsequente:** Disparar `study-gerenciar-bibliotecas` para cada referência
- Pergunta: "Você tem arquivo desta biblioteca? (PDF, link, etc.)"
- Se sim: adiciona como biblioteca `global` do domínio
- Se não: registra como "a procurar/adicionar depois"

---

### Stage 5: Matérias Sub-Domínio

**Pergunta:**
```
Quais são as **matérias/disciplinas** principais dentro de **{DOMINIO}**?

(Exemplos)
— Medicina: Anatomia, Fisiologia, Farmacologia, Patologia, Clínica
— Programação: Fundamentos, Web, Mobile, DevOps, Arquitetura
— Psicologia: Psicologia Geral, Psicopatologia, Avaliação, Intervenção

Descreva até 8 matérias (uma por linha):
```

Resultado: array de `MATERIAS`

---

### Stage 6: Tone e Estilo Orquestrador

**Pergunta:**
```
Como você quer que o Orquestrador se comunique neste domínio?

Escolha até 3:
[1] Técnico — preciso, com termos especializados
[2] Didático — acessível, explicações passo-a-passo
[3] Prático — hands-on, com exemplos reais
[4] Formal — rigoroso, acadêmico
[5] Conversacional — casual, amigável
[6] Reflexivo — questionador, ponderado
```

Resultado: array de `TONE`

---

### Stage 7: Preferências e Configuração

**Perguntas:**
```
Pergunta A:
  question: "Qual seu **pace** de aprendizado preferido?"
  options: [Rápido, Médio, Lento, Adaptativo]

Pergunta B:
  question: "Profundidade padrão?"
  options: [Básico, Intermediário, Avançado, Expert]

Pergunta C:
  question: "Feedback imediato?"
  type: choice
  options: [Sim (feedback em tempo real), Não (ao final)]

Pergunta D:
  question: "Celebrar progresso?"
  type: choice
  options: [Sim (marco → celebração), Não]
```

Resultado: `PACE`, `PROFUNDIDADE`, `FEEDBACK_IMEDIATO`, `CELEBRAR`

---

### Stage 8: Confirmação e Salvamento

**Resumo visual:**
```
✅ ORQUESTRADOR GLOBAL PROFILE

Domínio: Medicina
Objetivo: Formar profissional em medicina clínica
Contexto: Formação acadêmica (graduação)

Personas:
  Primária: Professor
  Secundária: Coach
  Validação: Expert

Bibliotecas Base:
  ✓ Gray's Anatomy (adicionada)
  ✓ Guyton Fisiologia (adicionada)
  ○ Robbins Patologia (a adicionar)

Matérias:
  1. Anatomia
  2. Fisiologia
  3. Farmacologia
  4. Patologia
  5. Clínica

Tone: Técnico, Didático, Reflexivo
Pace: Médio
Profundidade: Intermediário → Avançado
Feedback: Imediato
Celebração: Sim

---

Confirmar e salvar? [Sim/Não/Editar]
```

**Se Sim:**
1. Gera `.claude/orquestrador-global-profile.yaml`
2. Cria pastas de bibliotecas base
3. Registra matérias em `config.yaml → materias_estendidas`
4. Confirma: "✅ Orquestrador Global pronto! Você está em: **{DOMINIO}**"

---

## Resultado Esperado

Arquivo `.claude/orquestrador-global-profile.yaml`:

```yaml
orquestrador_global_profile:
  version: "1.0"
  created_at: "2026-09-07T14:30:00Z"
  
  dominio: "Medicina"
  objetivo: "Formar profissional em medicina clínica"
  contexto: "Formação acadêmica"
  
  personas:
    primária: "Professor"
    secundária: "Coach"
    validação: "Expert"
  
  bibliotecas_base:
    - name: "Gray's Anatomy"
      scope: "global"
      status: "adicionada"
      path: "data/biblioteca/global/grays-anatomy-001/"
    
    - name: "Guyton Fisiologia"
      scope: "global"
      status: "adicionada"
      path: "data/biblioteca/global/guyton-fisiologia-001/"
    
    - name: "Robbins Patologia"
      scope: "global"
      status: "a-adicionar"
      path: null
  
  materias:
    - "Anatomia"
    - "Fisiologia"
    - "Farmacologia"
    - "Patologia"
    - "Clínica"
  
  tone: ["Técnico", "Didático", "Reflexivo"]
  
  preferences:
    pace: "Médio"
    profundidade: "Intermediário"
    feedback_imediato: true
    celebrar_progresso: true
  
  historico:
    - event: "perfil_criado"
      timestamp: "2026-09-07T14:30:00Z"
      usuario_confirmou: true
```

---

## Reuso em Sessões

Toda sessão futura carrega esse perfil automaticamente:

```
1. Study-Agent inicia
2. Lê `.claude/orquestrador-global-profile.yaml`
3. Inicializa Orquestrador com:
   - Domínio, objetivo, personas
   - Bibliotecas base disponíveis
   - Tone/estilo/pace
4. Sessão começa contextualizda: "Bem-vindo de volta! Você está em: Medicina. Hoje vamos aprender sobre...?"
```

---

## Comandos Auxiliares

```bash
# Ver perfil atual
/study-setup-orquestrador visualizar

# Validar completude
/study-setup-orquestrador validar

# Reconfigurar domínio (reseta perfil)
/study-setup-orquestrador reconfigurar

# Editar um campo específico
/study-setup-orquestrador editar personas
/study-setup-orquestrador editar bibliotecas-base
/study-setup-orquestrador editar tone

# Adicionar matéria
/study-setup-orquestrador adicionar-materia "Patologia Geral"

# Exportar perfil (para backup/share)
/study-setup-orquestrador exportar
```

---

## Integração com Fluxo

```
Setup Orquestrador
    ↓
Orquestrador carrega perfil
    ↓
Usuário fala/pergunta
    ↓
Orquestrador analisa (com contexto do perfil)
    ↓
Seleciona persona (do perfil)
    ↓
Busca bibliotecas (do perfil global + materia)
    ↓
Responde com tone/persona/bibliotecas
```

---

## Arquivos de Saída

- `.claude/orquestrador-global-profile.yaml` — perfil persistente
- `data/biblioteca/global/` — bibliotecas base do domínio
- `config.yaml` — atualizado com matérias estendidas
- `.claude/session-context/orquestrador-history.yaml` — histórico de edições
