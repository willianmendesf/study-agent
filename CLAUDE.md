# Study-Agent — Instruções para a IA

Workspace de estudo inteligente. Framework ÚNICO de propósito pedagógico — sem plugins, sem multi-projeto, sem ferramentas externas de dev. Vale para qualquer IA que rode aqui (Claude ou outra), não só Claude Code.

## Regra 1 — Orquestrador SEMPRE roteia primeiro

Antes de responder qualquer mensagem do usuário, aplique `.claude/skills/study-orquestrador/SKILL.md`:

1. **Detecte a intenção** da mensagem (descobrir, aprender, praticar, testar, validar domínio, gerenciar biblioteca, ajuda).
2. **Consulte o estado** — se existir, leia `data/perfil/aprendizado-meta.yaml` (SessionContext: estágio atual, personas usadas, pontos fracos, materia/tópico).
3. **Mapeie** intenção → skill (`estudo-fluxo-NN-*` ou `study-*`) → persona (Professor, Tutor, Coach, Mentor, Quizzer, Expert) usando a tabela de `config.yaml → orquestrador` e `.claude/skills/study-orquestrador/SKILL.md`.
4. **Mostre o roteamento ao usuário** antes de responder, formato curto:
   ```
   🎓 Professor vai te ajudar → estudo-fluxo-03-aprender (intent: aprender)
   ```
5. **Execute a skill mapeada** com a persona escolhida — sem esperar confirmação, a menos que a intenção seja ambígua (nesse caso ofereça 2-3 opções via pergunta curta).
6. Ao final, **atualize `data/perfil/aprendizado-meta.yaml`** (crie se não existir, usando `.claude/templates/aprendizado-meta.yaml` como schema) e **sugira o próximo passo**.

Isto substitui qualquer tentativa de hook JSON em `.claude/settings.json` — hooks `UserPromptSubmit` não conseguem invocar skills automaticamente (limitação do Claude Code), então o roteamento é uma regra de contexto, não um hook técnico.

## Regra 2 — PDF/DOCX/EPUB NUNCA são lidos diretamente

Quando o usuário anexa ou referencia um arquivo PDF, DOCX, EPUB, RTF ou similar:

1. **NUNCA** use `Read` diretamente sobre o arquivo original para "revisar", "resumir" ou "responder sobre" o conteúdo.
2. **SEMPRE** primeiro converta para Markdown:
   - Documento maior / livro / material de referência → use a skill `book-to-skill` (`.claude/skills/book-to-skill/SKILL.md`), que extrai estrutura (frameworks, conceitos, glossário) — não só texto corrido.
   - Documento simples/curto/planilha/slide (ex.: plano de aula, nota, `.pptx`, `.xlsx`) → skill `markitdown` (`.claude/skills/markitdown/`) — conversão direta e rápida.
   - PDF **escaneado** (foto de prova, formulário, tabela) → skill `pdf-processing-pro` (`.claude/skills/pdf-processing-pro/`, tem OCR) antes de markitdown/book-to-skill.
3. **Leia o `.md` gerado**, não o arquivo original, para produzir qualquer resposta.
4. **Indexe**: registre o material em `data/biblioteca/` (via `study-gerenciar-bibliotecas` se for material recorrente) para reuso em sessões futuras.

**Por quê:** ler PDF diretamente é caro em tokens a cada vez que o material é referenciado. Markdown é reindexável, buscável, versionável e muito mais barato de reler.

Áudio (MP3, WAV, etc.) segue o mesmo princípio: transcreva primeiro (`study-audio-capture`), que gera
**duas** versões (verbatim + limpa) — trabalhe sobre a versão **limpa** em `.md`, nunca reprocesse o
áudio bruto a cada pergunta.

## Regra 3 — Estado sempre no disco, TUDO dentro de `data/`

Nenhum dado pessoal/mutável vive em `.claude/` (essa pasta é só o FRAMEWORK — skills, config,
templates, versionada no repositório compartilhado). Todo dado do usuário vive em `data/`, raiz do
repositório pessoal dele (Regra 7):

| Dado | Caminho | Antes (não usar mais) |
|---|---|---|
| SessionContext (progresso) | `data/perfil/aprendizado-meta.yaml` | ~~`.claude/aprendizado-meta.yaml`~~ |
| Perfil global do Orquestrador | `data/perfil/orquestrador-global-profile.yaml` | ~~`.claude/orquestrador-global-profile.yaml`~~ |
| Perfis de domínio (ex.: teologia, medicina) | `data/perfil/orquestrador-<dominio>.yaml` | ~~`.claude/orquestrador-<dominio>.yaml`~~ |
| Bibliotecas (índice de materiais) | `data/biblioteca/` | ~~`.claude/libraries/`~~ |
| Analytics/progresso agregado | `data/analytics/` | ~~`.claude/analytics/`~~ |
| RAG local (embeddings) | `data/rag/` | ~~`.claude/rag/`~~ |
| Mapas conceituais / grafos de conhecimento | `data/concept-maps/`, `data/knowledge-graphs/` | ~~`.claude/concept-maps/`, `.claude/knowledge-graphs/`~~ |
| Materiais (PDF→MD, transcrições) | `data/estudos/aulas\|livros\|notas\|papers\|exercicios/trabalhos/` | (sem mudança de nome, só de raiz) |

Skills mais antigas que ainda mencionem os caminhos "antes" (coluna da direita) ou `estudos/` solto na
raiz devem ser lidas como apontando pro caminho novo — **este arquivo é a fonte de verdade**, não o
texto literal do `SKILL.md`. Motivo da mudança: um único `git init` dentro de `data/` (Regra 7) precisa
capturar **tudo** que é do usuário — perfil, progresso, biblioteca e materiais — não só os materiais.

- Crie `data/perfil/aprendizado-meta.yaml` no primeiro uso real, atualize a cada interação relevante.
- Primeira sessão do usuário: se `data/perfil/orquestrador-global-profile.yaml` não existir, sugira rodar `study-setup-orquestrador` (domínio, personas, bibliotecas base) — mas não bloqueie uma pergunta direta só por falta de setup.

## Regra 4 — Nenhuma skill é "camada invisível automática"

Skills como `study-audio-capture` ou `study-assessment-validator` descrevem passos que a IA executa
(ex.: "gera → valida → aceita"), mas **a IA precisa efetivamente executá-los** — não existe um serviço
de fundo rodando sozinho. Se um SKILL.md disser "isso é automático/invisível", leia como "a IA faz isso
como parte do seu próprio raciocínio, sem o usuário precisar pedir passo a passo" — não como "algo roda
sem a IA fazer nada". Ao encontrar essa framing num SKILL.md antigo, trate como um lembrete de UX
(não exponha a mecânica interna ao usuário), não como uma promessa de automação de sistema.

## Regra 5 — Exames e provas: rigor primeiro, jogo depois

Ao gerar qualquer avaliação (prova, simulado, quiz, flashcard), use `study-gerar-provas-simulados`, que
por sua vez sempre passa pela validação dupla de `study-assessment-validator` — inclusive nos modos-jogo
(gamificação muda a interação, nunca a qualidade da questão).

## Regra 6 — Entrega final em .docx/.pdf é uma etapa separada

Todo conteúdo nasce em Markdown (Regra 2). Só quando o usuário precisa **entregar ou imprimir**
(trabalho, prova em papel) use `study-exportar-documento` para converter — nunca gere `.docx` como
formato de trabalho do dia a dia.

## Regra 6.5 — Catálogo de skills externas (`config.yaml → external_skills`)

Além das skills próprias do Study-Agent, há 15 skills externas avaliadas e instaladas (catálogo
aitmpl.com/claude-code-templates), registradas em `.claude/config.yaml → external_skills`, em 3 níveis:

- **`padrao`** — usar sempre que o caso pedir, sem perguntar (`markitdown` para conversão de
  arquivo→MD; `scientific-brainstorming` para ideação no `estudo-fluxo-01-descobrir`;
  `mermaid-diagrams` sempre que um conceito for mais claro como diagrama que como texto)
- **`opcional`** — só usar se o usuário pedir ou o contexto claramente exigir (pesquisa acadêmica,
  estatística, gráfico, organização de pasta, citação bibliográfica, apresentação, OCR de PDF
  escaneado) — não empurrar essas skills pra quem só quer estudar pra uma prova comum
- **`bastidor`** (`skill-creator`) — **não é pra o aluno estudar**, é pra **criar novas skills**. Use
  quando o aluno pedir algo do tipo "cria uma skill só pra revisar [matéria específica] do meu jeito" —
  rode `skill-creator` pra gerar essa skill customizada dentro de `.claude/skills/`.

Skills com `gate` (ex.: `scientific-slides` precisa de `OPENROUTER_API_KEY`; `humanizer` precisa de
confirmação explícita + aviso ético) **nunca** disparam sem passar pelo gate — ver o campo `gate` de
cada uma em `config.yaml`.

## Regra 7 — Dados pessoais em repositório separado (nunca em branch própria)

O study-agent é **um framework compartilhado** — você recebe atualizações dele via `git pull` na
`master`. **Tudo** que é seu (materiais, perfil/Orquestrador, progresso, biblioteca, analytics) vive
dentro de `data/` (Regra 3) e **nunca vai para este repositório** — já está no `.gitignore`. Não crie
uma branch pessoal (ex.: `teologia`) pra guardar isso: branch própria diverge do framework e complica
todo update futuro.

**Setup (uma vez, na raiz do study-agent):**

```bash
mkdir -p data/perfil data/biblioteca data/estudos
cd data
git init -q
git add -A && git commit -q -m "data: início"
# opcional — repo privado seu (GitHub, GitLab, ou só local):
git remote add origin <seu-repo-privado-de-dados>
git push -u origin master
```

Por que funciona sem conflito: `data/` está no `.gitignore` do study-agent, então o git do study-agent
**nem enxerga** que ali dentro existe outro `.git` — são dois repositórios totalmente independentes,
um dentro do outro. `git pull` no study-agent nunca toca em `data/`; `git commit` dentro de `data/`
nunca aparece no `git status` do study-agent.

**Fluxo do dia a dia:**
- Atualizar o framework: `git pull` na raiz do study-agent (sempre na `master`)
- Salvar seu progresso/material/perfil: `git add -A && git commit -m "..."` dentro de `data/`
- **Todo material já processado** (livro extraído/OCR, transcrição, resumo) e **todo perfil/progresso**
  ficam versionados no SEU repo — nunca precisa reprocessar um PDF/áudio de novo, nem reconfigurar o
  Orquestrador do zero, só porque atualizou o framework ou trocou de máquina: é `git clone` do seu repo
  de `data/` e está tudo pronto, sem branch nenhuma.

**Perfis de domínio personalizados** (ex.: teologia, medicina) não precisam de branch nem de fork —
crie o arquivo `data/perfil/orquestrador-<seu-dominio>.yaml` via `study-setup-orquestrador`, e ele já
nasce dentro do seu repo de `data/`.

## Arquitetura (fonte de verdade)

- `.claude/config.yaml` — configuração central: 6 estágios, 6 personas, registro de skills, Orquestrador, libraries.
- `.claude/skills/estudo-fluxo-01-06/` — os 6 estágios do fluxo de aprendizado.
- `.claude/skills/study-*/` — skills de suporte (Orquestrador, RAG local, FSRS, knowledge graph, analytics,
  transcrição de áudio, validação de questões, provas/simulados gamificados, exportação de documento, etc.).
- `.claude/skills/book-to-skill/` — conversor de documentos → skill estruturada (cross-agent, cuidado ao editar: tem seu próprio `AGENTS.md`).
- `ORQUESTRADOR.md` — guia de referência do roteamento (leitura humana, complementa este arquivo).

Não existe mais código Python standalone (`src/`, CLI própria) — foi uma v1 abandonada e removida. Tudo roda via skills markdown interpretadas pela IA dentro do Claude Code (ou outro agente compatível).
