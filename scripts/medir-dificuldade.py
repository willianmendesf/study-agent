#!/usr/bin/env python3
"""Mede a dificuldade linguistica de uma obra, com o MESMO metodo da nota 10.

Metodo (10-dificuldade-medida-acervo.md):
  1. Extracao de prosa: remove frontmatter, titulos, linhas curtas (aparelho
     critico) e linhas com densidade de notas. Fica so o corpo do texto.
  2. Medidas: palavras/frase, % palavras 4+ silabas, % palavras 11+ caracteres,
     % palavras raras (<=5 ocorrencias no corpus de referencia do acervo),
     % hapax (aparecem uma vez so no livro).
  3. score = 0.35*sintaxe + 0.40*raridade*2.2 + 0.25*tamanho   (0-20, menor = mais facil)
     sintaxe   = 0.45*p/frase + 0.35*silabas4*1.2 + 0.20*long11*1.5
     tamanho  = palavras/100000*8

Uso:
  python3 scripts/medir-dificuldade.py <arquivo.md> [<corpus-ref-dir>]
Sem 2o argumento, usa data/biblioteca/ como corpus de referencia (lento).
"""
import re
import sys
import unicodedata
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _extrair_prosa(texto: str) -> str:
    """Fica so o corpo da prosa: tira frontmatter, titulos, aparato critico."""
    linhas = []
    if texto.startswith("---"):
        partes = texto.split("---", 2)
        if len(partes) == 3:
            texto = partes[2]
    for ln in texto.splitlines():
        s = ln.strip()
        if not s:
            continue
        if s.startswith("#"):
            continue
        if len(s) < 120:
            continue  # aparelho critico / cabecalhos / verso
        if s.count("|") >= 2:
            continue  # tabela
        linhas.append(s)
    return " ".join(linhas)


def _tokens(prosa: str) -> list[str]:
    return re.findall(r"[A-Za-zÀ-ÿ]+", prosa.lower())


def _silabas(pal: str) -> int:
    p = unicodedata.normalize("NFD", pal)
    p = "".join(c for c in p if unicodedata.category(c) != "Mn")
    vogais = "aeiouy"
    n, anterior_vogal = 0, False
    for c in p:
        eh_vogal = c in vogais
        if eh_vogal and not anterior_vogal:
            n += 1
        anterior_vogal = eh_vogal
    if p.endswith("e") and n > 1:
        n -= 1
    return max(n, 1)


def _frases(prosa: str) -> list[str]:
    return [f for f in re.split(r"[.!?…]+\s+", prosa) if f.strip()]


def medir(arquivo: Path, ref: Counter | None = None) -> dict:
    texto = arquivo.read_text(encoding="utf-8", errors="replace")
    prosa = _extrair_prosa(texto)
    toks = _tokens(prosa)
    n = len(toks)
    frases = _frases(prosa)
    pf = n / max(len(frases), 1)
    cnt = Counter(toks)
    sil4 = sum(1 for t in toks if _silabas(t) >= 4) / max(n, 1)
    long11 = sum(1 for t in toks if len(t) >= 11) / max(n, 1)
    if ref is None:
        raras = 0.0
        hapax = 0.0
    else:
        raras = sum(1 for t in toks if ref.get(t, 0) <= 5) / max(n, 1)
        hapax = sum(1 for t in toks if cnt.get(t, 0) == 1) / max(n, 1)
    sintaxe = 0.45 * pf + 0.35 * sil4 * 1.2 + 0.20 * long11 * 1.5
    tamanho = (n / 100000) * 8
    score = 0.35 * sintaxe + 0.40 * raras * 2.2 + 0.25 * tamanho
    return {
        "arquivo": str(arquivo.relative_to(ROOT)) if ROOT in arquivo.parents else str(arquivo),
        "palavras": n,
        "frases": len(frases),
        "p_frase": round(pf, 1),
        "sil4_pct": round(sil4 * 100, 1),
        "long11_pct": round(long11 * 100, 1),
        "rara_pct": round(raras * 100, 1),
        "hapax_pct": round(hapax * 100, 1),
        "score": round(score, 2),
        "paginas_estimadas": round(n / 235),
    }


def corpus_ref(diretorio: Path) -> Counter:
    cnt: Counter = Counter()
    for p in diretorio.rglob("*.md"):
        try:
            txt = p.read_text(encoding="utf-8", errors="replace")
        except Exception:
            continue
        cnt.update(_tokens(txt.lower()))
    return cnt


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    alvo = Path(sys.argv[1])
    ref = None
    if len(sys.argv) > 2:
        ref = corpus_ref(Path(sys.argv[2]))
    else:
        ref = corpus_ref(ROOT / "data" / "biblioteca")
    import json
    print(json.dumps(medir(alvo, ref), ensure_ascii=False, indent=2))
