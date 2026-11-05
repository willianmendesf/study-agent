#!/usr/bin/env python3
"""Confere se a lista de 58 da estante do William bate com o YAML canonico e o markdown.

Compara campo a campo: titulo, autor, detalhes — entre:
  - a lista em texto (data/perfil/bibliotecario/estante-william.txt)
  - o YAML     (data/perfil/bibliotecario/estante-william.yaml)
  - o markdown (data/biblioteca/literatura/estante-william-58-livros.md)

Uso: python3 scripts/conferir-estante-william.py
"""
import re
import sys
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TXT = ROOT / "data/perfil/bibliotecario/estante-william.txt"
YML = ROOT / "data/perfil/bibliotecario/estante-william.yaml"
MD = ROOT / "data/biblioteca/literatura/estante-william-58-livros.md"


def norm(s):
    """Normaliza para comparar: tira acento, apaga aspas, colapsa espacos."""
    s = unicodedata.normalize("NFKD", s or "")
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = s.replace("''", "'").replace("‘", "'").replace("’", "'")
    s = re.sub(r"[`*_\"'|]", "", s)
    s = re.sub(r"\s+", " ", s)
    s = s.strip().lower()
    # placeholders de "sem detalhes" sao equivalentes entre as tres fontes
    if s in ("", "—", "-", "--", "n/a", "n/a."):
        return ""
    return s


# --- texto ---
texto = {}
for linha in TXT.read_text(encoding="utf-8").splitlines():
    linha = linha.strip()
    if not linha:
        continue
    p = linha.split("|")
    if len(p) < 3:
        print(f"[TXT] linha malformada: {linha!r}")
        continue
    texto[int(p[0])] = (p[1].strip(), p[2].strip(),
                        p[3].strip() if len(p) > 3 else "")

# --- yaml ---
yml_txt = YML.read_text(encoding="utf-8")
yml = {}
for m in re.finditer(
        r"  - id: (\d+)\n    titulo: '((?:[^']|'')*)'\n    autor: '((?:[^']|'')*)'"
        r"(?:\n    detalhes: '((?:[^']|'')*)')?", yml_txt):
    i = int(m.group(1))
    yml[i] = (m.group(2).replace("''", "'"),
              m.group(3).replace("''", "'"),
              (m.group(4) or "").replace("''", "'"))

# --- markdown ---
md = {}
for m in re.finditer(r"^\| (\d+) \| (.+?) \| (.+?) \| (.+?) \| (.+?) \|$",
                     MD.read_text(encoding="utf-8"), re.M):
    md[int(m.group(1))] = (m.group(2).strip(), m.group(3).strip(),
                           m.group(4).strip(), m.group(5).strip())

print(f"contagens -> texto:{len(texto)} yaml:{len(yml)} markdown:{len(md)}")

problemas = []
for i in sorted(set(texto) | set(yml) | set(md)):
    if i not in texto:
        problemas.append(f"#{i}: ausente no TEXTO")
        continue
    if i not in yml:
        problemas.append(f"#{i}: ausente no YAML")
        continue
    if i not in md:
        problemas.append(f"#{i}: ausente no MARKDOWN")
        continue
    t, y, d = texto[i], yml[i], md[i]
    for campo, idx_t, idx_y, idx_d in (("titulo", 0, 0, 0),
                                       ("autor", 1, 1, 1),
                                       ("detalhes", 2, 2, 2)):
        if norm(t[idx_t]) != norm(y[idx_y]):
            problemas.append(f"#{i} {campo}: TXT='{t[idx_t]}' != YAML='{y[idx_y]}'")
        if norm(t[idx_t]) != norm(d[idx_d]):
            problemas.append(f"#{i} {campo}: TXT='{t[idx_t]}' != MD='{d[idx_d]}'")

if problemas:
    print(f"\n!! {len(problemas)} divergencia(s):")
    for p in problemas:
        print("  -", p)
    sys.exit(1)
print("\nOK: os 58 titulos conferem entre texto, YAML e markdown.")
