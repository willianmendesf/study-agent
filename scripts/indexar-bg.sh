#!/bin/sh
# Indexa a biblioteca em segundo plano e grava log em /tmp/indexar.log
cd "$(dirname "$0")/../skills/study-busca-livros" || exit 1
nohup python3 indexar.py > /tmp/indexar.log 2>&1 &
echo "PID $!"
