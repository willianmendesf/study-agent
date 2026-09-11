#!/bin/bash
# setup.sh — Configura OAuth do Google Drive + dependências
# Uso: bash .claude/skills/book-pipeline/setup.sh
set -e

SKILL_DIR="$(cd "$(dirname "$0")" && pwd)"
CONFIG_DIR="$HOME/.config/gdrive-mcp"
OAUTH_CLIENT_FILE="$CONFIG_DIR/gcp-oauth.keys.json"
OAUTH_TOKEN_FILE="$CONFIG_DIR/gdrive-credentials.json"

echo "=========================================="
echo "🔧 Setup do book-pipeline"
echo "=========================================="
echo ""

# 1. Verificar dependências do sistema
echo "1️⃣  Verificando dependências..."
MISSING=""
for cmd in python3 curl lsof uvx; do
  if ! command -v "$cmd" >/dev/null 2>&1; then
    MISSING="$MISSING $cmd"
  fi
done
if [ -n "$MISSING" ]; then
  echo "   ⚠️  Faltando:$MISSING"
  echo "   Instale com: sudo apt install python3 curl lsof"
  echo "   uvx instala via: pip install uv (ou pipx install uv)"
else
  echo "   ✅ Dependências OK"
fi
echo ""

# 2. Verificar/Instalar uvx
if ! command -v uvx >/dev/null 2>&1; then
  echo "2️⃣  Instalando uvx (gerenciador de pacotes Python)..."
  pip install --user uv || pip3 install --user uv
  export PATH="$HOME/.local/bin:$PATH"
fi
echo "   ✅ uvx OK"
echo ""

# 3. Verificar credenciais OAuth do Google Drive
echo "3️⃣  Verificando credenciais OAuth do Google Drive..."
mkdir -p "$CONFIG_DIR"

if [ -f "$OAUTH_CLIENT_FILE" ] && [ -f "$OAUTH_TOKEN_FILE" ]; then
  echo "   ✅ Credenciais já configuradas em $CONFIG_DIR"
  echo "   Se precisar reconfigurar, delete os arquivos e rode setup.sh de novo"
else
  echo "   ⚠️  Credenciais NÃO encontradas"
  echo ""
  echo "   Para configurar OAuth do Google Drive:"
  echo ""
  echo "   a) Acesse https://console.cloud.google.com/"
  echo "   b) Crie/selecione um projeto (ex: study-agent-drive)"
  echo "   c) Ative a API 'Google Drive API'"
  echo "   d) Crie credenciais OAuth 2.0 (tipo: Desktop app OU Web application)"
  echo "      - Se Web: adicione http://localhost:3000/oauth2callback em 'Authorized redirect URIs'"
  echo "   e) Baixe o JSON das credenciais"
  echo "   f) Salve o JSON como: $OAUTH_CLIENT_FILE"
  echo "      (renomeie 'client_secret_*.json' para 'gcp-oauth.keys.json' se necessário)"
  echo ""
  read -p "   Já tem o arquivo de credenciais salvo? (s/n) " RESP
  if [ "$RESP" = "s" ] || [ "$RESP" = "S" ]; then
    echo "   OK — re-rode o setup.sh e o servidor vai detectar automaticamente"
  else
    echo "   Configure primeiro e depois rode: bash $0"
    exit 1
  fi
fi
echo ""

# 4. Tornar scripts executáveis
echo "4️⃣  Tornando scripts executáveis..."
chmod +x "$SKILL_DIR"/*.py "$SKILL_DIR"/*.sh 2>/dev/null || true
echo "   ✅ Permissões OK"
echo ""

# 5. Criar diretório de logs
echo "5️⃣  Criando diretórios de log/state..."
mkdir -p /tmp
echo "   ✅ /tmp pronto"
echo ""

echo "=========================================="
echo "✅ Setup completo!"
echo "=========================================="
echo ""
echo "Próximos passos:"
echo "  1. bash $SKILL_DIR/start.sh   # sobe o servidor"
echo "  2. Acesse http://localhost:8765 no navegador"
echo "  3. Clique 'TRAZER TODOS' para processar"
echo ""
echo "Se credenciais OAuth não estiverem prontas:"
echo "  1. Configure no Google Cloud Console"
echo "  2. Salve o JSON em $OAUTH_CLIENT_FILE"
echo "  3. Acesse http://localhost:8765 no navegador (vai abrir OAuth automaticamente)"