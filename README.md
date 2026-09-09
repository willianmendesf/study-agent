# 🎓 Study-Agent

Workspace de estudo inteligente para Claude Code (ou qualquer IA compatível com skills markdown). Conversa natural, sem CLI, sem código — a IA organiza materiais, ensina, pratica e testa seguindo um fluxo pedagógico de 6 estágios.

**Status:** framework baseado em skills markdown + regras de projeto (`CLAUDE.md`). Sem código standalone, sem API key própria — roda inteiramente dentro do agente de IA que você já usa.

> 📁 **Seus materiais e seu perfil ficam em `data/`, separados deste repositório.** Você pode (e deve)
> versionar `data/` no seu próprio repositório git privado — ele nunca conflita com atualizações do
> framework. Ver [Seus dados ficam separados do framework](#seus-dados-ficam-separados-do-framework).

---

## Como usar

Abra o projeto no Claude Code (ou outro agente compatível) e converse:

```
"Quero aprender Cardiologia"
    ↓
Orquestrador detecta intenção, mostra o roteamento e aciona a skill certa:
🎓 Tutor vai te ajudar → estudo-fluxo-01-descobrir (intent: descobrir)
    ↓
Tutor mapeia o tópico, pré-requisitos, define metas com você
```

```
"Explica o ciclo cardíaco"
🎓 Professor vai te ajudar → estudo-fluxo-03-aprender (intent: aprender)
```

```
"Revise este plano de aula" [+ anexa PDF]
🎓 Professor vai te ajudar → estudo-fluxo-03-aprender (intent: aprender)
→ PDF é convertido para Markdown primeiro (nunca lido direto — ver CLAUDE.md)
```

Sem setup técnico. A primeira sessão real pode disparar `study-setup-orquestrador` (define seu domínio, personas favoritas e bibliotecas base).

---

## Seus dados ficam separados do framework

Tudo que é seu — materiais, perfil, progresso, biblioteca — vive em `data/`, já no `.gitignore` do
framework. O `git pull` do study-agent nunca toca ali, e você nunca precisa de branch própria pra
guardar seu conteúdo: `data/` vira um repositório git independente, seu. Comandos de setup: `CLAUDE.md` Regra 7.

## O motor: Study-Orquestrador

Toda mensagem passa primeiro pelo roteamento de Orquestrador: detecta intenção → consulta seu progresso → escolhe skill + persona → executa → sugere o próximo passo. É uma regra de comportamento em [`CLAUDE.md`](./CLAUDE.md), não um hook técnico — detalhes em [`ORQUESTRADOR.md`](./ORQUESTRADOR.md).

---

## 6 Estágios de Aprendizado

| Estágio | Objetivo | Persona padrão | Skill |
|---|---|---|---|
| 01 — Descobrir | Mapear tópico, definir metas | Tutor | `estudo-fluxo-01-descobrir` |
| 02 — Organizar | Indexar materiais (PDF/áudio → MD) | Professor | `estudo-fluxo-02-organizar` |
| 03 — Aprender | Ensinar progressivamente | Professor | `estudo-fluxo-03-aprender` |
| 04 — Praticar | Exercícios com feedback imediato | Coach | `estudo-fluxo-04-praticar` |
| 05 — Testar | Provas/simulados, análise de erros | Quizzer | `estudo-fluxo-05-testar` |
| 06 — Domínio | Validar mastery, celebrar progresso | Expert | `estudo-fluxo-06-dominio` |

## 6 Personas

Professor (explica), Tutor (questiona), Coach (motiva), Mentor (visão holística), Quizzer (avalia com rigor), Expert (aprofunda e valida). Detalhes em `.claude/rules/personas/README.md` e `.claude/config.yaml`.

## Skills de suporte

| Skill | Função |
|---|---|
| `book-to-skill` | Converte PDF/EPUB/DOCX/etc. em skill estruturada (frameworks, conceitos, glossário) |
| `study-gerenciar-bibliotecas` | Cria/organiza bibliotecas de conhecimento (global, por skill, persona ou matéria) |
| `study-audio-capture` | Transcreve áudio/vídeo (Whisper local) |
| `study-rag-local` | Indexação semântica local (ChromaDB) |
| `study-spaced-repetition-fsrs` | Repetição espaçada otimizada (FSRS) — integra com o estágio 05 |
| `study-concept-mapping` | Mapeamento conceitual visual (Neo4j + Gephi) |
| `study-knowledge-graph` | Ontologia com inferência de pré-requisitos |
| `study-analytics-dashboard` | Dashboard de progresso, retenção, pontos fracos |
| `study-assessment-validator` | Validação dupla de questões (gerador + validador) |
| `study-orquestrador` | Lógica completa de roteamento intent → skill → persona |
| `study-setup-orquestrador` | Configura o perfil global (domínio, personas, bibliotecas base) |
| `study-help` / `study-about` | Ajuda e explicação do sistema |
| `study-gerar-provas-simulados` | Provas sérias (Modo Prova) ou gamificadas (Modo Jogo: quiz cronometrado, streak, flashcard battle) |
| `study-exportar-documento` | Converte material para `.docx`/`.pptx`/`.pdf` (trabalhos, apresentações, provas para imprimir) |

## Skills externas (catálogo aitmpl.com) — padrão + opcional

Lista completa e critério de uso em `.claude/config.yaml → external_skills`.

| Nível | Skill | Uso |
|---|---|---|
| Padrão | `markitdown` | Converte PDF/DOCX/PPTX/XLSX/imagem/áudio → Markdown |
| Padrão | `scientific-brainstorming` | Ideação quando o tópico está vago (usado em `estudo-fluxo-01-descobrir`) |
| Padrão | `docx`, `pptx` | Geram Word/PowerPoint de verdade (usados por `study-exportar-documento`) |
| Padrão | `mermaid-diagrams` | Diagramas em texto puro (flowchart, ER, estado, Gantt) — sem dependência, alternativa leve a `study-concept-mapping` |
| Opcional | `pdf-processing-pro` | OCR + tabela/formulário em PDF escaneado |
| Opcional | `file-organizer` | Organiza pasta bagunçada de materiais |
| Opcional | `scientific-critical-thinking`, `literature-review`, `statistical-analysis`, `scientific-writing`, `citation-management`, `plotly` | Pesquisa acadêmica/científica — só relevante se você estuda nessa linha |
| Opcional (API key) | `scientific-slides` | Slides com imagem gerada por IA — requer `OPENROUTER_API_KEY` |
| Opcional (gate ético) | `humanizer` | Deixa texto mais natural — nunca automático; não usar pra disfarçar autoria de trabalho |
| Bastidor | `skill-creator` | Peça "cria uma skill pra [sua necessidade específica]" e a IA gera uma skill nova sob medida |

---

## 📁 Estrutura do projeto

```
study-agent/                      # ← repositório do FRAMEWORK (git pull recebe updates aqui)
├── CLAUDE.md                     # Regras de projeto (Orquestrador sempre roteia, PDF→MD sempre)
├── ORQUESTRADOR.md               # Guia de referência do roteamento
├── .claude/
│   ├── config.yaml                # Config central: estágios, personas, skills
│   ├── skills/                    # Todas as skills (estudo-fluxo-* + study-* + book-to-skill)
│   ├── rules/                     # Princípios pedagógicos, estágios, personas (referência)
│   └── templates/                 # Schema do aprendizado-meta.yaml (SessionContext)
└── data/                          # ← SEU repositório pessoal (git init próprio, ver Regra 7)
    ├── perfil/
    │   ├── aprendizado-meta.yaml         # seu progresso
    │   └── orquestrador-global-profile.yaml # seu perfil (criado via study-setup-orquestrador)
    ├── biblioteca/                # índice de materiais indexados
    └── estudos/                   # seus materiais processados
        ├── aulas/ · livros/ · notas/ · papers/ · exercicios/ · trabalhos/
```

---

## Princípios Pedagógicos

1. **Progressão** — camadas crescentes de complexidade
2. **Repetição Espaçada** — revisar em intervalos ótimos (FSRS)
3. **Aprender Fazendo** — prática ativa com exercícios
4. **Feedback Imediato** — corrigir no ato
5. **Conexão com Realidade** — exemplos do domínio real
6. **Validação de Compreensão** — testar antes de avançar
7. **Autonomia Crescente** — de guiado a auto-dirigido
8. **Celebração de Progresso** — reforçar marcos

Detalhes: `.claude/rules/pedagogical-principles/README.md`.

---

## FAQ

**Preciso de API key própria?** Não — roda dentro do Claude Code (ou agente compatível), usa a sessão que você já tem.

**Dados são seguros?** Sim — tudo local em `data/`. Zero upload externo.

**Funciona com qualquer matéria?** Sim — `.claude/config.yaml → materias` já tem Anatomia, Fisiologia, História, Programação, e aceita `Custom`.

**Por que PDFs viram Markdown antes de eu perguntar sobre eles?** Para economizar tokens em releituras e permitir indexação/busca — ver Regra 2 em `CLAUDE.md`.

---

**Estude com inteligência. 🎓✨**
