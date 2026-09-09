---
name: estudo-fluxo-01-descobrir
description: "Etapa 1 do fluxo de aprendizado: identifica o que o aluno quer estudar, materiais disponíveis e objetivo final. Use ao começar um tópico de estudo novo."
---

# estudo-fluxo-01-descobrir

**Etapa 1 do Fluxo de Aprendizado: Descobrir**

Identifica o que o aluno quer estudar, que materiais tem disponível, e que objetivo final existe.

## Entrada
- Descrição do tópico/matéria
- Materiais disponíveis (opcionais)
- Objetivo final (prova, apresentação, domínio, etc)

## Processo
1. Clarifica o tópico exato — se o tópico estiver vago ou o aluno estiver "travado" sem saber por onde
   começar, usar a skill `scientific-brainstorming` (`.claude/skills/scientific-brainstorming/`) para
   explorar o problema (hipóteses, conexões, SCAMPER) antes de fechar o objetivo
2. Mapeia materiais disponíveis
3. Define objetivo SMART
4. Sugere estrutura de estudo — desenhar como mapa/fluxograma com a skill `mermaid-diagrams`
   (`.claude/skills/mermaid-diagrams/`) ajuda o aluno a visualizar antes de começar
5. Cria SessionContext inicial

## Saída
- `01-descoberta.md` com tópico + objetivo + estrutura
- SessionContext inicializado
- Sugestão de próximo passo (organizar materiais ou começar)

## Persona Padrão
Professor — explica o caminho de forma clara e progressiva
