#!/usr/bin/env bash
# transcrever.sh — transcrição via Whisper local (faster-whisper)
# Saída: texto CRU (sem pontuação/formatação) em data/audios/.raw/ — a IA elabora
# depois (ver SKILL.md, Etapa 5) e move o cru pra data/audios/aulas/... na Etapa 4.
# Sem dependência de serviço LLM externo.
#
# Uso:
#   ./transcrever.sh <arquivo-audio-ou-video> [idioma]

set -euo pipefail

ARQUIVO="${1:-}"
IDIOMA="${2:-pt}"

SKILL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
# Saída vai para data/ (dado pessoal do usuário), NUNCA para dentro de .claude/skills/
# (isso é pasta do FRAMEWORK — ver CLAUDE.md Regra 3/7). Raiz do study-agent = 3 níveis
# acima de .claude/skills/study-audio-capture/scripts/.
STUDY_AGENT_ROOT="$(cd "$SKILL_DIR/../../.." && pwd)"
SAIDA_DIR="$STUDY_AGENT_ROOT/data/audios/.raw"

if [[ -z "$ARQUIVO" ]]; then
  echo "Uso: $0 <arquivo> [idioma]" >&2
  exit 1
fi

[[ -f "$ARQUIVO" ]] || { echo "ERRO: arquivo não encontrado: $ARQUIVO" >&2; exit 1; }
command -v ffmpeg >/dev/null || { echo "ERRO: ffmpeg não instalado (apt/brew install ffmpeg)" >&2; exit 1; }
python3 -c "import faster_whisper" 2>/dev/null || {
  echo "ERRO: faster-whisper não instalado. Rode:" >&2
  echo "  pip install -r $SKILL_DIR/requirements.txt" >&2
  exit 1
}

BASE=$(basename "$ARQUIVO")
STEM="${BASE%.*}"
WORK="$STUDY_AGENT_ROOT/data/audios/.work/local-$STEM-$(date +%H%M%S)"
mkdir -p "$SAIDA_DIR" "$WORK"
trap 'rm -rf "$WORK"' EXIT   # WAV de trabalho sempre limpo

echo "→ [1/2] Convertendo para WAV 16kHz mono..."
ffmpeg -y -i "$ARQUIVO" -ar 16000 -ac 1 "$WORK/$STEM.wav" 2>/dev/null || {
  echo "ERRO: conversão falhou" >&2
  exit 1
}

echo "→ [2/2] Transcrevendo com Whisper (GPU local se disponível)... (pode demorar)"

python3 - "$WORK/$STEM.wav" "$IDIOMA" "$SAIDA_DIR/$STEM-raw.txt" <<'PYEOF'
import sys
from faster_whisper import WhisperModel

wav_path, idioma, out_path = sys.argv[1], sys.argv[2], sys.argv[3]

# Auto-detect device (GPU if available, else CPU)
try:
    import torch
    device = "cuda" if torch.cuda.is_available() else "cpu"
    compute_type = "int8" if device == "cuda" else "float32"
    print(f"Device auto-detected: {device} (compute_type: {compute_type})")
except ImportError:
    device = "cpu"
    compute_type = "float32"
    print("Device: CPU (torch não instalado — fallback)")

model = WhisperModel("large-v3", device=device, compute_type=compute_type)
segments, info = model.transcribe(
    wav_path,
    language=idioma,
    vad_filter=True,
    condition_on_previous_text=False,
    beam_size=5,
    initial_prompt=f"Transcrição de aula em {idioma}.",
)
text = " ".join(s.text.strip() for s in segments)

with open(out_path, "w", encoding="utf-8") as f:
    f.write(text)

print(f"DONE len: {len(text)}")
PYEOF

[[ -s "$SAIDA_DIR/$STEM-raw.txt" ]] || { echo "ERRO: transcrição falhou (saída vazia)" >&2; exit 1; }

echo "✓ Transcrição crua salva: $SAIDA_DIR/$STEM-raw.txt"
echo ""
echo "Próximo passo (a IA faz, não este script):"
echo "  1. Ler $SAIDA_DIR/$STEM-raw.txt"
echo "  2. Elaborar as 4 saídas em data/estudos/aulas/<materia>/<unidade>/parteN/"
echo "  3. Mover o cru pra data/audios/aulas/<materia>/<unidade>/parteN.txt"
echo "  Ver: SKILL.md, Etapas 4 e 5."
