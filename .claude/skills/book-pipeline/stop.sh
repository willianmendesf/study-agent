#!/bin/bash
# stop.sh — Para o servidor book-pipeline
# Uso: bash .claude/skills/book-pipeline/stop.sh

echo "🛑 Parando book-pipeline..."

# Mata o servidor
pkill -f "server-livros.py" 2>/dev/null && echo "   ✅ servidor parado" || echo "   ⚠️  servidor não estava rodando"

# Mata o supervisor
pkill -f "supervisor-livros.sh" 2>/dev/null && echo "   ✅ supervisor parado" || echo "   ⚠️  supervisor não estava rodando"

# NÃO deleta state (preserva progresso)
# Para limpar tudo: rm /tmp/server-livros-state.json

echo ""
echo "Estado preservado em /tmp/server-livros-state.json"
echo "Para reiniciar: bash $0/../start.sh  # o start.sh cria o supervisor"
echo "Para limpar TUDO: bash $0/../clean.sh"