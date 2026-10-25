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
1. **Etapa 0 — leitura própria** (só quando o objeto do estudo é **um texto a interpretar** — passagem bíblica,
   fonte primária, texto clássico; ver `CLAUDE.md` Regra 9.5):
   - ler o texto (original + traduções) e responder **sozinho**: estrutura, o que o texto diz, léxico/gramática,
     contexto imediato, tese, aplicação;
   - **não** consultar comentários, teses doutrinais ou interpretações de outros autores sobre o texto;
     ferramentas são permitidas (crítica textual, gramática/morfologia, verbetes de léxico, concordância,
     fatos históricos/geográficos, o próprio corpus do texto para correlação canônica);
   - entregar a **leitura/roteiro** **antes** de abrir a biblioteca.
   - Pergunta **factual pura** ("quando X publicou", "definição de Y") → pula para o passo 2 (Regra 9 vale
     inteira).
2. Busca relevante na KnowledgeBase (Regra 9) — sempre via `study-busca-livros`
   (`buscar.py "<termos>" --tags <tags_do_dominio do especialista ativo>`), nunca "de cabeça".
   - Num estudo exegético isto é o **diálogo com os autores** (Etapa 1): confrontar a leitura própria
     (onde concorda, onde diverge) — **sem reescrever** a Etapa 0 e sem absorver a opinião alheia como
     se fosse a leitura do texto.
3. Seleciona persona apropriada
4. Explica de forma progressiva
5. Cita fontes (materiais + timestamps)
6. Oferece exemplos — se o conceito envolver processo, relação entre partes, hierarquia ou sequência
   de passos, desenhar com `mermaid-diagrams` (`.claude/skills/mermaid-diagrams/`) em vez de só texto
7. Sugere próximo conceito

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
