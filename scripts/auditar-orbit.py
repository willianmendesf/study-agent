#!/usr/bin/env python3
"""AUDITORIA: quais livros das KBs do acervo NAO existem no BookOrbit.

POR QUE EXISTE (2026-11-25)
  Queixa do William: "voce esta toda hora referenciando livros que nao existem
  pra mim no bookorbit, ex: Aconselhamento Biblico vol. 8".
  O acervo local (data/biblioteca/**/*.md + KBs) e' MUITO maior que o app.
  O `pipeline-estado.json` so rastreia o que o PIPELINE baixou; os livros que
  entraram por semente/catalogo manual nunca foram conferidos contra o app.

COMO CASA (3 regras, testadas contra os casos reais)
  1. NUMERO SO CONTA COMO VOLUME quando vem depois de vol/volume/livro/parte.
     "02-Teologia-Puritana..." NAO e' volume 2 — e' prefixo de arquivo.
     Sem isso o auditor dava falso negativo em todo .md numerado.
  2. Volume diferente = livro diferente. "Coletaneas Vol VIII" NAO casa com
     Vol VI (era exatamente o erro que o William apontou).
  3. Casamento por contencao: >=80% das palavras da KB no titulo do app, ou
     todas as palavras do titulo do app dentro do titulo da KB (>=2 palavras).

USO
  python3 scripts/auditar-orbit.py --catalogo /tmp/orbit-catalogo.json
  python3 scripts/auditar-orbit.py --validar      # roda os casos de controle
"""
import argparse
import json
import re
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
KB_DIR = ROOT / "data" / "biblioteca" / "global"
SAIDA = ROOT / "data" / "perfil" / "bibliotecario" / "auditoria-orbit.json"

ROMANOS = {"i": "1", "ii": "2", "iii": "3", "iv": "4", "v": "5", "vi": "6",
           "vii": "7", "viii": "8", "ix": "9", "x": "10", "xi": "11", "xii": "12"}
MARCA_VOL = re.compile(r"\b(vol|volume|livro|parte|n[ºo]|tomo)\s*\.?\s*"
                       r"(\d{1,2}|[ivx]{1,5})\b", re.I)
STOP = {"para", "como", "pela", "pelo", "sobre", "entre", "dos", "das", "com"}


def norm(s):
    s = unicodedata.normalize("NFKD", s or "")
    s = "".join(c for c in s if not unicodedata.combining(c)).lower()
    return re.sub(r"[^a-z0-9 ]", " ", s)


def volumes(titulo_bruto):
    """Numeros que designam VOLUME (e so eles)."""
    out = []
    for m in MARCA_VOL.finditer(titulo_bruto or ""):
        v = m.group(2).lower()
        out.append(ROMANOS.get(v, v))
    return out


def palavras(titulo, minimo=3):
    return [x for x in norm(titulo).split()
            if len(x) > minimo and not x.isdigit() and x not in STOP]


def _stem(p, n=5):
    return p[:n]


def casa(titulo, orbit):
    """orbit = lista de (id, titulo_normalizado, set_palavras, vols).

    Tres regras, cada uma nascida de um caso REAL medido:
      A) Volume declarado na KB tem de bater. O app traz numero de SERIE
         ("Série Aconselhamento Livro 16") que nao existe na KB — entao a
         trava so vale quando a KB declara volume. Volume diferente NUNCA
         casa (Coletaneas Vol VIII x Vol VI = o erro que o William apontou).
      B) Direcao KB -> app: >=80% das palavras da KB aparecem no titulo do app.
         (titulo curto no app, longo na KB)
      C) Direcao app -> KB: TODAS as palavras do titulo do app (>=2) aparecem
         na KB. (titulo curto na KB, com subtitulo longo no app)
    Comparacao por PREFIXO de 5 letras: "familia" casa com "familias",
    "biblico" com "biblica" — igualdade exata perdia plural e genero.
    """
    pw = palavras(titulo)
    vv = volumes(titulo)
    if not pw and not vv:
        return True, None
    spw = {_stem(x) for x in pw}
    for bid, ot, otoks, ovols in orbit:
        if vv and sorted(vv) != sorted(ovols):
            continue
        if not pw:
            return True, bid
        opal = [x for x in ot.split()
                if len(x) > 3 and not x.isdigit() and x not in STOP]
        sopal = {_stem(x) for x in opal}
        cas = sum(1 for x in spw if x in sopal)
        if cas >= 0.8 * len(spw):          # regra B
            return True, bid
        if len(opal) >= 2 and all(x in spw for x in sopal):   # regra C
            return True, bid
    return False, None


def montar_orbit(catalogo):
    orbit = []
    for bid, v in catalogo.items():
        t = v.get("t") or ""
        if not t:
            continue
        orbit.append((int(bid), norm(t), set(norm(t).split()), volumes(t)))
    return orbit


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--catalogo", default="/tmp/orbit-catalogo.json")
    ap.add_argument("--kb", default="")
    ap.add_argument("--validar", action="store_true")
    args = ap.parse_args()

    cat = json.loads(Path(args.catalogo).read_text(encoding="utf-8"))
    orbit = montar_orbit(cat)

    if args.validar:
        casos = [
            ("Coletâneas Vol VIII", False),      # NAO existe (queixa do William)
            ("Coletâneas Vol VI", True),         # existe: id 130
            ("Coletâneas de Aconselhamento Bíblico Vol II", True),
            ("Enfrentando a Morte com Esperança", True),
            ("Sofrendo com a Perda de um Filho", True),
            ("O Pastor e o Aconselhamento — Um guia básico", True),
            ("02-Teologia-Puritana-Doutrina-Vida", True),
            ("Aconselhamento a partir da cruz: conectando pessoas ao poder curador do amor de Cristo", True),
            ("Teologia Sistemática", True),
            ("Manual Bíblico do Jejum", True),
        ]
        falhas = 0
        for t, esperado in casos:
            ok, bid = casa(t, orbit)
            marca = "OK " if ok == esperado else "ERRO"
            if ok != esperado:
                falhas += 1
            print(f"{marca} esperado={'existe' if esperado else 'falta':6s} "
                  f"obtido={'existe' if ok else 'falta':6s} id={bid} :: {t[:60]}")
        print(f"\n{len(casos)-falhas}/{len(casos)} casos de controle OK")
        return 0 if falhas == 0 else 1

    kbs = sorted(KB_DIR.glob("kb-*.yaml"))
    if args.kb:
        kbs = [p for p in kbs if args.kb in p.name]
    rel = {}
    for p in kbs:
        txt = p.read_text(encoding="utf-8", errors="ignore")
        titulos = re.findall(r"^\s*- titulo:\s*'?\"?([^'\"\n]+)'?\"?\s*$", txt, re.M)
        faltam = [t for t in titulos if not casa(t, orbit)[0]]
        rel[p.stem] = {"total": len(titulos), "faltam": faltam}
        print(f"{p.stem:34s} {len(titulos):4d} titulos  {len(faltam):4d} FORA do BookOrbit")

    SAIDA.write_text(json.dumps(rel, ensure_ascii=False, indent=1), encoding="utf-8")
    tot = sum(v["total"] for v in rel.values())
    falta = sum(len(v["faltam"]) for v in rel.values())
    print(f"\nTOTAL: {tot} titulos nas KBs · {falta} sem correspondencia no BookOrbit")
    print(f"relatorio: {SAIDA.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
