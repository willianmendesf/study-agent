---
name: study-processar-video
description: "Processa um vídeo (arquivo local ou URL como YouTube) em 4 saídas de estudo: transcrição limpa, resumo, lista completa de pontos com timestamps, e material pronto para conversar com o conteúdo. Use quando o usuário anexa ou linka um vídeo (vídeo-aula, palestra, webinar) e quer estudar em cima dele."
---

# Processar Vídeo — Transcrever, Resumir, Mapear Pontos, Conversar

**Tipo:** skill real (invocada via `CLAUDE.md` Regra 1)
**Escopo:** Study-Agent — insumo de estudo a partir de vídeo (vídeo-aula, palestra, webinar, curso)
**Modo padrão:** Professor
**Trigger:** usuário anexa um arquivo de vídeo, cola uma URL de vídeo (YouTube, Vimeo…), ou pede "resume esse vídeo", "levanta os pontos desse vídeo", "quero estudar em cima desse vídeo"

---

## O que entrega (4 saídas, sempre nesta ordem)

| # | Saída | Arquivo |
|---|---|---|
| 1 | **Transcrição limpa** (verbatim + limpa, como `study-audio-capture`) | `<video>-transcricao.md` |
| 2 | **Resumo** — a mensagem central + estrutura do vídeo em ~1 página | `<video>-resumo.md` |
| 3 | **Mapa de pontos** — TODOS os pontos abordados, em ordem, com timestamp | `<video>-pontos.md` |
| 4 | **Conversar com o conteúdo** — indexado para perguntas com citação de trecho/timestamp | (indexado via `study-rag-local`) |

Tudo salvo em `data/estudos/aulas/<tema>/`.

---

## Processo

### 1. Obter o vídeo

- **Arquivo local** (`.mp4`, `.mkv`, `.webm`, `.mov`, etc.) → usar direto.
- **URL** (YouTube etc.) → baixar só o necessário:
  - Preferir `yt-dlp` se instalado: `yt-dlp -x --audio-format wav -o "<tmp>/%(id)s.%(ext)s" <URL>` (baixa só o áudio, mais rápido/leve).
  - Alguns vídeos já têm **legenda/transcript oficial** — `yt-dlp --write-auto-sub --skip-download` pega a legenda automática. Se existir e for de boa qualidade, usar como base da transcrição (pula o Whisper). Se não, seguir para o passo 2.
  - `markitdown` também aceita URL de YouTube e extrai o transcript quando disponível — é um caminho alternativo rápido.
  - Se nada disso funcionar (vídeo privado, sem legenda, sem `yt-dlp`), avisar o usuário e pedir o arquivo.

### 2. Transcrever

Reusa o pipeline de `study-audio-capture` (mesmo gate local-vs-externo):
- Extrai o áudio (`ffmpeg -i video.mp4 -ar 16000 -ac 1 audio.wav`).
- Transcreve com Whisper local (`study-audio-capture/scripts/transcrever.sh`) **ou** a skill `transcribe` (API, se o usuário escolheu externo / precisa de diarização) — ver §Gate em `study-audio-capture/SKILL.md`.
- **Preservar timestamps** — o Whisper e a API entregam segmentos com tempo; guardar `[hh:mm:ss]` a cada mudança de tópico/parágrafo. Os timestamps são o que torna as saídas 3 e 4 úteis.

Gera as duas versões (verbatim + limpa) como `study-audio-capture` faz. A **limpa** com timestamps é a base das próximas saídas.

### 3. Resumo (saída 2)

A partir da transcrição limpa, escrever `<video>-resumo.md`:
- **Tese central** em 1-2 frases (qual é a mensagem principal do vídeo).
- **Estrutura** — as 3-7 partes em que o vídeo se divide, uma linha cada.
- **Conclusões / o que fazer com isso** — se o vídeo tiver.
- Máximo ~1 página. Não é a lista de pontos (isso é a saída 3) — é a visão de cima.

### 4. Mapa de pontos (saída 3)

`<video>-pontos.md` — **todos** os pontos abordados, sem filtrar por importância (o usuário decide o que importa):
```markdown
## Mapa de pontos — <título do vídeo>

- **[00:00]** <ponto>
- **[02:14]** <ponto> — <sub-detalhe se relevante>
- **[05:40]** <ponto>
...
```
Regras: um ponto por ideia distinta; timestamp de onde começa; nunca resumir a ponto de perder um dado/nome/número citado. Se o vídeo cita fontes/livros/pessoas, listá-los numa seção "Referências citadas no vídeo".

### 5. Conversar com o conteúdo (saída 4)

- Indexar a transcrição limpa (com timestamps) via `study-rag-local`, no pool de biblioteca (data/biblioteca/), com as tags certas
  .
- A partir daí, perguntas do usuário sobre o vídeo são respondidas citando o trecho + `[timestamp]`.
- Registrar o vídeo como material em `data/biblioteca/` (com `tags:` no topo) — é só salvar
  o `.md`, sem passo de registro (Regra 8).

---

## Entrega ao usuário

Ao terminar, mostrar:
- O resumo (saída 2) direto no chat.
- Onde ficaram os 4 arquivos.
- Oferecer próximo passo: "quer que eu gere um simulado com base nesse vídeo?" (`study-gerar-provas-simulados`),
  "quer um mapa conceitual?" (`mermaid-diagrams` / `study-concept-mapping`), ou "pode perguntar qualquer
  coisa sobre o vídeo que eu respondo com o timestamp".

---

## Dependências

- `ffmpeg` (extrair áudio) — obrigatório
- `yt-dlp` (baixar de URL) — opcional; sem ele, só arquivo local ou `markitdown` para YouTube
- `faster-whisper` (transcrição local) **ou** `OPENAI_API_KEY` para a skill `transcribe` (externo)

## Referências

- `study-audio-capture/SKILL.md` — pipeline de transcrição e o gate local-vs-externo
- `transcribe/SKILL.md` — transcrição via API com diarização
- `study-rag-local/SKILL.md` — indexação para "conversar com o conteúdo"
- `estudo-fluxo-02-organizar/SKILL.md` — como o vídeo processado entra no fluxo de estudo
