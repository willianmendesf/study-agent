---
name: study-about
description: "Explica o que é o Study-Agent, o que dá pra fazer com ele, e como usar o Bibliotecário e criar especialistas. Use quando o usuário pergunta como o sistema funciona, o que pode fazer, ou pede informação sobre o framework."
---

# Study-Agent: O Que Você Pode Fazer

**Tipo:** informação · **Acionado por:** "o que posso fazer com o study-agent", "como funciona", "/sobre"

---

## O que é

Um framework de estudo guiado por IA: você estuda qualquer matéria em 6 estágios, com 6 "modos de
estudo" diferentes conforme o momento, uma biblioteca única onde tudo que você manda fica organizado
e reaproveitável, e a opção de criar "especialistas" — versões da IA focadas num domínio específico.

**Dois conceitos que não se confundem:**
- **Modo de estudo** — o *tom* da resposta (Professor explica, Tutor questiona, Coach motiva, Mentor
  dá visão de conjunto, Quizzer avalia, Expert aprofunda). Muda sozinho conforme o estágio.
- **Especialista** — um *perfil* que você cria (ex.: "Professor de Banco de Dados"), que só enxerga
  os materiais tagueados daquele domínio. Um especialista pode responder em qualquer modo de estudo.

---

## 1. Estudar em 6 estágios guiados

`Descobrir → Organizar → Aprender → Praticar → Testar → Domínio`. Cada estágio troca o modo de estudo
automaticamente — você só diz o que quer ("quero aprender X", "me testa em Y") e a IA decide o estágio
e o modo.

## 2. O Bibliotecário — cuida dos seus materiais

Você manda um PDF, slide, e-book ou áudio de aula, e o **Bibliotecário** (é assim que a IA se
apresenta ao cuidar da biblioteca) converte pra Markdown estruturado, sugere tags, e organiza em
`data/biblioteca/` — **um pool único**, sem pasta separada por especialista ou matéria. Qualquer
especialista ou o Orquestrador enxerga o material certo automaticamente, pela tag.

Com o Bibliotecário você pode:
- **Adicionar material** — "adiciona esse PDF de Banco de Dados"
- **Perguntar o que já tem** — "temos algo sobre Redes?"
- **Listar a biblioteca** — "o que tá na minha biblioteca?"
- **Ver o que falta** — "o que falta cobrir sobre X?" (mantém uma lista de aquisição)

O Bibliotecário **não responde sobre o conteúdo dos livros** (isso é o especialista do domínio ou o
modo de estudo ativo) e **não cria especialista** — só organiza o material.

## 3. Criar especialistas de domínio

Peça "cria um especialista de [assunto]" a qualquer momento (não precisa ser no setup inicial). Você
escolhe nome, título e domínio; a IA consulta o que já existe na biblioteca sobre aquele tema e propõe
as tags que o especialista vai enxergar. Assim que ele é criado, o Bibliotecário já mostra — sem você
precisar pedir — o que você tem sobre o tema e sugere obras de referência que faltam, com base na
ênfase que você descreveu. Depois é só chamar pelo nome ("fala com o Professor de Banco de Dados sobre
X") pra ativar. Sem especialista ativo, a IA usa a biblioteca inteira.

## 4. Transcrever aulas e vídeos

Áudio de aula → transcrição + resumo + pontos-chave (`study-audio-capture`). Vídeo (arquivo ou link,
ex. YouTube) → o mesmo, com timestamps, e dá pra "conversar com o vídeo" depois (`study-processar-video`).

## 5. Provas e simulados, sérios ou gamificados

Toda questão passa por validação dupla (gera → valida) antes de chegar até você. Modo Prova replica um
exame real; Modo Jogo tem quiz cronometrado, streak, flashcard battle — inclusive numa versão clicável
no navegador, se preferir (`study-h5p`), em vez de só texto no chat.

## 6. Buscar dentro de livros grandes sem reler tudo

Livros indexados (`study-rag-local`) permitem perguntar algo específico e receber a citação exata
(arquivo + trecho), mesmo em obras de milhares de páginas — sem a IA precisar reler o arquivo inteiro
a cada pergunta.

## 7. Mapear pré-requisitos e visualizar conexões entre conceitos

Pra matérias com estrutura clara de dependência ("preciso saber X antes de Y"), a IA pode montar um
grafo real de pré-requisitos (`study-knowledge-graph` — calcula o caminho de estudo e o que falta) e um
mapa visual das conexões entre conceitos (`study-concept-mapping` — gera diagrama Mermaid).

## 8. Acompanhar progresso entre sessões

`data/perfil/aprendizado-meta.yaml` guarda estágio atual, pontos fracos, matérias já vistas — a IA
retoma de onde você parou, sem você precisar reexplicar.

## 9. Repetição espaçada, dashboard, exportar pra .docx/PDF

Revisão agendada pelo algoritmo FSRS quando você erra algo (`study-spaced-repetition-fsrs`), progresso
num dashboard (`study-analytics-dashboard`), e conversão de material pra Word/PDF quando precisa
entregar/imprimir (`study-exportar-documento`).

## 10. Ingestão em massa de livros (Google Drive)

Se você tem uma pasta inteira (≥15 livros) pra trazer de uma vez, `book-pipeline` processa tudo em
fila, com retomada automática se cair.

---

## Skills complementares (sob demanda)

Além do núcleo acima, o Study-Agent vem com dezenas de skills complementares — diagramas ricos
(`diagram-design`), brainstorming quando o tópico está vago (`scientific-brainstorming`), e um catálogo
grande de skills científicas (estatística, revisão de literatura, etc.) que a IA ativa só se fizerem
sentido pro seu perfil. Você não precisa saber os nomes — só descrever o que quer.

---

## Comece agora

- Primeira vez? Diga o que quer estudar ("quero aprender X") — a IA guia pelo estágio 1.
- Tem material? Manda o arquivo — o Bibliotecário organiza.
- Quer um especialista? "Cria um especialista de X."
