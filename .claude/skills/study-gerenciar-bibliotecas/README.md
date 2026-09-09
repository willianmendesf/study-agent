# Study-Gerenciar-Bibliotecas

**Utility skill** para criar, editar, listar e organizar bibliotecas de conhecimento no Study-Agent.

## Comandos

```bash
# Criar nova biblioteca (gate interativo)
/study-gerenciar-bibliotecas criar

# Listar bibliotecas
/study-gerenciar-bibliotecas listar                              # todas
/study-gerenciar-bibliotecas listar global                       # só globais
/study-gerenciar-bibliotecas listar skill estudo-fluxo-03-aprender
/study-gerenciar-bibliotecas listar persona Professor
/study-gerenciar-bibliotecas listar materia Anatomia

# Adicionar fonte a biblioteca existente
/study-gerenciar-bibliotecas adicionar-fonte <biblioteca-id>

# Indexar biblioteca (gerar embeddings semânticos)
/study-gerenciar-bibliotecas indexar <biblioteca-id>

# Editar metadados
/study-gerenciar-bibliotecas editar <biblioteca-id>

# Deletar
/study-gerenciar-bibliotecas deletar <biblioteca-id>
```

## Fluxo de Criação (Gate Interativo)

1. **Nome** — que você quer chamar a biblioteca?
2. **Escopo** — global, skill, persona, ou materia?
3. **Referência** — qual skill/persona/materia (se não-global)?
4. **Descrição** — breve resumo
5. **Fontes** — adicionar PDFs, Markdown, URLs, datasets (repetitivo)
6. **Tags** — categorias (esqueleto, osteologia, etc.)
7. **Indexação** — deseja gerar embeddings agora?

Após confirmar, biblioteca fica registrada em `.claude/config.yaml` e pronta para usar.

## Integração com KnowledgeBase

Se você indexar a biblioteca:
- Embeddings são gerados para cada conceito
- Conceitos são extraídos e linkados
- Relações com estágios/personas/materias são mapeadas
- Sugestões de aprofundamento são automáticas

Resultado escreve em: `.claude/rules/knowledge-base/<biblioteca-id>/`

## Integração com SessionContext

Durante uma sessão de aprendizado:
- Study-Agent verifica bibliotecas disponíveis para seu contexto
- Sugere: "Você tem {N} bibliotecas. Quer usá-las?"
- Se sim, referências e exemplos vêm dessas bibliotecas

## Exemplos

### Criar biblioteca global de referências

```
usuário: /study-gerenciar-bibliotecas criar

[gate interativo]

IA: Qual o nome?
usuário: Referências Técnicas — Biologia

IA: Escopo?
usuário: Global

IA: Descrição?
usuário: PDFs e artigos sobre biologia celular e molecular

IA: Adicionar fontes? Sim

IA: Tipo?
usuário: PDF

IA: Path?
usuário: ~/docs/cell-biology-comprehensive.pdf

IA: Indexada?
usuário: Não

IA: Outra fonte? Sim
[repete...]

IA: Tags?
usuário: célula, biologia, referência, técnico

IA: Indexar agora?
usuário: Sim

✅ Biblioteca criada: global-referencias-001
   Indexando... ✓ 1.200 embeddings gerados, 150 conceitos extraídos
```

### Criar biblioteca para persona Professor

```
usuário: /study-gerenciar-bibliotecas criar

[gate interativo]

IA: Qual o nome?
usuário: Exemplos Didáticos — Anatomia

IA: Escopo?
usuário: Persona-específica

IA: Qual persona?
usuário: Professor

IA: Descrição?
usuário: Exemplos práticos para ensinar anatomia humana

[continua...]
```

### Usar bibliotecas em uma sessão

```
usuário: Vou aprender sobre o sistema cardiovascular

IA: ✓ Você está na materia: Fisiologia
   📚 Bibliotecas disponíveis:
      1. "Referências Técnicas — Biologia" (global, 1.200 embeddings)
      2. "Fisiologia Cardiovascular" (materia/Fisiologia, 850 embeddings)
      3. "Exemplos Didáticos" (persona/Professor, 200 exemplos)
   
   Deseja usar estas durante a aula?
usuário: Sim

IA (Professor): O sistema cardiovascular é responsável por... [exemplos da biblioteca]
```

---

## Files

| Arquivo | Contém |
|---|---|
| `SKILL.md` | descrição completa da skill |
| `rules/gate-interativo.md` | protocolo do gate, validação, erros |
| `README.md` | este arquivo |

---

## Relacionados

- `study-indexar-conhecimento` — skill que indexa as bibliotecas (KnowledgeBase)
- `.claude/config.yaml` → seção `libraries` e `library_schema`
- `.claude/rules/knowledge-base/` → embeddings e conceitos gerados
