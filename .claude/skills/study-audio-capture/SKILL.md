---
name: study-audio-capture
description: "Transcreve áudio (Whisper local ou API externa), gera a transcrição bruta + 4 saídas de estudo elaboradas pela IA (limpa + resumo + mapa de pontos + perguntas de conversa). Use quando o usuário anexa ou referencia um arquivo de áudio (aula gravada, podcast, reunião)."
---

# Captura de Áudio — Transcrição + 4 saídas de estudo

**Tipo:** skill real (invocada via `CLAUDE.md` Regra 1)
**Escopo:** Study-Agent — insumo para `estudo-fluxo-02-organizar` e qualquer estágio que precise do conteúdo de uma aula/áudio
**Trigger:** usuário anexa/referencia um arquivo de áudio (aula gravada, podcast, reunião de estudo, entrevista, vídeo-aula em MP4 sem legenda)
**Modos de estudo:** Professor (default) / Mentor (revisão com anamnese do progresso)

---

## Convenções de pastas (NÃO variante por usuário — vale pra todos)

Esta convenção é **do framework**, não do usuário individual. Todo mundo que usa Study-Agent segue:

```
data/audios/aulas/<materia>/<unidade>/parteN.txt          ← transcrição bruta (gerada pelo pipeline)
data/audios/.work/<job-id>/...                             ← staging temporário (auto-apagado ao final)
data/estudos/aulas/<materia>/<unidade>/parteN/            ← elaborados pela IA (4 saídas em .md)
└── parteN-transcricao.md                                    (limpa, com pontuação/parágrafos)
└── parteN-resumo.md                                         (tese central + estrutura + chaves)
└── parteN-pontos.md                                         (mapa completo por seção)
└── parteN-conversa.md                                       (5 perguntas para discutir)
```

### Por que `<materia>/<unidade>/parteN` e não `<materia>/<data>/parteN`

A navegação é por **texto**, não por data. Se a materia é "Romanos" e você segue a convenção por data, vai ter `data/estudos/aulas/romanos/10-09-2026/...`, `data/estudos/aulas/romanos/17-09-2026/...`, ... crescendo sem fim. Com a navegação textual, `aulas/romanos/4/...` e `aulas/romanos/5/...` espelham `notas/evangelho-joao/3/`, `notas/evangelho-joao/4/` — que é a convenção que já existe em `data/estudos/notas/` (ver `data/estudos/README.md`). **Mesma lógica, mesma estrutura.**

### Padrões de nomenclatura

- **`<materia>`** — slug do conteúdo (em **português**, sem acento, separado por hífen). Casa com a unidade de navegação superior.
  - `notas/evangelho-joao/3/...` → audio em `aulas/evangelho-joao/3/...`
  - `notas/romanos/12/...` → audio em `aulas/romanos/12/...`
  - Conteúdo avulso sem livro-base: usa o tema (ex.: `cardiologia`, `redes-neurais`, `historia-igreja`)
  - **NUNCA** usar nomes ad-hoc que misturam eixos (ex.: `romanos-sala-4`, `joao-4-e-5`) — ver `CLAUDE.md`, convenção de subpasta em `data/estudos/`
- **`<unidade>`** — a subdivisão natural da materia. Não é a data da captura — é o **identificador textual** do que este material cobre:
  - Capítulo: `3`, `4`, `5`
  - Aula em série: `aula-1`, `aula-2`
  - Módulo: `modulo-3`, `modulo-4`
  - Sessão datada (quando a série é por tempo): `10-09-2026` ← sim, DD-MM-YYYY, **mas só quando fizer sentido** (cursos de 1 ano, seminários mensais)
  - Tema específico: `introducao`, `revisoes`, `caso-clinico-x`
- **`parteN`** — `parte1`, `parte2`, … para áudio dividido em partes (mesma aula/unidade gravada em 2 arquivos)
- **`<job-id>`** — `<slug-da-entrada>-<HHMMSS>` (timestamp do início do job)

### Regra do "bruto" × "elaborado"

- **Bruto (`data/audios/aulas/...`)** é a transcrição crua gerada pelo pipeline (1 arquivo `.txt` por parte). É a fonte única de verdade reproduzível (re-rodar o pipeline gera byte-a-byte o mesmo arquivo se a API for determinística).
- **Elaborado (`data/estudos/aulas/...`)** é o que a IA gera em cima do bruto (4 `.md` por parte). Não é reproduzível — depende da leitura da IA. É o insumo de estudo que vai pro RAG, vira prova, gera conversa.
- **A IA NUNCA escreve em cima do `.txt` bruto.** Bruto é sacrossanto. Edições/limpezas vão pro elaborado.

### Como o skill escolhe `<materia>` e `<unidade>` automaticamente

No gate de contexto (§Gate de contexto), a IA já coleta:

1. `data/perfil/aprendizado-meta.yaml` → `materia` (slug em uso agora). **Use como `<materia>` se existir.**
2. `<materia>` em `data/estudos/notas/` ou similar → se já existe a materia no estudo do aluno, **use a mesma string** (consistência entre notas e aulas)
3. Nome do arquivo → se contém pista clara (ex.: "Cardio 10.09 parte 2"), extrai materia e unidade
4. Mensagem atual do usuário → se o usuário falou "esse áudio é de Romanos 5", use `romanos` / `5`

Se ainda assim ficar ambíguo → gate explícito ao usuário:

> "Vou organizar como `<materia>/<unidade>/parteN>`. Me confirme: a **matéria** é `<X>` e a **unidade** é `<Y>`? (ex.: `romanos` / `5`, ou `cardiologia` / `aula-1`)"

---

## O que entrega (4 saídas elaboradas)

| # | Saída | Arquivo |
|---|---|---|
| 1 | **Transcrição limpa** (verbatim com pontuação, sem disfluências) | `data/estudos/aulas/<materia>/<unidade>/parteN/parteN-transcricao.md` |
| 2 | **Resumo** — tese central + estrutura da aula em ~1 página | `.../parteN-resumo.md` |
| 3 | **Mapa de pontos** — lista organizada por tema, sem perder nenhum detalhe | `.../parteN-pontos.md` |
| 4 | **Perguntas de conversa** — 5 perguntas para o aluno discutir/falar | `.../parteN-conversa.md` |

Bruto (sempre em `data/audios/aulas/<materia>/<unidade>/`):
- `parteN.txt` ← sempre (transcrição crua)
- `parteN.segments.json` ← só no modo timestamps (timeline bruta)
- `parteN-timestamps.md` ← só no modo timestamps (formatação mecânica `[mm:ss]` por bloco, não é a elaboração da IA)

---

## Gate de contexto — antes de transcrever

A transcrição fica muito melhor quando o contexto do aluno é informado ao modelo. Antes de chamar a API, faça este gate automaticamente:

### 1. Colete do estado atual do Study-Agent (sem perguntar)

1. **`data/perfil/aprendizado-meta.yaml`** — `materia` e `topico` (o que o aluno está estudando AGORA)
2. **Especialista ativo na conversa** — se houver nome (`Hermes`, `Kritikos`, etc.), leia `data/perfil/especialistas/<nome>.yaml` e veja o domínio dele. Especialistas não mudam a transcrição — só dão vocabulário
3. **`data/perfil/orquestrador-global-profile.yaml`** — idioma inferido do profile (tone, contexto_detalhes, lente de domínio)
4. **Tema da mensagem atual** — usuário falou do tema? Está no nome do arquivo? "Cardio 10.09 parte 2.mp3" → cardio / insuficiência cardíaca
5. **`materia` inferida** = `#1` se existir, **senão** `#4`. Use no path: `data/audios/aulas/<materia>/...`

### 2. Componha o prompt de contexto (curto, SÓ estilo/idioma)

```
"Transcrição de <tipo de conteúdo> de <tema detectado> em <idioma inferido>.
 Falar palavras técnicas em <idioma> completo, sem abreviações."
```

Exemplos:
- "Transcrição de aula universitária de medicina — cardiologia em português brasileiro. Falar palavras técnicas em português completo, sem abreviações."
- "Transcrição de podcast de teologia reformada em português brasileiro. Falar palavras técnicas em português completo, sem abreviações."

**Por que NÃO listar termos:** modelos de ASR, quando recebem listas de vocabulário no prompt, passam a **alucinar** termos inexistentes na fala. Só instruções de estilo e idioma funcionam; "dicionários" não.

### 3. Se o tema é opaco → gate explícito ao usuário

Se nem o aprendizado-meta, nem o especialista, nem o nome do arquivo dão dica da matéria:

> "Vou transcrever este áudio. Para a transcrição ficar boa (vocabulário técnico certo, sem trocas por outro idioma), me diga em uma frase: **de que é o áudio e em que idioma**?"

Uma frase basta. Defaults se o usuário não responder: `idioma=pt`, `materia="generico"` (sem vocabulário técnico específico).

---

## Política de modelo e timestamps

| Modo | Modelo | Saída | Custo/min* | Quando usar |
|---|---|---|---|---|
| **Padrão** | `gpt-4o-mini-transcribe` | Texto corrido sem timestamps | $0,003 | 95% dos casos — aula, podcast, entrevista |
| **Com timestamps** | `whisper-1` | Texto + segments `[ss.fff]` granulares | $0,006 | Quando o material será navegado por tempo (vídeo-aula longa, citação em estudo) |

*valores aproximados OpenAI; confirme em platform.openai.com para uso em volume.

### Por que dois modelos

- `gpt-4o-mini-transcribe` é a receita otimizada padrão — não retorna `verbose_json` (sem timestamps por segmento). **Use sempre que possível.**
- `whisper-1` é o único modelo OpenAI que aceita `verbose_json` e devolve timestamps granulares. Para material que será citado por tempo no estudo (ex.: "o que ele disse aos 12:34?"), é o caminho.

A diferença entre os dois é de **granularidade do output**, não de qualidade de transcrição (a receita otimizada bate ~96% do Turboscribe em qualquer dos dois para áudio limpo em PT-BR).

### Ativar timestamps

```bash
TRANSCRIBE_TIMESTAMPS=1 .claude/skills/study-audio-capture/scripts/transcrever-api.sh \
  audio.mp3 \
  data/audios/aulas/<materia>/<unidade> \
  pt \
  "prompt-curto-de-estilo"
```

Quando ligado, o pipeline gera — além do `<stem>.txt` de sempre — `<stem>.segments.json` (`[{start, end, text}, ...]` em segundos, 3 casas) e `<stem>-timestamps.md` (blocos `[mm:ss]`, formatação mecânica de navegação).

---

## Pipeline de execução

### Etapa 1 — Staging

O wrapper `bin/transcribe` (em `.claude/skills/study-audio-capture/bin/transcribe`) resolve a raiz do projeto a partir do próprio caminho (portátil: Linux/macOS/Git Bash/MSYS2/WSL) e carrega a chave de `~/.openai_env` (ou `%USERPROFILE%\.openai_env` no Windows).

Durante o pipeline, chunks e respostas intermediárias ficam em `data/audios/.work/<job-id>/`, removido por `trap` ao terminar (sucesso ou falha). A variável `WORK_DIR` permite redirecionar (ex.: CI em outro FS). O `transcrever-api.sh` usa esse staging; o wrapper sozinho só faz o exec do CLI.

### Etapa 2 — Detectar tamanho e dividir (>25MB?)

A API OpenAI rejeita arquivos >25 MB. Quando o áudio é maior:

- Calcular bitrate efetivo = `tamanho_bytes × 8 / duração_segundos`
- Escolher `chunk_seconds` = `(MAX_BYTES × 0.70) × 8 / bitrate`, mínimo 60s
- Re-encoding (NÃO `-c copy`) — MP3 VBR com `-c copy` gera centenas de mini-chunks de 12s. Re-encoding com `-ac 1 -ar 16000 -b:a 64k` resolve.
- Cada chunk vira uma chamada API independente; offsets acumulados preservam a timeline global.

### Etapa 3 — Transcrição

```bash
transcrever-api.sh <audio> data/audios/aulas/<materia>/<unidade>/ <lang> "<prompt>"
```

- A IA **DEVE** passar `out-dir` apontando pro destino final (`data/audios/aulas/<materia>/<unidade>/`) — os arquivos já saem lá.
- Sem `out-dir`, o script usa `data/audios/.raw/<job-id>/` (área crua persistente) como fallback — nunca lixeira silenciosa.
- O staging de chunks fica em `data/audios/.work/<job-id>/` e é **sempre** removido ao final (`trap`, inclusive em falha).

### Etapa 4 — Renomear para a convenção `parteN`

O script nomeia os arquivos com o `<stem>` do arquivo de entrada. Ao final, renomeie:

```bash
cd data/audios/aulas/<materia>/<unidade>/
mv "<stem>.txt" parteN.txt
[ -f "<stem>.segments.json" ] && mv "<stem>.segments.json" parteN.segments.json
[ -f "<stem>-timestamps.md" ] && mv "<stem>-timestamps.md" parteN-timestamps.md
```

### Etapa 5 — Gerar as 4 saídas elaboradas (a IA faz)

A IA lê o `.txt` cru e gera os 4 arquivos em `data/estudos/aulas/<materia>/<unidade>/parteN/`:

**Transcrição (`-transcricao.md`):**
- Pontuação, capitalização, parágrafos
- Remove disfluências ("né", "tá", "ah", repetições, "é... é assim")
- Preserva 100% do conteúdo substantivo (termos, dados, exemplos, números, nomes)
- Marca com `[trecho impreciso]` quando frase ambígua sem contexto visual/gestual
- Junta frases quebradas artificialmente por pausas ou ruído

**Resumo (`-resumo.md`):**
- Tese central em 1-2 frases
- Estrutura da aula em 3-7 seções numeradas
- Conclusões-chave (5-8 bullets do tipo "o que guardar pra prova")
- ~1 página máximo

**Pontos (`-pontos.md`):**
- Lista numerada de TODOS os pontos distintos
- Agrupados por seção/tema
- Sem filtrar por importância (aluno decide)
- Sub-bullets quando necessário (detalhe, exemplo, exceção)

**Perguntas de conversa (`-conversa.md`):**
- 5 perguntas que estimulem **falar/escrever** sobre o conteúdo
- Devem forçar raciocínio aplicado (resolver, comparar, decidir) — não definição de glossário
- Estrutura sugerida (adaptar ao domínio do material):
  - 1 cenário prático / caso aplicado
  - 1 comparação ou distinção (diferencial, contraste entre conceitos)
  - 1 interpretação (imagem, gráfico, tabela, dado)
  - 1 explicação para leigo
  - 1 classificação/escala
- Cada pergunta vem com instruções de auto-avaliação

### Etapa 6 — Indexação (opcional, recomendado)

A transcrição limpa (`-transcricao.md`) é o que deve ser indexado em `data/biblioteca/` com `tags:` apropriadas (RAG local). A partir daí, qualquer pergunta do aluno é respondida citando o trecho (e o timestamp, quando o material tiver).

---

## Estrutura final do diretório (exemplos)

**Material de livro bíblico (capítulos):**
```
data/audios/aulas/romanos/4/parte1.txt
data/audios/aulas/romanos/4/parte2.txt
data/audios/aulas/romanos/5/parte1.txt

data/estudos/aulas/romanos/4/parte1/parte1-transcricao.md
data/estudos/aulas/romanos/4/parte1/parte1-resumo.md
data/estudos/aulas/romanos/4/parte1/parte1-pontos.md
data/estudos/aulas/romanos/4/parte1/parte1-conversa.md
data/estudos/aulas/romanos/4/parte2/...
```

Aula avulsa (série numerada):
```
data/audios/aulas/cardiologia/aula-1/parte1.txt
data/audios/aulas/cardiologia/aula-1/parte2.txt
data/audios/aulas/cardiologia/aula-2/parte1.txt
```

Seminário mensal datado:
```
data/audios/aulas/teologia-pratica/10-09-2026/parte1.txt
data/audios/aulas/teologia-pratica/10-09-2026/parte2.txt
data/audios/aulas/teologia-pratica/15-10-2026/parte1.txt
```

Tema específico sem série:
```
data/audios/aulas/ingles/revisao/parte1.txt
```

---

## Gate local vs API (legacy)

- **API (recomendado)** — `bin/transcribe` + `transcrever-api.sh` desta skill. Custo baixo, qualidade alta.
- **Local (Whisper `faster-whisper`)** — `scripts/transcrever.sh` legacy da skill. Lento mas privado e grátis.

Em ambos os casos, **as convenções de pasta acima se aplicam** — só muda quem produz o `.txt` cru. No modo local, o cru sai em `data/audios/.raw/<stem>-raw.txt` e a IA move para `data/audios/aulas/<materia>/<unidade>/parteN.txt` na Etapa 4.

---

## Qualidade e limitações

- API padrão (`gpt-4o-mini-transcribe`) com receita otimizada: ~96% do Turboscribe em áudio PT-BR limpo
- Whisper-1 com timestamps: mesma qualidade + metadados temporais
- Áudios >1h: chunks de ~14 min cada (re-encoding); offset preservado
- Whisper local (`faster-whisper`): sem limite de tamanho, mas ~5-10× mais lento sem GPU
- Sem diarização nativa nos modelos atuais (multi-falante exige `gpt-4o-transcribe-diarize`)

## Dependências

```
ffmpeg                              (sistema)
openai>=1.0                         (pip, no venv .venv-transcribe)

# Modo local opcional:
faster-whisper==1.0.4
numpy>=1.24.0
pydantic>=2.0.0
```

## Referências

- `bin/transcribe` — wrapper portátil (Linux/macOS/Git Bash/MSYS2/WSL) para o CLI Python da skill `transcribe`
- `scripts/transcrever-api.sh` — pipeline completo (split + API + format `.txt` + segments JSON opcional)
- `scripts/transcrever.sh` — pipeline Whisper local (legacy)
- `estudo-fluxo-02-organizar/SKILL.md` — como este material entra no fluxo de estudo
- `study-processar-video/SKILL.md` — pipeline equivalente para vídeo
- `study-rag-local/SKILL.md` — indexação para busca
