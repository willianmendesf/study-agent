#!/usr/bin/env python3
"""Mapeia a estrutura real de uma colecao de contos no acervo.

Para cada conto: titulo, linha inicial, linha final, nº de palavras, nº de
frases, palavras/frase, e um trecho de abertura (para ancorar).

Uso: python3 scripts/mapa-contos.py <arquivo.md> <titulo1> <titulo2> ...
"""
import json
import re
import sys
from pathlib import Path


def _tokens(s: str) -> list[str]:
    return re.findall(r"[A-Za-zÀ-ÿ]+", s.lower())


def main() -> int:
    if len(sys.argv) < 3:
        print(__doc__)
        return 1
    arq = Path(sys.argv[1])
    titulos = sys.argv[2:]
    linhas = arq.read_text(encoding="utf-8", errors="replace").splitlines()
    # Remove cabecalhos de secao vazios
    idx = []
    for t in titulos:
        achado = None
        for i, ln in enumerate(linhas):
            s = ln.strip()
            if not s:
                continue
            # titulo do conto: linha curta, sem pontuacao final, ou cabecalho em caixa
            if s.lower() == t.lower() or s.lower().replace(" ", "") == t.lower().replace(" ", ""):
                achado = i
                break
        idx.append((t, achado))
    out = []
    for k, (t, ini) in enumerate(idx):
        if ini is None:
            out.append({"titulo": t, "erro": "titulo nao encontrado"})
            continue
        fim = idx[k + 1][1] if k + 1 < len(idx) and idx[k + 1][1] else len(linhas)
        corpo = "\n".join(linhas[ini + 1:fim])
        toks = _tokens(corpo)
        frases = [f for f in re.split(r"[.!?…]+\s+", " ".join(corpo.split())) if f.strip()]
        out.append({
            "titulo": t,
            "linha_ini": ini + 1,
            "linha_fim": fim,
            "palavras": len(toks),
            "frases": len(frases),
            "p_frase": round(len(toks) / max(len(frases), 1), 1),
            "abertura": " ".join(corpo.split())[:220],
        })
    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
