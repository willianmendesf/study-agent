#!/usr/bin/env bash
set -e
ESP_DIR=/home/study-agent/data/perfil/especialistas
MEM_DIR=/home/study-agent/data/perfil/memorias
mkdir -p "$MEM_DIR"

# Apresentações por persona (1 linha, em pt-BR)
declare -A APRES=(
  [hermes]="Eu sou Hermes, exegeta bíblico reformado."
  [hermeneia]="Eu sou Hermeneia, professora de hermenêutica."
  [homologia]="Eu sou Homologia, teóloga sistemática."
  [histor]="Eu sou Histor, cronista da história da Igreja."
  [eusebeia]="Eu sou Eusebeia, guia devocional."
  [darshan]="Eu sou Darshan, companheira de leitura contemplativa."
  [kerux]="Eu sou Kerux, pregadora."
  [kairos]="Eu sou Kairos, gestor do seu tempo e estudos."
  [kritikos]="Eu sou Kritikos, crítico textual e apologista."
  [rhetor]="Eu sou Rhetor, pregador e orador."
  [anglista]="Eu sou Anglista, professora de inglês bíblico."
  [bereiano]="Eu sou Bereiano, conselheiro bíblico."
  [areopago]="Eu sou Areópago, filósofo cristão."
  [antropos]="Eu sou Antropos, antropólogo bíblico."
  [aporia]="Eu sou Aporia, levantadora de questões."
  [zetesis]="Eu sou Zetesis, pesquisadora metodológica."
  [dialektikos]="Eu sou Dialektikos, lógica e argumentação."
  [literato]="Eu sou Literato, analista de literatura."
  [portuga]="Eu sou Portuga, professora de português e redação."
)

# Mapa de voz por persona (Plano C)
declare -A VOZ=(
  [hermes]="speaches-ai/piper-pt_BR-faber-medium|faber"
  [homologia]="speaches-ai/piper-pt_BR-faber-medium|faber"
  [histor]="speaches-ai/piper-pt_BR-faber-medium|faber"
  [kritikos]="speaches-ai/piper-pt_BR-faber-medium|faber"
  [rhetor]="speaches-ai/piper-pt_BR-faber-medium|faber"
  [kairos]="speaches-ai/piper-pt_BR-faber-medium|faber"
  [anglista]="speaches-ai/piper-pt_BR-faber-medium|faber"
  [bereiano]="speaches-ai/piper-pt_BR-faber-medium|faber"
  [areopago]="speaches-ai/piper-pt_BR-faber-medium|faber"
  [antropos]="speaches-ai/piper-pt_BR-faber-medium|faber"
  [hermeneia]="speaches-ai/Kokoro-82M-v1.0-ONNX-int8|pf_dora"
  [eusebeia]="speaches-ai/Kokoro-82M-v1.0-ONNX-int8|pf_dora"
  [darshan]="speaches-ai/Kokoro-82M-v1.0-ONNX-int8|pf_dora"
  [kerux]="speaches-ai/Kokoro-82M-v1.0-ONNX-int8|pf_dora"
  [literato]="speaches-ai/Kokoro-82M-v1.0-ONNX-int8|pf_dora"
  [portuga]="speaches-ai/Kokoro-82M-v1.0-ONNX-int8|pf_dora"
  [dialektikos]="speaches-ai/Kokoro-82M-v1.0-ONNX-int8|pf_dora"
  [aporia]="speaches-ai/Kokoro-82M-v1.0-ONNX-int8|pf_dora"
  [zetesis]="speaches-ai/Kokoro-82M-v1.0-ONNX-int8|pf_dora"
)

for persona in "${!APRES[@]}"; do
  yaml="$ESP_DIR/$persona.yaml"
  [ -f "$yaml" ] || { echo "FALTA: $persona"; continue; }
  IFS='|' read -r modelo voz <<<"${VOZ[$persona]}"
  printf "\n\n# ============================================================\n# ÁUDIO — TTS/STT via Speaches (LXC 140) — adicionado 2026-10-06\n# ============================================================\naudio:\n  enabled: true\n  tts_url: \"http://192.168.15.140:8000/v1/audio/speech\"\n  stt_url: \"http://192.168.15.140:8000/v1/audio/transcriptions\"\n  modelo: \"${modelo}\"\n  voz: \"${voz}\"\n  formato: \"mp3\"\n  chat_id: \"916214383\"\n  bot_nome: \"${persona^}\"\n  apresentacao: \"${APRES[$persona]}\"\n" >> "$yaml"
echo "OK $persona -> $(basename $yaml)"
done

# Bibliotecário: enabled=false, sem voz
yaml="$ESP_DIR/bibliotecario.yaml"
printf "\n\n# ============================================================\n# ÁUDIO — desabilitado (técnico, não fala)\n# ============================================================\naudio:\n  enabled: false\n  motivo: \"especialista técnico de biblioteca; só catalogação, sem fala\"\n" >> "$yaml"
echo "OK bibliotecario (mudo)"