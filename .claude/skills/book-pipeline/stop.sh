#!/bin/bash
# stop.sh — Para o servidor book-pipeline
# Uso: bash .claude/skills/book-pipeline/stop.sh

echo "🛑 Parando book-pipeline..."

SKILL_DIR="$(cd "$(dirname "$0")" && pwd)"
STATE="$(cd "$SKILL_DIR/../../.." && pwd)/data/perfil/book-pipeline-state.json"

# Mata o servidor
pkill -f "book-pipeline/server.py" 2>/dev/null && echo "   ✅ servidor parado" || echo "   ⚠️  servidor não estava rodando"

# Mata o supervisor
pkill -f "supervisor-livros.sh" 2>/dev/null && echo "   ✅ supervisor parado" || echo "   ⚠️  supervisor não estava rodando"

# NÃO deleta state (preserva progresso — vive em data/, sobrevive a reboot)
# Para limpar tudo: rm "$STATE"

echo ""
echo "Estado preservado em $STATE"
echo "Para reiniciar: bash \"$(dirname "$0")/start.sh\""
echo "Para limpar tudo: rm \"$STATE\""