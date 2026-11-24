#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Verificador das fichas de leitura por-conto (rampa de ficcao).

Checa 4 coisas que o modelo do `literato` exige e que a IA erra:
  1. frontmatter YAML valido + campos obrigatorios (Regra 3)
  2. zero caracteres nao latinos (CJK / cirilico / hangul / grego) — o bug
     recorrente de 2026-11-05 (10 corrupcoes num unico write_file)
  3. as 13 secoes do modelo estao presentes, na ordem
  4. as citacoes do § 9 tem linha real e a frase existe no texto do acervo

Uso:
  python3 scripts/verificar-fichas-contos.py            # auditar
  python3 scripts/verificar-fichas-contos.py --verbose  # mostra detalhe
"""
from __future__ import annotations

import argparse
import os
import re
import sys
import unicodedata

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, ".claude", "scripts", "vendor"))
import yaml  # noqa: E402

SERIE = os.path.join(ROOT, "data", "estudos", "notas", "ficcao-rampa-leitura")
FONTE = os.path.join(ROOT, "data", "biblioteca", "literatura-mundial-classica",
                     "portugues", "Doyle-O-Ultimo-Adeus-de-Sherlock-Holmes.md")

SECOES = [
    "§ 1", "§ 2", "§ 3", "§ 4", "§ 5", "§ 6",
    "§ 7", "§ 8", "§ 9", "§ 10", "§ 11", "§ 12", "§ 13",
]

CAMPOS_FM = ["passagem", "livro", "capitulo", "tipo", "publico", "serie"]

# blocos nao latinos (nao-latin) — os que o gerador corrompe
BLOCOS = {"CJK": r"[぀-ヿ㐀-䶿一-鿿豈-﫿]",
          "CIRILICO": r"[Ѐ-ӿ]",
          "HANGUL": r"[가-힯ᄀ-ᇿ]",
          "GREGO": r"[Ͱ-Ͽ]"}


def nao_latinos(txt):
    achados = []
    for nome, pat in BLOCOS.items():
        for m in re.finditer(pat, txt):
            ctx = txt[max(0, m.start() - 25):m.end() + 25].replace("\n", " ")
            achados.append((nome, m.group(), ctx))
    return achados


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--verbose", action="store_true")
    a = ap.parse_args()

    with open(FONTE, encoding="utf-8") as f:
        fonte = f.read()
    fonte_norm = unicodedata.normalize("NFKC", fonte)

    fichas = sorted(
        p for p in os.listdir(SERIE)
        if re.match(r"^\d\d-ficha-conto-.*\.md$", p)
    )
    if not fichas:
        print("NENHUMA ficha de conto encontrada em", SERIE)
        return 1

    erros = 0
    for nome in fichas:
        caminho = os.path.join(SERIE, nome)
        txt = open(caminho, encoding="utf-8").read()
        probs = []

        # 1 · frontmatter
        m = re.match(r"^---\n(.*?)\n---\n", txt, re.S)
        if not m:
            probs.append("sem frontmatter YAML")
            fm = {}
        else:
            try:
                fm = yaml.safe_load(m.group(1)) or {}
            except Exception as e:
                probs.append(f"frontmatter YAML invalido: {e}")
                fm = {}
            if not isinstance(fm, dict):
                probs.append("frontmatter nao e um mapa")
                fm = {}
            for c in CAMPOS_FM:
                if not fm.get(c):
                    probs.append(f"frontmatter sem campo obrigatorio: {c}")
            for c in ("conta_linhas", "conta_pos_rampa", "conta_rampa", "conta_palavras"):
                if c not in fm:
                    probs.append(f"frontmatter sem campo de rastreio: {c}")

        # 2 · caracteres nao latinos
        nl = nao_latinos(txt)
        if nl:
            for nome_b, ch, ctx in nl[:6]:
                probs.append(f"caractere {nome_b} {ch!r} em: ...{ctx}...")
            if len(nl) > 6:
                probs.append(f"... e mais {len(nl) - 6} ocorrencias nao-latinas")

        # 3 · secoes do modelo, em ordem
        pos = []
        for s in SECOES:
            i = txt.find(s)
            if i < 0:
                probs.append(f"faltando a secao {s}")
            pos.append(i)
        if all(i >= 0 for i in pos) and pos != sorted(pos):
            probs.append("secoes fora de ordem")

        # 4 · citacoes do § 9: linha real + frase no acervo
        sec9 = txt.split("§ 9")[1].split("§ 10")[0] if "§ 9" in txt and "§ 10" in txt else ""
        linhas_cit = re.findall(r"\|\s*(\d{3,5})\s*\|", sec9)
        if not linhas_cit:
            probs.append("§ 9 sem tabela de citacoes com linha")
        for ln in linhas_cit:
            n = int(ln)
            if n < 1 or n > len(fonte.split("\n")):
                probs.append(f"§ 9 cita linha {n} fora do acervo")
        # frases entre aspas na § 9 -> conferir no acervo
        frases = re.findall(r'"([^"]{12,120})"', sec9)
        for f_ in frases:
            alvo = unicodedata.normalize("NFKC", f_)
            if alvo not in fonte_norm:
                probs.append(f"citacao NAO CONFIRMADA no acervo: {f_[:60]!r}")

        status = "OK " if not probs else "ERR"
        if probs:
            erros += 1
        print(f"[{status}] {nome}")
        for p in probs:
            print(f"        - {p}")
        if a.verbose and not probs:
            print(f"        {len(linhas_cit)} citacoes · {len(frases)} frases verificadas")

    print(f"\n{len(fichas) - erros}/{len(fichas)} fichas OK")
    return 1 if erros else 0


if __name__ == "__main__":
    raise SystemExit(main())