#!/usr/bin/env python3
"""Restaura as marcacoes de codigo (backticks) na tabela 'Documentos desta estante'.

O patch anterior passou pelo shell, que interpreitou as backticks como comando.
Uso: python3 scripts/tmp_corrigir_backticks_estante.py
"""
from pathlib import Path

P = Path("/home/willian/study-agent/data/biblioteca/literatura/estante-william-58-livros.md")

LINHAS = {
    "|  | o plano da rampa de leitura (5 degraus) |":
        "| `data/estudos/notas/ficcao-rampa-leitura/01-rampa-de-leitura.md` | o plano da rampa de leitura (5 degraus) |",
    "|  | cruzamento inicial da lista com o acervo (02:00) |":
        "| `data/estudos/notas/ficcao-rampa-leitura/02-cruzamento-lista-de-casa.md` | cruzamento inicial da lista com o acervo (02:00) |",
    "|  | **cruzamento ATUALIZADO** (pós-lote de 30 traduções PT-BR) — este é o vigente |":
        "| `data/estudos/notas/ficcao-rampa-leitura/03-cruzamento-pos-lote.md` | **cruzamento ATUALIZADO** (pós-lote de 30 traduções PT-BR) — este é o vigente |",
    "|  | dados estruturados (58 itens, com eixo e caminho no acervo) |":
        "| `data/perfil/bibliotecario/estante-william.yaml` | dados estruturados (58 itens, com eixo e caminho no acervo) |",
}

t = P.read_text(encoding="utf-8")
for velho, novo in LINHAS.items():
    if velho in t:
        t = t.replace(velho, novo)
        print(f"[ok] corrigido: {novo[:60]}")
    else:
        print(f"[aviso] nao achei: {velho[:60]}")
P.write_text(t, encoding="utf-8")
