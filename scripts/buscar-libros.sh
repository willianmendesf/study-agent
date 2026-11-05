#!/bin/sh
# Wrapper temporário para rodar o buscar.py do índice de livros
exec python3 "$(dirname "$0")/../skills/study-busca-livros/buscar.py" "$@"
