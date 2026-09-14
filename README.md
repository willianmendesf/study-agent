# 🎓 Study-Agent

Workspace de estudo inteligente para Claude Code (ou qualquer IA compatível com skills markdown).
Conversa natural, sem CLI, sem código — a IA organiza materiais, ensina, pratica e testa seguindo um
fluxo pedagógico de 6 estágios, com uma biblioteca de conhecimento que cresce com você e especialistas
de domínio que você mesmo cria.

**Status:** framework baseado em skills markdown + regras de projeto (`CLAUDE.md`). Sem código
standalone, sem API key própria — roda inteiramente dentro do agente de IA que você já usa.

> 📁 **Seus materiais e seu perfil ficam em `data/`, separados deste repositório.** Você pode (e deve)
> versionar `data/` no seu próprio repositório git privado — ele nunca conflita com atualizações do
> framework. Ver [Seus dados ficam separados do framework](#seus-dados-ficam-separados-do-framework).

---

## O que dá pra fazer

Não é só "responder perguntas de estudo". O study-agent junta, num único lugar:

- **Aprender do zero até dominar** um tópico, em 6 estágios (descobrir → organizar → aprender →
  praticar → testar → domínio), com a IA ajustando o tom/rigor da resposta a cada etapa.
- **Trazer qualquer material seu** — PDF, DOCX, áudio de aula, vídeo, ou uma pasta inteira do Google
  Drive (`book-pipeline`, para ≥15 livros de uma vez) — e ter tudo convertido, catalogado e citável.
  Nada é lido "cru": tudo vira Markdown reindexável primeiro (Regra 2 do `CLAUDE.md`).
- **Criar seus próprios especialistas** — não vem nenhum pré-pronto: você descreve o que precisa
  ("um monitor de Cálculo I", "um revisor de TCC") e o Orquestrador cria o perfil, consultando o
  Bibliotecário pra já conectar às tags que existem na sua biblioteca.
- **Nunca perder o que já processou** — seus materiais, progresso e biblioteca ficam no SEU repositório
  git (`data/`), separado do framework. Trocar de máquina ou atualizar o study-agent nunca reprocessa
  nada.
- **Gerar provas e simulados** — sérios (fiéis a um exame real) ou gamificados (quiz cronometrado,
  streak, flashcard battle), sempre com validação dupla de qualidade das questões.
- **Exportar** o que precisar entregar/imprimir em `.docx`/`.pptx`/`.pdf`.
- **Rodar de graça, sem configurar API própria** — usa a sessão de IA que você já tem. Algumas skills
  opcionais aceitam chave de API própria só se você quiser (ex.: geração de slides com imagem por IA).

Sem setup técnico pra começar. Só conversa:

```
"Quero aprender Cardiologia"
    ↓
Orquestrador detecta intenção, mostra o roteamento e aciona a skill certa:
🎓 Tutor → estudo-fluxo-01-descobrir (intent: descobrir)
    ↓
Mapeia o tópico, pré-requisitos, define metas com você
```

```
"Revise este plano de aula" [+ anexa PDF]
🎓 Professor → estudo-fluxo-03-aprender (intent: aprender)
→ PDF é convertido para Markdown primeiro (nunca lido direto — ver CLAUDE.md)
```

A primeira sessão real pode disparar `study-setup-orquestrador` (define seu domínio e biblioteca base).

---

## Dois conceitos que não são a mesma coisa

Isso confunde gente nova — vale ler com atenção.

| | **Modo de estudo** | **Especialista** |
|---|---|---|
| O que é | O **tom/ênfase** com que a resposta é entregue | Um **expert de domínio** que você cria |
| Exemplos | Professor, Tutor, Coach, Mentor, Quizzer, Expert | "Monitor de Cálculo I"; "Revisor de TCC" |
| Quantos existem | 6, fixos, vêm prontos no framework | Zero por padrão — você cria os que precisar |
| Onde mora | `.claude/config.yaml` (framework) | `data/perfil/especialistas/<nome>.yaml` (seu, no `data/`) |
| Muda o quê | Como a resposta é dita (explica / questiona / motiva / avalia...) | Qual fatia da sua biblioteca é usada e com que ótica de domínio |

**Um modo de estudo não é um especialista, e não existe sozinho** — ele é sempre a ênfase de **quem**
está respondendo: o Orquestrador sem especialista ativo, ou um especialista seu. Exemplo: "seu monitor
de Cálculo I, no modo Professor" — o monitor é o especialista (define o domínio/óptica), Professor é a
ênfase (define como ele explica naquele momento). Não confunda "criar um Professor" com "criar um
especialista" — os 6 modos já existem prontos; quem você cria são os especialistas.

---

## A biblioteca e o Bibliotecário

**Uma origem só de material:** `data/biblioteca/` — pool único, sem catálogo, sem ID. Cada arquivo
declara `tags: [...]`; cada especialista declara `tags_do_dominio: [...]`; o que casa aparece pra ele,
automático, sem você registrar nada.

Quem cuida disso é a skill `study-gerenciar-bibliotecas` — o **Bibliotecário**: converte e tagueia
material novo, responde "temos livro sobre X?", detecta o que falta (lista de aquisição). Ele **nunca
cria especialista** — isso é papel do Orquestrador (`study-setup-orquestrador`), que consulta o
Bibliotecário pra saber que tags já existem antes de conectar o especialista novo. O Bibliotecário
também não responde sobre o *conteúdo* dos livros — só sobre os livros em si; conteúdo é sempre com o
especialista do domínio.

---

## Seus dados ficam separados do framework

Tudo que é seu — materiais, perfil, progresso, biblioteca — vive em `data/`, já no `.gitignore` do
framework. O `git pull` do study-agent nunca toca ali, e você nunca precisa de branch própria pra
guardar seu conteúdo: `data/` vira um repositório git independente, seu. Comandos de setup: `CLAUDE.md`
Regra 7. O framework também se atualiza sozinho em background (a cada ~3 dias, sem avisar) — ver Regra 7.

## O motor: Study-Orquestrador

Toda mensagem passa primeiro pelo roteamento do Orquestrador: detecta intenção → consulta seu progresso
→ resolve especialista + biblioteca do turno → escolhe skill + modo de estudo → executa → sugere o
próximo passo. É uma regra de comportamento em [`CLAUDE.md`](./CLAUDE.md), não um hook técnico —
detalhes em [`ORQUESTRADOR.md`](./ORQUESTRADOR.md).

---

## 6 Estágios de Aprendizado

| Estágio | Objetivo | Modo padrão | Skill |
|---|---|---|---|
| 01 — Descobrir | Mapear tópico, definir metas | Tutor | `estudo-fluxo-01-descobrir` |
| 02 — Organizar | Indexar materiais (PDF/áudio → MD) | Professor | `estudo-fluxo-02-organizar` |
| 03 — Aprender | Ensinar progressivamente | Professor | `estudo-fluxo-03-aprender` |
| 04 — Praticar | Exercícios com feedback imediato | Coach | `estudo-fluxo-04-praticar` |
| 05 — Testar | Provas/simulados, análise de erros | Quizzer | `estudo-fluxo-05-testar` |
| 06 — Domínio | Validar mastery, celebrar progresso | Expert | `estudo-fluxo-06-dominio` |

## 6 Modos de Estudo (ênfase — não confundir com especialista, ver acima)

Professor (explica), Tutor (questiona), Coach (motiva), Mentor (visão holística), Quizzer (avalia com
rigor), Expert (aprofunda e valida). Detalhes em `.claude/rules/modos-de-estudo/README.md` e
`.claude/config.yaml`.

## Skills de suporte

| Skill | Função |
|---|---|
| `study-gerenciar-bibliotecas` | O Bibliotecário — converte, organiza, tagueia a biblioteca (nunca cria especialista) |
| `book-to-skill` | Converte PDF/EPUB/DOCX/etc. em skill estruturada (frameworks, conceitos, glossário) |
| `book-pipeline` | Ingestão em massa de livros de uma pasta do Google Drive (≥15 livros ou drive inteiro) |
| `study-audio-capture` | Transcreve áudio/vídeo (Whisper local) |
| `study-processar-video` | Vídeo → transcrição + resumo + mapa de pontos com timestamps |
| `study-rag-local` | Indexação semântica local, para buscar em livros grandes sem ler o arquivo inteiro |
| `study-spaced-repetition-fsrs` | Repetição espaçada otimizada (FSRS) — integra com o estágio 05 |
| `study-concept-mapping` | Mapeamento conceitual visual (Neo4j + Gephi) |
| `study-knowledge-graph` | Ontologia com inferência de pré-requisitos |
| `study-analytics-dashboard` | Dashboard de progresso, retenção, pontos fracos |
| `study-assessment-validator` | Validação dupla de questões (gerador + validador) |
| `study-orquestrador` | Lógica completa de roteamento intent → skill → modo/especialista |
| `study-setup-orquestrador` | Configura o perfil global (domínio, biblioteca base) |
| `study-token-economy` | Economia de tokens automática via `rtk`, se instalado (opcional, gated) |
| `study-help` / `study-about` | Ajuda e explicação do sistema |
| `study-gerar-provas-simulados` | Provas sérias (Modo Prova) ou gamificadas (Modo Jogo: quiz cronometrado, streak, flashcard battle) |
| `study-h5p` | Exercícios interativos clicáveis (múltipla escolha, arrastar, lacunas, flashcards) rodando localmente no navegador — mecânica opcional do Modo Jogo |
| `study-exportar-documento` | Converte material para `.docx`/`.pptx`/`.pdf` (trabalhos, apresentações, provas para imprimir) |

## Skills complementares — padrão + opcional

Lista completa e critério de uso em `.claude/config.yaml → skills_complementares`.

| Nível | Skill | Uso |
|---|---|---|
| Padrão | `markitdown` | Converte PDF/DOCX/PPTX/XLSX/imagem/áudio → Markdown |
| Padrão | `scientific-brainstorming` | Ideação quando o tópico está vago (usado em `estudo-fluxo-01-descobrir`) |
| Padrão | `docx`, `pptx` | Geram Word/PowerPoint de verdade (usados por `study-exportar-documento`) |
| Padrão | `mermaid-diagrams` | Diagramas em texto puro (flowchart, ER, estado, Gantt) — sem dependência, rápido, renderiza direto na resposta |
| Padrão | `diagram-design` | ~40 tipos de diagrama (arquitetura, organograma, mapa conceitual, Gantt, UML...) como HTML/SVG/PNG rico e autocontido — complementa o `mermaid-diagrams`; a IA escolhe o melhor pro contexto, ou oferece as duas opções |
| Opcional | `pdf-processing-pro` | OCR + tabela/formulário em PDF escaneado |
| Opcional | `file-organizer` | Organiza pasta bagunçada de materiais |
| Opcional | `scientific-critical-thinking`, `literature-review`, `statistical-analysis`, `scientific-writing`, `citation-management`, `plotly` | Pesquisa acadêmica/científica — só relevante se você estuda nessa linha |
| Opcional (API key) | `scientific-slides` | Slides com imagem gerada por IA — requer `OPENROUTER_API_KEY` |
| Opcional (gate ético) | `humanizer` | Deixa texto mais natural — nunca automático; não usar pra disfarçar autoria de trabalho |
| Opcional (catálogo amplo) | **161 skills científicas** | Medicina, bioinformática, genômica, química, física, ML científico, estatística, laboratório etc. (MIT, `github.com/K-Dense-AI/scientific-agent-skills`). O catálogo inteiro fica disponível — o Orquestrador sugere ativar só as que casam com seu domínio/objetivo (nunca instala dependência pesada sem confirmar). Bom pra quem estuda medicina, fisioterapia, biologia, química, e áreas científicas em geral. |
| Bastidor | `skill-creator` | Peça "cria uma skill pra [sua necessidade específica]" e a IA gera uma skill nova sob medida |

---

## 📁 Estrutura do projeto

```
study-agent/                      # ← repositório do FRAMEWORK (git pull recebe updates aqui)
├── CLAUDE.md                     # Regras de projeto (Orquestrador sempre roteia, PDF→MD sempre)
├── ORQUESTRADOR.md               # Guia de referência do roteamento
├── .claude/
│   ├── config.yaml                # Config central: estágios, modos de estudo, especialistas, skills
│   ├── skills/                    # Todas as skills (estudo-fluxo-* + study-* + book-to-skill + book-pipeline)
│   ├── rules/                     # Princípios pedagógicos, estágios, modos (referência)
│   ├── hooks/                     # UserPromptSubmit (inventário da biblioteca, auto-pull) + PreToolUse (rtk)
│   └── templates/                 # Schema do aprendizado-meta.yaml (SessionContext)
└── data/                          # ← SEU repositório pessoal (git init próprio, ver Regra 7)
    ├── perfil/
    │   ├── aprendizado-meta.yaml         # seu progresso
    │   ├── orquestrador-global-profile.yaml # seu perfil (criado via study-setup-orquestrador)
    │   ├── especialistas/                # os especialistas que você criou
    │   └── relacionamentos.yaml           # (opcional) colaboração entre especialistas
    ├── biblioteca/                # pool único de materiais (tags definem visibilidade)
    │   └── lista-aquisicao.md     # (opcional) o que o Bibliotecário identificou faltando
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

**E se um especialista/skill tiver material em outro idioma?** Não importa — a IA sempre responde no
idioma que você definiu no setup (`study-setup-orquestrador`), traduzindo o que for preciso. Isso vale
até pras 161 skills científicas complementares, documentadas em inglês.

**Dados são seguros?** Sim — tudo local em `data/`. Zero upload externo.

**Funciona com qualquer matéria?** Sim — teologia, medicina, direito, programação, o que for. Não vem
nenhum especialista pré-pronto: você descreve o que precisa e o Orquestrador cria.

**Professor/Coach/Tutor são personas que eu escolho como "personagem"?** Não — são **modos de estudo**,
o tom da resposta. Quem você cria e nomeia são os **especialistas** (ver seção acima). Os 6 modos já
vêm prontos e se aplicam a qualquer especialista (ou ao Orquestrador direto, sem especialista).

**Como crio um especialista?** Peça pro Orquestrador: "cria um especialista de [domínio]" (skill
`study-setup-orquestrador`). Ele pergunta nome, domínio, quando ativar, consulta o Bibliotecário pra
saber que tags de biblioteca já existem, e conecta o especialista a elas. O Bibliotecário nunca cria
especialista sozinho — só informa o que tem na biblioteca quando o Orquestrador pergunta.

**Por que PDFs viram Markdown antes de eu perguntar sobre eles?** Para economizar tokens em releituras
e permitir indexação/busca — ver Regra 2 em `CLAUDE.md`.

**Tenho mais de 15 livros pra trazer de uma vez — preciso adicionar um por um?** Não — peça "traz os
livros do Drive [pasta]" e a skill `book-pipeline` processa tudo em fila, com retomada se cair.

---

**Estude com inteligência. 🎓✨**
