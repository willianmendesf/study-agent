# Study-Orquestrador — Guia de Referência

Orquestrador é o roteador central do Study-Agent: a cada mensagem, decide qual skill + persona deve responder. **Não é um hook técnico** — é uma regra de comportamento aplicada pela IA a cada turno, definida em [`CLAUDE.md`](./CLAUDE.md) (Regra 1) e detalhada em [`.claude/skills/study-orquestrador/SKILL.md`](./.claude/skills/study-orquestrador/SKILL.md).

> Por que não é hook: `UserPromptSubmit` (o hook de interceptação do Claude Code) roda em um contexto isolado sem acesso à ferramenta `Skill` — não consegue invocar uma skill automaticamente. A abordagem que funciona de fato é uma regra em `CLAUDE.md`, que é sempre carregado no contexto principal da IA.

## Como funciona, na prática

```
Usuário: "revise este plano de aula"
    ↓
IA lê CLAUDE.md → aplica Regra 1 (Orquestrador roteia primeiro)
    ↓
Detecta intent: "aprender" (revisar conteúdo educacional)
    ↓
Consulta data/perfil/aprendizado-meta.yaml (se existir) — estágio atual, personas usadas
    ↓
Mapeia: estudo-fluxo-03-aprender + persona Professor
    ↓
Mostra: "🎓 Professor vai te ajudar → estudo-fluxo-03-aprender (intent: aprender)"
    ↓
Executa a skill com a persona — SEM esperar confirmação
    ↓
Atualiza aprendizado-meta.yaml + sugere próximo passo
```

## Mapeamento intent → skill → persona

| Intenção | Exemplo de mensagem | Skill | Persona |
|----------|---------------------|-------|---------|
| `descobrir` | "quero aprender sobre célula" | `estudo-fluxo-01-descobrir` | Tutor |
| `aprender` | "explique mitose" / "revise este plano" | `estudo-fluxo-03-aprender` | Professor |
| `praticar` | "passa um exercício" | `estudo-fluxo-04-praticar` | Coach |
| `testar` | "me testa sobre isso" | `estudo-fluxo-05-testar` | Quizzer |
| `validar-dominio` | "acho que já sei tudo" | `estudo-fluxo-06-dominio` | Expert |
| `gerenciar` | "adiciona esse PDF" | `study-gerenciar-bibliotecas` | Professor |
| `ajuda` | "?" / "ajuda" | `study-help` | Tutor |
| `entender-sistema` | "como você funciona?" | `study-about` | Mentor |
| ambíguo | mensagem vaga | `estudo-fluxo-03-aprender` (fallback) | Professor |

Tabela completa e exemplos de decisão contextual (pré-requisitos, retenção baixa, troca de persona): ver `.claude/skills/study-orquestrador/SKILL.md`.

## 6 Personas

| Persona | Estilo | Estágios padrão |
|---------|--------|------------------|
| **Professor** | Explica com clareza, exemplos, cita fontes | 01, 02, 03 |
| **Tutor** | Questiona, guia descoberta socrática | 01 |
| **Coach** | Motiva, celebra, feedback imediato | 04, 06 |
| **Mentor** | Perspectiva holística, conecta ao futuro | 01, 06 |
| **Quizzer** | Rigoroso, cria e corrige questões | 05 |
| **Expert** | Valida rigor técnico, aprofunda | 06 |

## 6 Estágios de Aprendizado

```
01-descobrir  → Tutor mapeia o tópico, define metas
02-organizar  → Professor indexa materiais (PDF/áudio → MD, ver Regra 2 do CLAUDE.md)
03-aprender   → Professor ensina progressivamente
04-praticar   → Coach propõe exercícios, feedback imediato
05-testar     → Quizzer avalia com provas/simulados
06-dominio    → Expert valida mastery, Coach celebra
```

## SessionContext (estado persistente)

Arquivo: `data/perfil/aprendizado-meta.yaml` (schema em `.claude/templates/aprendizado-meta.yaml`). Guarda tópico atual, estágio, histórico de personas usadas, pontos fracos, progresso — para que Orquestrador tome decisões contextuais (ex.: "sua retenção caiu, quer revisar antes de avançar?").

## Perfil Global (setup único)

Primeira sessão real, se `.claude/orquestrador-global-profile.yaml` não existir: sugerir `study-setup-orquestrador` para definir domínio (Medicina, Programação...), personas primárias, bibliotecas base e tom de comunicação. Ver `.claude/skills/study-setup-orquestrador/SKILL.md`.

## Limitações conhecidas

1. **Depende da IA seguir CLAUDE.md** — não há enforcement de sistema (nenhum agente de IA hoje suporta hook que auto-invoque skill). Se a IA ignorar a regra, o roteamento não acontece — reforce pedindo explicitamente se notar que não rodou.
2. **Detecção de intenção é heurística (LLM)**, não determinística — mensagens muito vagas caem no fallback (`estudo-fluxo-03-aprender` + Professor).
3. **SessionContext não é lido/escrito automaticamente pelo sistema** — é a IA, seguindo a regra, que lê e grava o YAML a cada turno.

## Referências

- [`CLAUDE.md`](./CLAUDE.md) — regras de projeto (sempre carregado)
- `.claude/skills/study-orquestrador/SKILL.md` — lógica completa de roteamento
- `.claude/config.yaml` — registro de skills, personas, estágios
- `.claude/skills/estudo-fluxo-*/` — as 6 skills de estágio
- `.claude/templates/aprendizado-meta.yaml` — schema do SessionContext
