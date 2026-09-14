#!/usr/bin/env bash
# setup.sh — instala as dependências do study-rag-local (chromadb + sentence-transformers).
# Uso: bash .claude/skills/study-rag-local/setup.sh
set -euo pipefail

echo "1) Verificando python3..."
command -v python3 >/dev/null 2>&1 || { echo "python3 não encontrado."; exit 1; }
echo "   OK: $(python3 --version)"

SKILL_DIR="$(cd "$(dirname "$0")" && pwd)"
REQ="$SKILL_DIR/requirements.txt"

echo "2) Verificando dependências (chromadb, sentence-transformers)..."
if python3 -c "import chromadb, sentence_transformers" >/dev/null 2>&1; then
  echo "   já instaladas."
  exit 0
fi

echo "3) Instalando via pip --user (ambientes 'externally managed' usam --break-system-packages)..."
if pip install --user -r "$REQ" >/tmp/study-rag-setup.log 2>&1; then
  echo "   OK"
else
  echo "   pip padrão falhou (ambiente 'externally managed'?), tentando --break-system-packages..."
  pip install --user --break-system-packages -r "$REQ" >>/tmp/study-rag-setup.log 2>&1 \
    || { echo "   Falhou. Veja /tmp/study-rag-setup.log. Alternativa: crie um venv"; exit 1; }
  echo "   OK"
fi

python3 -c "import chromadb, sentence_transformers; print('   chromadb', chromadb.__version__, '| sentence-transformers', sentence_transformers.__version__)"
echo "✅ study-rag-local pronto. Use index.py pra indexar e search.py pra buscar."
