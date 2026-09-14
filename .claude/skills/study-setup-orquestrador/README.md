# Study-Setup-Orquestrador

**Setup skill** para criar e gerenciar o **Orquestrador Global Profile** — perfil macro que define o domínio, personas, bibliotecas e estilo de aprendizado.

---

## Comandos

```bash
# Setup inicial (chamado automaticamente na primeira sessão)
/study-setup-orquestrador

# Ver perfil atual
/study-setup-orquestrador visualizar

# Validar completude do perfil
/study-setup-orquestrador validar

# Reconfigurar domínio (reseta perfil)
/study-setup-orquestrador reconfigurar

# Editar um campo específico
/study-setup-orquestrador editar personas
/study-setup-orquestrador editar bibliotecas-base
/study-setup-orquestrador editar tone
/study-setup-orquestrador editar profundidade

# Adicionar/remover matéria
/study-setup-orquestrador adicionar-materia "Patologia"
/study-setup-orquestrador remover-materia "Anatomia"

# Adicionar biblioteca base
/study-setup-orquestrador adicionar-biblioteca-base "Robbins Patologia"

# Exportar perfil (para backup/compartilhamento)
/study-setup-orquestrador exportar

# Importar perfil (de um arquivo/backup)
/study-setup-orquestrador importar <arquivo.yaml>
```

---

## Fluxo de Primeira Sessão

```
Study-Agent inicia
    ↓
Detecta ausência de .claude/orquestrador-global-profile.yaml
    ↓
Sugere: "Vamos configurar seu Orquestrador Global? (Sim/Não)"
    ↓
Usuário: Sim
    ↓
/study-setup-orquestrador (inicia 8 stages)

Stage 1: Escolher domínio (Medicina, Programação, etc.)
Stage 2: Objetivo e contexto
Stage 3: Personas (primária, secundária, validação)
Stage 4: Bibliotecas base (Gray's Anatomy, etc.)
Stage 5: Matérias sub-domínio (Anatomia, Fisiologia, etc.)
Stage 6: Tone (técnico, didático, prático, etc.)
Stage 7: Preferências (pace, profundidade, feedback)
Stage 8: Confirmação e salvamento
    ↓
✅ .claude/orquestrador-global-profile.yaml criado
    ↓
"Seu Orquestrador Global está pronto! Domínio: Medicina"
    ↓
Sessão começa contextualizada
```

---

## Exemplo: Setup de Medicina

```
IA: Qual é seu domínio principal de aprendizado?
   [1] Medicina [2] Programação [3] Psicologia [4] Custom
Usuário: 1 (Medicina)

IA: Qual é seu objetivo principal em Medicina?
Usuário: Formar médico clínico com especialização em cardiologia

IA: Em que contexto você está aprendendo?
   [1] Formação acadêmica [2] Especialização [3] Autodidata [4] Profissional
Usuário: 1 (Formação acadêmica)

IA: Qual é sua persona primária?
   [1] Professor [2] Tutor [3] Coach [4] Mentor [5] Quizzer [6] Expert
Usuário: 1 (Professor)

IA: Secundária?
Usuário: 3 (Coach)

IA: Quais são as referências principais de Medicina?
Usuário: 
  Gray's Anatomy
  Guyton Fisiologia
  Robbins Patologia
  Pharmacology Rang & Dale
  Harrison Medicina Interna

IA: Você tem esses arquivos? (PDFs, links)
Usuário: 
  Gray's Anatomy: ~/docs/grays-anatomy.pdf
  Guyton: https://exemplo.com/guyton-physiology.pdf
  Outros: a procurar

[adiciona bibliotecas base, indexa com book-to-skill]

IA: Matérias sub-domínio em Medicina?
Usuário:
  Anatomia
  Fisiologia
  Farmacologia
  Patologia
  Clínica
  Cirurgia

IA: Como você quer que o Orquestrador se comunique?
   [1] Técnico [2] Didático [3] Prático [4] Formal [5] Conversacional [6] Reflexivo
Usuário: 1, 2, 6 (Técnico, Didático, Reflexivo)

IA: Qual seu pace?
   [1] Rápido [2] Médio [3] Lento [4] Adaptativo
Usuário: 2 (Médio)

IA: Profundidade?
   [1] Básico [2] Intermediário [3] Avançado [4] Expert
Usuário: 3 (Avançado)

IA: Feedback imediato? Celebrar progresso?
Usuário: Sim, Sim

[resumo visual]

✅ ORQUESTRADOR GLOBAL PROFILE
Domínio: Medicina
Objetivo: Formação médica com especialização cardio
...
Confirmar? Sim

✅ Perfil salvo! Você está em: Medicina
Próximo passo: /study-orquestrador (rotear para persona)
```

---

## Arquivo Resultante

`.claude/orquestrador-global-profile.yaml`:

```yaml
orquestrador_global_profile:
  version: "1.0"
  created_at: "2026-09-07T14:30:00Z"
  
  dominio: "Medicina"
  objetivo: "Formação médica com especialização cardio"
  contexto: "Formação acadêmica"
  
  personas:
    primária: "Professor"
    secundária: "Coach"
    validação: "Expert"
    tone_geral: ["Técnico", "Didático", "Reflexivo"]
  
  bibliotecas_base:
    - name: "Gray's Anatomy"
      scope: "global"
      status: "adicionada"
      path: "data/biblioteca/global/grays-anatomy-001/"
      indexed: true
      concepts_count: 1200
    
    - name: "Guyton Fisiologia"
      scope: "global"
      status: "adicionada"
      path: "data/biblioteca/global/guyton-fisiologia-001/"
      indexed: true
      concepts_count: 850
  
  materias:
    - name: "Anatomia"
      status: "não-iniciada"
      estágio_atual: "01-descobrir"
      bibliotecas_relacionadas: ["Gray's Anatomy"]
    
    - name: "Fisiologia"
      status: "não-iniciada"
      estágio_atual: "01-descobrir"
      bibliotecas_relacionadas: ["Guyton Fisiologia"]
    
    - name: "Farmacologia"
      status: "não-iniciada"
      bibliotecas_relacionadas: ["Pharmacology Rang & Dale"]
    
    # ... outras matérias
  
  preferences:
    pace: "Médio"
    profundidade_padrão: "Avançado"
    feedback_imediato: true
    celebrar_progresso: true
  
  historico:
    - event: "perfil_criado"
      timestamp: "2026-09-07T14:30:00Z"
      usuario_confirmou: true
```

---

## Integração com Fluxo Completo

```
1. study-setup-orquestrador (AQUI)
   ↓ Cria .claude/orquestrador-global-profile.yaml
   ↓ Registra bibliotecas base

2. study-gerenciar-bibliotecas
   ↓ Usuário adiciona mais bibliotecas (specific/persona/materia)

3. study-orquestrador (próxima skill)
   ↓ Usuário fala/pergunta
   ↓ Orquestrador lê perfil global
   ↓ Seleciona persona + estágio + bibliotecas
   ↓ Responde personalizado

4. SessionContext
   ↓ Rastreia progresso por matéria
   ↓ Atualiza histórico no perfil

5. Próximas sessões
   ↓ Carrega .claude/orquestrador-global-profile.yaml
   ↓ Continua contextualizado
```

---

## Campos Editáveis

| Campo | Tipo | Editável? | Como |
|---|---|---|---|
| `dominio` | string | Sim (reset) | `/study-setup-orquestrador reconfigurar` |
| `objetivo` | string | Sim | `/study-setup-orquestrador editar objetivo` |
| `personas` | array | Sim | `/study-setup-orquestrador editar personas` |
| `bibliotecas_base` | array | Sim | `/study-setup-orquestrador adicionar-biblioteca-base` |
| `materias` | array | Sim | `/study-setup-orquestrador adicionar-materia` |
| `tone` | array | Sim | `/study-setup-orquestrador editar tone` |
| `profundidade_padrão` | enum | Sim | `/study-setup-orquestrador editar profundidade` |
| `pace` | enum | Sim | `/study-setup-orquestrador editar pace` |
| `historico` | array | Não (append-only) | — |

---

## Validação

Ao salvar, verifica:
- ✅ Domínio é válido (ou "Custom")
- ✅ Objetivo tem 10–200 caracteres
- ✅ Personas escolhidas existem em config.yaml
- ✅ Bibliotecas_base ≥ 1 e ≤ 10
- ✅ Matérias ≥ 1 e ≤ 10
- ✅ Tone é um dos valores válidos
- ✅ Profundidade é Básico|Intermediário|Avançado|Expert
- ✅ Pace é Rápido|Médio|Lento|Adaptativo

Se houver erro, sugere correção antes de salvar.

---

## Relacionados

- `.claude/orquestrador-global-profile.yaml` — perfil persistente
- `study-gerenciar-bibliotecas` — gerir bibliotecas (base + sub-domínio)
- `study-orquestrador` — rotear persona dinamicamente
- `SessionContext` — rastrear progresso, histórico
