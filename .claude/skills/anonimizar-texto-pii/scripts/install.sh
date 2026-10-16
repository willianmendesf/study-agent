#!/usr/bin/env bash
set -euo pipefail

BASE="${ANON_HOME:-$HOME/.local/share/anonimizador-dp}"
VENV="${BASE}/venv"
VERSION="1.1.0"
MODEL_URL="https://github.com/anatelgovbr/anonimizador-dp/releases/download/v${VERSION}/modelo_ner.zip"
MODEL_SHA256="a841403e170bf520c9aa970233436fd4795dda8e1390e3830f791c708f3abbab"

log() { printf '[anonimizador] %s\n' "$*"; }

install -d -m 700 "$BASE"
python3 -c 'import venv, ensurepip' >/dev/null 2>&1 || { log "python3-venv ausente; instale e rode de novo" >&2; exit 1; }
[ -x "${VENV}/bin/python" ] || python3 -m venv "$VENV"
"${VENV}/bin/pip" -q install "anonimizador-dp==${VERSION}"

if [ ! -d "${BASE}/model" ]; then
  command -v unzip >/dev/null 2>&1 || { log "unzip ausente; instale e rode de novo" >&2; exit 1; }
  TMP="$(mktemp -d)"
  curl -fsSL -o "${TMP}/modelo_ner.zip" "$MODEL_URL"
  echo "${MODEL_SHA256}  ${TMP}/modelo_ner.zip" | sha256sum -c - >/dev/null \
    || { log "checksum do modelo divergente; abortando" >&2; exit 1; }
  mkdir "${TMP}/x"
  unzip -q "${TMP}/modelo_ner.zip" -d "${TMP}/x"
  mv "${TMP}"/x/modelo_* "${BASE}/model"
fi

printf '{"text":"CPF 123.456.789-09"}' | ANON_HOME="$BASE" "${VENV}/bin/python" \
  "$(dirname "$0")/anonymize.py" >/dev/null || { log "autoteste falhou" >&2; exit 1; }
log "pronto: ${VENV}/bin/python"
