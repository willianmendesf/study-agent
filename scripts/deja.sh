#!/bin/sh
# Consulta o deja (memória entre sessões). Uso: sh scripts/deja.sh "<termo>"
DEJA=".claude/skills/deja-search/bin/linux_amd64/deja"
if [ ! -x "$DEJA" ]; then
  echo "deja nao encontrado em $DEJA" >&2
  exit 2
fi
exec "$DEJA" "$@"
