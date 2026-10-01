#!/usr/bin/env bash
# memos-post.sh — posta conteúdo no Memos
# Uso: memos-post.sh [--file PATH | --content "texto"] [--visibility PRIVATE|PUBLIC] [--tags "tag1,tag2"] [--dry-run]
# Lê config de data/config-backup/memos/memos.env (chmod 600).
set -euo pipefail

REPO="/home/opencode/study-agent/data"
ENV_FILE="$REPO/config-backup/memos/memos.env"

if [[ ! -f "$ENV_FILE" ]]; then
  echo "✗ memos.env não encontrado em $ENV_FILE" >&2
  exit 2
fi

# shellcheck disable=SC1090
source "$ENV_FILE"

if [[ -z "${MEMOS_URL:-}" || -z "${MEMOS_PAT:-}" ]]; then
  echo "✗ MEMOS_URL ou MEMOS_PAT vazio no memos.env" >&2
  exit 2
fi

FILE=""
CONTENT=""
VIS="PRIVATE"
TAGS=""
DRY=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    --file) FILE="$2"; shift 2 ;;
    --content) CONTENT="$2"; shift 2 ;;
    --visibility) VIS="$2"; shift 2 ;;
    --tags) TAGS="$2"; shift 2 ;;
    --dry-run) DRY=1; shift ;;
    -h|--help)
      sed -n '2p;3p' "$0"; sed -n '/^# Uso:/,/^## /p' "$0" | head -10
      exit 0
      ;;
    *) echo "✗ flag desconhecida: $1" >&2; exit 2 ;;
  esac
done

# lê conteúdo do arquivo se --file
if [[ -n "$FILE" ]]; then
  if [[ ! -f "$FILE" ]]; then
    echo "✗ arquivo não existe: $FILE" >&2
    exit 2
  fi
  CONTENT="$(cat "$FILE")"
fi

if [[ -z "$CONTENT" ]]; then
  echo "✗ precisa de --file ou --content" >&2
  exit 2
fi

# tamanho trava (108192 bytes = ~106 KB — limite efetivo do Memos)
SIZE=$(printf '%s' "$CONTENT" | wc -c)
if [[ $SIZE -gt 108192 ]]; then
  echo "✗ conteúdo muito grande ($SIZE bytes > 108192). Quebre em seções." >&2
  exit 2
fi

# anexa tags ao final como hashtags (Memos aceita)
if [[ -n "$TAGS" ]]; then
  # transforma "tag1,tag2" em "#tag1 #tag2"
  TAGS_FORMATTED=""
  IFS=',' read -ra ARR <<< "$TAGS"
  for t in "${ARR[@]}"; do
    t_trim="$(echo "$t" | xargs)"
    [[ -n "$t_trim" ]] && TAGS_FORMATTED+="#${t_trim} "
  done
  CONTENT+=$'\n\n'"$TAGS_FORMATTED"
fi

# monta JSON via python (seguro contra aspas)
JSON=$(python3 -c '
import json, sys
content = sys.stdin.read()
vis = sys.argv[1]
print(json.dumps({"content": content, "visibility": vis}, ensure_ascii=False))
' "$VIS" <<< "$CONTENT")

if [[ $DRY -eq 1 ]]; then
  echo "=== DRY RUN — JSON que seria enviado ==="
  echo "$JSON" | python3 -m json.tool | head -30
  echo "..."
  echo "endpoint: POST ${MEMOS_URL%/}/api/v1/memos"
  exit 0
fi

# POST
HTTP=$(curl -sS -o /tmp/memos-resp.$$ -w "%{http_code}" \
  -X POST "${MEMOS_URL%/}/api/v1/memos" \
  -H "Authorization: Bearer ${MEMOS_PAT}" \
  -H "Content-Type: application/json" \
  --data-binary "$JSON")

RESP=$(cat /tmp/memos-resp.$$)
rm -f /tmp/memos-resp.$$

if [[ "$HTTP" == "200" || "$HTTP" == "201" ]]; then
  ID=$(echo "$RESP" | python3 -c 'import json,sys; d=json.loads(sys.stdin.read()); print(d.get("name","?"))' 2>/dev/null || echo "?")
  echo "✓ memo criado: $ID"
  exit 0
else
  echo "✗ falha HTTP $HTTP" >&2
  echo "$RESP" | head -c 500 >&2
  echo "" >&2
  exit 1
fi
