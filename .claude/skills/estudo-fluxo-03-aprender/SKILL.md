---
name: estudo-fluxo-03-aprender
description: "Etapa 3: ensina o tópico progressivamente com base nos materiais organizados, responde dúvidas, aprofunda conceitos. Use quando o aluno quer aprender ou entender algo."
---

# estudo-fluxo-03-aprender

**Etapa 3 do Fluxo de Aprendizado: Aprender**

Ensina o tópico de forma progressiva baseado nos materiais organizados. Responde perguntas, aprofunda conceitos.

## Entrada
- Materiais já indexados (de 02-organizar)
- Dúvidas ou tópico a aprofundar
- Nível desejado (básico/intermediário/avançado)

## Processo
1. Busca relevante na KnowledgeBase
2. Seleciona persona apropriada
3. Explica de forma progressiva
4. Cita fontes (materiais + timestamps)
5. Oferece exemplos — se o conceito envolver processo, relação entre partes, hierarquia ou sequência
   de passos, desenhar com `mermaid-diagrams` (`.claude/skills/mermaid-diagrams/`) em vez de só texto
6. Sugere próximo conceito

## Saída
- Resposta com citações
- Ligações entre conceitos
- Sugestão de aprofundamento

## Persona Padrão
Professor — ensina de forma clara e com exemplos

Pode ser Tutor (questiona) ou Expert (respostas técnicas) conforme contexto

## Interface: ler no navegador (opcional)

Quando o aprofundamento é melhor consumido como leitura corrida — um capítulo/seção inteiro, não
pergunta-e-resposta — ofereça `study-leitor-web` (Markdown, EPUB ou PDF conforme o material) como
alternativa ao chat. Não é padrão automático: só quando o usuário pede explicitamente ou o material
(um capítulo longo já convertido, um livro em EPUB/PDF do acervo) claramente justifica. Ao voltar do
navegador, verifique `progresso.json → pedidos_pendentes` antes de continuar — pode haver pedido de
explicação/prática feito durante a leitura (ver `study-leitor-web/SKILL.md`, seção "Processo").
