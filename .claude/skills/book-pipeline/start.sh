#!/bin/bash
# start.sh — Sobe o servidor book-pipeline em background (imune a fechar terminal)
# Uso: bash .claude/skills/book-pipeline/start.sh
#      # Para parar: bash .claude/skills/book-pipeline/stop.sh

SKILL_DIR="$(cd "$(dirname "$0")" && pwd)"
SERVER="$SKILL_DIR/server.py"
LOG="/tmp/server-livros.log"
SUPERVISOR="/tmp/supervisor-livros.sh"
PORT="${PORT:-8765}"

# Cria supervisor script (loop imortal)
cat > "$SUPERVISOR" <<EOF
#!/bin/bash
SCRIPT="$SERVER"
SCRIPT_LOG="/tmp/server-livros.log"
echo "\$(date) [supervisor] iniciando book-pipeline" >> "\$SCRIPT_LOG"
pkill -f "server-livros.py" 2>/dev/null
sleep 1
while true; do
  echo "\$(date) [supervisor] iniciando server-livros.py" >> "\$SCRIPT_LOG"
  PORT="$PORT" python3 "\$SCRIPT" >> "\$SCRIPT_LOG" 2>&1
  echo "\$(date) [supervisor] server morreu, reiniciando em 3s" >> "\$SCRIPT_LOG"
  sleep 3
done
EOF
chmod +x "$SUPERVISOR"

# Mata instâncias anteriores
pkill -f "supervisor-livros.sh" 2>/dev/null
pkill -f "server-livros.py" 2>/dev/null
sleep 1

# Sobe em background com setsid + nohup (imune a SIGHUP)
nohup setsid bash "$SUPERVISOR" > /tmp/supervisor-stdout.log 2>&1 < /dev/null &
SUP_PID=$!
disown
sleep 3

# Verifica se subiu
if curl -s --max-time 3 http://localhost:$PORT/health >/dev/null 2>&1; then
  echo "=========================================="
  echo "✅ book-pipeline servidor online!"
  echo "=========================================="
  echo ""
  echo "🌐 URL:    http://localhost:$PORT"
  echo "📋 Log:    tail -f $LOG"
  echo "🛑 Parar:  bash $SKILL_DIR/stop.sh"
  echo "📊 Status: curl -s http://localhost:$PORT/worker-status"
  echo ""
  echo "▶  Para processar livros:"
  echo "   1. Abra http://localhost:$PORT no navegador"
  echo "   2. Clique em 'TRAZER TODOS' (1 por 1, do menor pro maior)"
  echo "   3. A página recarrega sozinha a cada 5s"
  echo ""
  echo "💡 Dica: use 'bibliotecario' persona pra recomendações e mapeamento"
else
  echo "⚠️  Servidor não respondeu no health check. Veja os logs:"
  echo "  tail $LOG"
fi