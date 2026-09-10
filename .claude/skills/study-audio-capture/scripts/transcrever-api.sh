#!/usr/bin/env bash
# transcrever-api.sh — transcrição via OpenAI (texto corrido ou com timestamps)
#
# Pipeline determinístico sobre a skill `transcribe`:
#   1. Se áudio >23.6MB (~90% do limite de 25MB): divide em chunks por re-encoding
#      (NÃO `-c copy` — MP3 VBR com -c copy gera centenas de mini-chunks de ~12s)
#   2. Chama a API por chunk, no modo escolhido:
#        - padrão      → gpt-4o-mini-transcribe, texto corrido
#        - timestamps  → whisper-1 + verbose_json, segmentos com [mm:ss]
#   3. Concatena/alinha e grava no out-dir:
#        - <stem>.txt              (sempre — transcrição crua)
#        - <stem>.segments.json    (só no modo timestamps — timeline bruta)
#        - <stem>-timestamps.md    (só no modo timestamps — formatação mecânica [mm:ss])
#
# Uso:
#   transcrever-api.sh <audio> [out-dir] [lang] [prompt]
#
# Variáveis de ambiente:
#   TRANSCRIBE_LANG        idioma (default: pt)
#   TRANSCRIBE_PROMPT      prompt guia — CURTO, só estilo/idioma (default: vazio)
#   TRANSCRIBE_MODEL       overrides o modelo do modo atual
#   TRANSCRIBE_TIMESTAMPS  "1" liga o modo timestamps (whisper-1 + verbose_json)
#   TRANSCRIBE_BIN         path alternativo do wrapper `transcribe`
#   WORK_DIR               staging (default: data/audios/.work/<stem>-<HHMMSS>)
#
# Saída default (sem out-dir): data/audios/.raw/<stem>-<HHMMSS>/
# O staging em data/audios/.work/<job-id>/ é removido ao final (trap), sempre.

set -euo pipefail

ARQUIVO="${1:-}"
OUT_DIR="${2:-}"
LANG_ARG="${3:-${TRANSCRIBE_LANG:-pt}}"
PROMPT_ARG="${4:-${TRANSCRIBE_PROMPT:-}}"

if [[ "${TRANSCRIBE_TIMESTAMPS:-0}" == "1" ]]; then
  # whisper-1 é o único modelo OpenAI que aceita verbose_json com segmentos
  MODEL="${TRANSCRIBE_MODEL:-whisper-1}"
  USE_TIMESTAMPS=1
else
  MODEL="${TRANSCRIBE_MODEL:-gpt-4o-mini-transcribe}"
  USE_TIMESTAMPS=0
fi

SKILL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
STUDY_AGENT_ROOT="$(cd "$SKILL_DIR/../../.." && pwd -P)"
WRAPPER="${TRANSCRIBE_BIN:-$SKILL_DIR/bin/transcribe}"

[[ -n "$ARQUIVO" ]] || { echo "Uso: $0 <audio> [out-dir] [lang] [prompt]" >&2; exit 1; }
[[ -f "$ARQUIVO" ]] || { echo "ERRO: arquivo não encontrado: $ARQUIVO" >&2; exit 1; }
command -v ffmpeg >/dev/null || { echo "ERRO: ffmpeg não instalado" >&2; exit 1; }
command -v ffprobe >/dev/null || { echo "ERRO: ffprobe não instalado (vem com ffmpeg)" >&2; exit 1; }

human_bytes() { numfmt --to=iec "$1" 2>/dev/null || echo "${1} bytes"; }

STEM="$(basename "$ARQUIVO")"; STEM="${STEM%.*}"
JOB_ID="${STEM}-$(date +%H%M%S)"

WORK="${WORK_DIR:-$STUDY_AGENT_ROOT/data/audios/.work/$JOB_ID}"
mkdir -p "$WORK"
trap 'rm -rf "$WORK"' EXIT   # staging (chunks) sempre limpo

# Destino default: área crua persistente (não some ao sair)
OUT_DIR="${OUT_DIR:-$STUDY_AGENT_ROOT/data/audios/.raw/$JOB_ID}"
mkdir -p "$OUT_DIR"

SIZE=$(wc -c < "$ARQUIVO")
MAX_BYTES=$((25 * 1024 * 1024 * 90 / 100))   # 90% de 25MB (margem de segurança)

CHUNK_ARGS=()
if [[ "$SIZE" -le "$MAX_BYTES" ]]; then
  echo "→ [1/3] Áudio $(human_bytes "$SIZE") — dentro do limite, sem split"
  CHUNK_ARGS=("$ARQUIVO")
else
  DUR=$(ffprobe -v error -show_entries format=duration -of csv=p=0 "$ARQUIVO" 2>/dev/null | cut -d. -f1)
  if [[ -z "$DUR" || "$DUR" -lt 1 ]]; then
    echo "ERRO: não consegui detectar duração do áudio" >&2; exit 1
  fi
  BITRATE=$(awk -v s="$SIZE" -v d="$DUR" 'BEGIN{printf "%.0f", s*8/d}')
  echo "→ [1/3] Áudio $(human_bytes "$SIZE"), ${DUR}s, ~${BITRATE}bps — vai precisar de split"

  TARGET_BYTES=$((MAX_BYTES * 70 / 100))
  CHUNK_SEC=$(awk -v t="$TARGET_BYTES" -v b="$BITRATE" 'BEGIN{printf "%d", t*8/b}')
  CHUNK_SEC=$((CHUNK_SEC < 60 ? 60 : CHUNK_SEC))
  echo "    chunks de ~${CHUNK_SEC}s"

  mkdir -p "$WORK/chunks"
  ffmpeg -y -loglevel error \
    -i "$ARQUIVO" \
    -f segment -segment_time "$CHUNK_SEC" -reset_timestamps 1 \
    -ac 1 -ar 16000 -b:a 64k \
    "$WORK/chunks/${STEM}_%03d.mp3"
  shopt -s nullglob
  CHUNK_ARGS=("$WORK/chunks/${STEM}"_*.mp3)
  shopt -u nullglob
fi

echo "→ [2/3] Transcrevendo ${#CHUNK_ARGS[@]} chunk(s) com $MODEL (timestamps=$USE_TIMESTAMPS)..."
[[ -n "$PROMPT_ARG" ]] && echo "    prompt=\"${PROMPT_ARG:0:80}...\""

for i in "${!CHUNK_ARGS[@]}"; do
  CHUNK="${CHUNK_ARGS[$i]}"

  PROMPT_FLAG=()
  [[ -n "$PROMPT_ARG" ]] && PROMPT_FLAG+=(--prompt "$PROMPT_ARG")

  if [[ "$USE_TIMESTAMPS" == "1" ]]; then
    # whisper-1 não aceita chunking_strategy — omitido aqui
    "$WRAPPER" \
      "$CHUNK" \
      --model "$MODEL" \
      --language "$LANG_ARG" \
      --response-format verbose_json \
      "${PROMPT_FLAG[@]}" \
      --out "$WORK/chunk_$i.json" >/dev/null
  else
    "$WRAPPER" \
      "$CHUNK" \
      --model "$MODEL" \
      --language "$LANG_ARG" \
      --chunking-strategy auto \
      "${PROMPT_FLAG[@]}" \
      --out "$WORK/chunk_$i.txt" >/dev/null
  fi

  CHUNK_DUR=$(ffprobe -v error -show_entries format=duration -of csv=p=0 "$CHUNK" | cut -d. -f1)
  printf "    chunk %d/%d (%ss) — ok\n" "$((i+1))" "${#CHUNK_ARGS[@]}" "$CHUNK_DUR"
done

if [[ "$USE_TIMESTAMPS" == "1" ]]; then
  echo "    reconstruindo timeline global..."
  python3 << PY
import json
from pathlib import Path

work = Path('$WORK')
out_dir = Path('$OUT_DIR')
stem = '${STEM}'
model = '$MODEL'

offset = 0.0
all_segments = []
language = '?'

for cf in sorted(work.glob('chunk_*.json')):
    data = json.load(open(cf))
    language = data.get('language', language)
    for s in data.get('segments', []):
        all_segments.append({
            'start': round(s['start'] + offset, 3),
            'end': round(s['end'] + offset, 3),
            'text': s['text'].strip(),
        })
    offset += data.get('duration', 0) or 0

total_dur = all_segments[-1]['end'] if all_segments else 0
segments_doc = {
    'language': language,
    'model': model,
    'total_duration': round(total_dur, 3),
    'segments': all_segments,
}
(out_dir / f'{stem}.segments.json').write_text(
    json.dumps(segments_doc, ensure_ascii=False, indent=2), encoding='utf-8')

def fmt(t):
    return f'[{int(t // 60):02d}:{int(t % 60):02d}]'

# agrupa segmentos em blocos (pausa > 5s ou 6 segmentos) para parágrafos legíveis
blocks, cur, last_end = [], [], -1.0
for s in all_segments:
    if not cur:
        cur = [s]
    elif s['start'] - last_end > 5 or len(cur) >= 6:
        blocks.append(cur); cur = [s]
    else:
        cur.append(s)
    last_end = s['end']
if cur:
    blocks.append(cur)

# 1) <stem>.txt — transcrição crua em parágrafos (sem timestamps)
paras = [' '.join(b['text'] for b in blk if b['text']).strip() for blk in blocks]
(out_dir / f'{stem}.txt').write_text('\n\n'.join(p for p in paras if p) + '\n', encoding='utf-8')

# 2) <stem>-timestamps.md — formatação mecânica com [mm:ss] por bloco
lines = [
    f'# Transcrição — {stem}',
    '',
    f'- Idioma detectado: \`{language}\`',
    f'- Segmentos: {len(all_segments)}',
    f'- Duração: ~{int(total_dur // 60)}m{int(total_dur) % 60:02d}s',
    f'- Modelo: {model}',
    '',
    '---',
    '',
]
for blk in blocks:
    lines.append(f'## {fmt(blk[0]["start"])}')
    lines.append('')
    lines.append(' '.join(b['text'] for b in blk if b['text']).strip())
    lines.append('')
(out_dir / f'{stem}-timestamps.md').write_text('\n'.join(lines), encoding='utf-8')

print(f'    {len(all_segments)} segments, {round(total_dur/60,1)} min')
PY
else
  # modo padrão: concatena os textos crus dos chunks
  cat "$WORK"/chunk_*.txt > "$OUT_DIR/${STEM}.txt"
  echo "    txt: $(wc -l < "$OUT_DIR/${STEM}.txt") linhas"
fi

echo "→ [3/3] Concluído"
ls -lh "$OUT_DIR" 2>/dev/null | tail -4
