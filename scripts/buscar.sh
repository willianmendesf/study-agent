#!/bin/sh
# Busca no índice de livros (wrapper). Uso: sh scripts/buscar.sh "termos" [opções]
cd "$(dirname "$0")/../skills/study-busca-livros" || exit 1
exec python3 buscar.py "$@"
