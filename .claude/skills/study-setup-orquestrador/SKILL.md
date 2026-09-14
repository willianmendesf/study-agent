---
name: study-setup-orquestrador
description: "Configura o perfil global do usuário (domínio de estudo, modo de estudo favorito, bibliotecas base) e cria especialistas novos (nunca é o Bibliotecário quem cria). Use no primeiro uso real do Study-Agent, quando o usuário pede para reconfigurar/ver o perfil, ou pede 'cria um especialista de X'."
---

# Skill: Setup Orquestrador Global

**Tipo:** setup/configuração  
**Escopo:** framework  
**Modo padrão:** Mentor  
**Chamado em:** Primeiro uso do Study-Agent (detecção automática)

---

## Objetivo

Criar e configurar o **Orquestrador Global Profile** — perfil macro que define:
- **Domínio de aprendizado** (Medicina, Programação, Psicologia, etc.)
- **Objetivo e contexto** do usuário
- **Modo de estudo favorito** (e, opcionalmente, especialistas do domínio)
- **Bibliotecas base** (referências principais)
- **Matérias sub-domínio** (disciplinas dentro do domínio)
- **Tone e estilo** de comunicação do Orquestrador

Esse perfil é **persistente** e reutilizado em todas as sessões futuras.

---

## Quando Disparar

### Automático
- Primeira sessão do Study-Agent (detecta ausência de `data/perfil/orquestrador-global-profile.yaml`)
- Sugestão: "Vamos configurar seu Orquestrador Global primeiro?"

### Manual
- `/study-setup-orquestrador reconfigurar` — alterar domínio/perfil existente
- `/study-setup-orquestrador visualizar` — ver perfil atual
- `/study-setup-orquestrador validar` — verificar completude do perfil

---

## Fluxo de Setup

### Stage 0: Idioma de resposta (sempre — vale pra qualquer skill/especialista/material)

**Pergunta** (só se não for óbvio pelo idioma em que o usuário já está escrevendo — nesse caso, confirme
em vez de perguntar do zero):
```
Em que idioma você quer que eu (e qualquer especialista que você criar) sempre responda?
```

Resultado: `IDIOMA` (ex.: `pt-BR`), salvo em
`data/perfil/orquestrador-global-profile.yaml → idioma`. **Vale pra sempre, sem exceção**: mesmo que o
material da biblioteca esteja em inglês (comum em skills complementares técnicas/científicas — muitas
vêm em inglês), ou que um especialista tenha sido descrito em outro idioma, a resposta final ao usuário
é sempre no `IDIOMA` configurado. Traduzir o conteúdo é papel da IA, não do usuário. Ver `CLAUDE.md`
Regra 1, passo de idioma.

---

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

### Stage 3: Modo de Estudo favorito

**Pergunta:**
```
Qual modo de estudo é seu **favorito**?

[1] Professor — explica conceitos com profundidade
[2] Tutor — questiona, guia descoberta socrática
[3] Coach — motiva, celebra, dá feedback
[4] Mentor — perspectiva holística, visão futura
[5] Quizzer — cria questões rigorosas
[6] Expert — valida conhecimento técnico

(Você pode escolher mais de uma — primária + secundária)
```

Resultado: `MODO_FAVORITO_PRIMARIO`, `MODO_FAVORITO_SECUNDARIO` (opcional)

---

### Criar um especialista (papel do Orquestrador, não do Bibliotecário)

Quando o usuário pede "cria um especialista de [domínio]" (aqui ou a qualquer momento, fora do setup
inicial):

1. Perguntar: nome (slug), título, domínio, `tipo` (`conteudo` — padrão, ou `sistema` — ver
   `config.yaml → especialistas.tipos_de_especialista`), como o usuário vai chamá-lo (`quando_ativar`).
2. **Se `tipo: conteudo`:** consultar o pool (`data/biblioteca/`) — pode pedir pro Bibliotecário
   (`study-gerenciar-bibliotecas`) listar as tags existentes relevantes ao domínio — e **propor**
   `tags_do_dominio` com base no que já existe. Se o pool cobre mal o domínio, sinalizar isso ao
   usuário (e, se fizer sentido, sugerir ao Bibliotecário registrar a lacuna na lista de aquisição).
3. **Se `tipo: sistema`:** `tags_do_dominio` fica vazio; não há nada do pool pra conectar.
4. Escrever `data/perfil/especialistas/<nome>.yaml` com o schema de `config.yaml → especialistas.schema`.
5. Se fizer sentido colaboração com outro especialista já existente, sugerir uma entrada em
   `data/perfil/relacionamentos.yaml` (criar o arquivo se ainda não existir).

O Bibliotecário **nunca cria especialista** — ele só cataloga a biblioteca e, quando consultado,
informa quais tags existem. Quem decide, pergunta ao usuário e escreve o arquivo é o Orquestrador.

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
Idioma: pt-BR

Modo de estudo favorito:
  Primário: Professor
  Secundário: Coach

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
1. Gera `data/perfil/orquestrador-global-profile.yaml`
2. Registra as bibliotecas base indicadas no pool (`data/biblioteca/`, com tags do domínio — ver
   `study-gerenciar-bibliotecas`; nunca cria subpasta separada por domínio, é sempre o pool único)
3. Registra matérias em `config.yaml → materias_estendidas`
4. Confirma: "✅ Orquestrador Global pronto! Você está em: **{DOMINIO}**"
5. **Sempre, na sequência, sem o usuário precisar perguntar:** mostrar um resumo curto do que dá pra
   fazer agora, com ênfase no que não é óbvio de descobrir sozinho — **o Bibliotecário** e **criar
   especialistas** (conteúdo completo em `study-about/SKILL.md`, aqui a versão condensada pós-setup):
   ```
   Pronto! Agora que seu perfil de {DOMINIO} está configurado, aqui vai o essencial:

   📚 Bibliotecário — manda qualquer PDF/slide/e-book/áudio que eu converto, tagueio e organizo.
      Depois é só perguntar "temos algo sobre X?" ou "o que falta na biblioteca?".

   🎓 Especialistas — se quiser uma versão da IA focada num assunto específico (ex.: "Professor de
      Anatomia"), é só pedir "cria um especialista de X" a qualquer momento — eu pergunto o essencial
      e já conecto aos materiais certos da biblioteca.

   Sem especialista ativo, eu uso a biblioteca inteira. Quer começar mandando um material, ou já
   quer estudar algum tópico específico?
   ```
   Não pular este passo mesmo se o usuário não perguntar "o que posso fazer" — é a primeira
   oportunidade real de ensinar o Bibliotecário e a criação de especialista, e não vale esperar o
   usuário descobrir sozinho.

---

## Resultado Esperado

Arquivo `data/perfil/orquestrador-global-profile.yaml`:

```yaml
orquestrador_global_profile:
  version: "1.0"
  created_at: "2026-09-07T14:30:00Z"

  idioma: "pt-BR"
  dominio: "Medicina"
  objetivo: "Formar profissional em medicina clínica"
  contexto: "Formação acadêmica"

  modo_de_estudo_favorito:
    primario: "Professor"
    secundario: "Coach"

  # Bibliotecas base ficam no pool único (data/biblioteca/), tagueadas — nunca em subpasta por
  # domínio. "status" aqui é só o que este setup sabe até agora (o Bibliotecário mantém o real).
  bibliotecas_base:
    - name: "Gray's Anatomy"
      status: "adicionada"
      tags: [anatomia, medicina]

    - name: "Guyton Fisiologia"
      status: "adicionada"
      tags: [fisiologia, medicina]

    - name: "Robbins Patologia"
      status: "a-adicionar"
      tags: []

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
   - Domínio, objetivo, modo de estudo favorito
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
/study-setup-orquestrador editar modo-de-estudo
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
Seleciona modo de estudo (do perfil)
    ↓
Busca bibliotecas (do perfil global + materia)
    ↓
Responde com tone/modo de estudo/bibliotecas
```

---

## Arquivos de Saída

- `.claude/orquestrador-global-profile.yaml` — perfil persistente
- `data/biblioteca/global/` — bibliotecas base do domínio
- `config.yaml` — atualizado com matérias estendidas
- `.claude/session-context/orquestrador-history.yaml` — histórico de edições
