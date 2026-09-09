---
name: study-audio-capture
description: "Transcreve áudio/vídeo (Whisper local ou API externa), gera versão verbatim e versão limpa (study-ready). Use quando o usuário anexa ou referencia um arquivo de áudio/vídeo (aula gravada, podcast)."
---

# Transcrever Áudio/Vídeo — Captura, Transcrição e Limpeza

**Tipo:** skill real (invocada pelo fluxo — ver `CLAUDE.md` Regra 1)
**Escopo:** Study-Agent — insumo para `estudo-fluxo-02-organizar` e qualquer estágio que precise do conteúdo de uma aula/áudio
**Trigger:** usuário anexa/referencia um arquivo de áudio ou vídeo (aula gravada, podcast, reunião de estudo)

---

## O que faz

1. **Aceita**: MP3, MP4, WAV, OGG, FLAC, WebM, M4A, etc.
2. **Pergunta onde transcrever** (gate — ver §Gate: local ou externo)
3. **Transcreve**: local (Whisper) ou externo (API), conforme a escolha
4. **Gera 2 versões** (nunca só uma — ver §Duas saídas):
   - **Verbatim** — pontuação/parágrafos, 100% das palavras preservadas (fonte fiel)
   - **Limpa (study-ready)** — remove disfluências, mantém todo conteúdo substantivo
5. **Indexa**: registra em `data/estudos/aulas/<tema>/` e sugere indexação via `study-rag-local`

---

## Gate: local ou externo

**Nem toda máquina aguenta rodar Whisper local** (precisa de CPU razoável, GPU ajuda muito, e o
modelo `large-v3` ocupa ~2.9GB de download na primeira vez). Antes de transcrever, decida:

1. **Teste se local é viável**: `faster-whisper` está instalado? (`python3 -c "import faster_whisper"`)
   Se não, o custo é só instalar (`pip install -r requirements.txt`) — não tem custo monetário nem
   perde privacidade, só leva um tempo na primeira vez.
2. **Se o usuário já indicou preferência** (ex.: "transcreve rápido", "não quero instalar nada", "usa
   a API"), respeite sem perguntar de novo.
3. **Se ambíguo**, pergunte objetivamente:
   > "Posso transcrever de 2 jeitos: **local** (grátis, privado, mas pode ser lento sem GPU e precisa
   > instalar `faster-whisper` na primeira vez) ou **externo** (API OpenAI, mais rápido, identifica
   > quem falou cada parte — mas tem custo por uso e o áudio é enviado pra OpenAI). Qual prefere?"
4. **Local** → segue §Processo normalmente (`scripts/transcrever.sh`, Whisper).
5. **Externo** → usa a skill `transcribe` (`.claude/skills/transcribe/`):
   - Requer `OPENAI_API_KEY` configurada — se ausente, avisar como obter e não tentar rodar sem ela
   - Vantagem real: **diarização nativa** (identifica cada falante) — útil pra aula com pergunta e
     resposta, grupo de estudo, entrevista
   - Roda `scripts/transcribe_diarize.py` da skill `transcribe`, produz a transcrição já com falantes
     rotulados — ainda assim passa pelos passos 2/3 abaixo (verbatim + limpa) antes de virar insumo

---

## Duas saídas — por quê

O pedido original de transcrição de aula tem dois usos diferentes:

| Versão | Uso | O que preserva/remove |
|---|---|---|
| **Verbatim** | fonte fiel, citação exata, revisão de disputa | 100% das palavras — nunca resume, nunca corta |
| **Limpa** | insumo de estudo (ler, gerar prova, RAG) | remove "é", "tipo", "né", repetições e falsas partidas; preserva **todo** conteúdo substantivo — nunca corta uma ideia, um dado, um exemplo |

**Nunca gere só a limpa** — a verbatim é o registro de auditoria caso a limpeza tenha errado algo.

---

## Processo

### 1. Transcrição (script local, determinístico)

```bash
.claude/skills/study-audio-capture/scripts/transcrever.sh <arquivo> [idioma]
```

- Converte para WAV 16kHz mono (`ffmpeg`)
- Roda Whisper local (`faster-whisper`, modelo `large-v3`, GPU auto-detectada via `torch.cuda.is_available()`)
- Salva a transcrição **crua** (verbatim, sem pontuação) em `.tmp-transcricao/`

> **Sem GPU**: roda em CPU (mais lento, mesma qualidade). **Sem `faster-whisper` instalado**: o script informa o comando de instalação (`pip install -r requirements.txt`) — não falha silenciosamente.

### 2. Formatação verbatim (a IA faz, não um serviço externo)

A IA (Claude/outro agente) lê a transcrição crua e adiciona pontuação, capitalização e parágrafos — **sem remover ou resumir nenhuma palavra**. Salva como `data/estudos/aulas/<tema>/<nome>-verbatim.md`.

> Versões anteriores desta skill dependiam de um proxy LiteLLM local (`localhost:7002`) para esse passo — **removido**: a própria IA rodando a skill já é o LLM disponível, não precisa de um serviço externo hardcoded. Isso também é o que torna a skill portável para qualquer clone do repositório.

### 3. Limpeza (a IA faz, passo separado, explícito)

A IA lê a versão verbatim e produz a versão limpa:

- Remove: hesitações ("é...", "tipo", "né", "então assim"), repetições ("eu eu acho"), falsas partidas ("o conceito é- é assim que funciona")
- Preserva: **todo** dado, exemplo, definição, número, nome citado — a limpeza é de forma, não de conteúdo
- Se uma frase for ambígua sem o contexto de fala (ex.: gesto/apontar), marcar `[trecho impreciso na fala original]` em vez de inventar
- Salva como `data/estudos/aulas/<tema>/<nome>-limpa.md`

### 4. Indexação

Sugerir `study-gerenciar-bibliotecas` (registrar como material da matéria) e `study-rag-local` (indexar a versão **limpa** — é a que deve ser buscada/citada nas respostas).

---

## Saída

```
data/estudos/aulas/<tema>/
├── <nome>-verbatim.md   ← fonte fiel (auditoria)
└── <nome>-limpa.md      ← insumo de estudo (usado por RAG, provas, resumos)
```

---

## Qualidade e limitações

- Transcrição local: qualidade comparável a serviços comerciais de Whisper (varia com ruído/sotaque do áudio de origem)
- Whisper local não distingue falantes (sem diarização) — se a aula tem diálogo, a limpeza pode precisar de revisão manual de quem disse o quê
- Áudios muito longos (>1h): processar em blocos (o script já divide a formatação em blocos de ~4500 chars)

## Dependências

```
faster-whisper==1.0.4
numpy>=1.24.0
pydantic>=2.0.0
```
Mais `ffmpeg` no sistema (`apt install ffmpeg` / `brew install ffmpeg`).

## Referências

- `scripts/transcrever.sh` — script de transcrição (etapa 1)
- `estudo-fluxo-02-organizar/SKILL.md` — como o material entra no fluxo de estudo
- `study-rag-local/SKILL.md` — indexação semântica da versão limpa
