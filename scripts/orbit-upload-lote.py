#!/usr/bin/env python3
"""Upload em LOTE para o BookOrbit: 1 login para a fila inteira.

POR QUE EXISTE
  O `orbit-upload.py` faz login por arquivo (um subprocess por ebook). O
  throttler do BookOrbit devolve 429 a partir do 4o arquivo e a fila inteira
  falha. Este script reusa as funcoes do `orbit-upload.py` via importlib:
  UM login, uploads sequenciais com pausa, backoff em 429/401.

NOME DO ARQUIVO = "Autor - Titulo.ext"
  O BookOrbit deriva titulo e autor do NOME do arquivo enviado. Mandar so o
  autor faz todos os PDFs virarem `_unorganized.pdf` (409 no 2o).

USO
  python3 scripts/orbit-upload-lote.py --dir /tmp/oracao-dl
  python3 scripts/orbit-upload-lote.py --dir ... --dry
"""
import argparse
import importlib.util
import json
import sys
import time
import unicodedata
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OU_PATH = ROOT / "scripts" / "orbit-upload.py"


def carregar():
    spec = importlib.util.spec_from_file_location("orbit_upload", OU_PATH)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def slug(t):
    s = "".join(c for c in unicodedata.normalize("NFKD", t) if not unicodedata.combining(c))
    s = re.sub(r"[^\w\s.-]", "", s)
    s = re.sub(r"[\s_]+", " ", s).strip()
    return s[:120]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", required=True)
    ap.add_argument("--dry", action="store_true")
    ap.add_argument("--pausa", type=float, default=1.2)
    args = ap.parse_args()

    ou = carregar()
    pasta = Path(args.dir)
    arquivos = sorted([p for p in pasta.iterdir()
                       if p.suffix.lower() in (".epub", ".pdf", ".mobi", ".azw3")])
    if not arquivos:
        print("nada a enviar")
        return 0

    if args.dry:
        for p in arquivos:
            print(f"[dry] {p.name}")
        return 0

    token, user = ou.login()
    print(f"login OK: {user.get('username')} (id {user.get('id')}) — {len(arquivos)} arquivo(s)")

    ok = falhou = 0
    for p in arquivos:
        nome = p.stem  # ja vem no formato "Autor - Titulo"
        st, d = ou.upload(p, token, folder_id=1, autor=nome)
        if st == 401:
            print(f"[sessao] token expirou; renovando...")
            token, _ = ou.login()
            st, d = ou.upload(p, token, folder_id=1, autor=nome)
        if st == 429:
            for espera in (15, 30, 60):
                print(f"[429] {p.name}: aguardando {espera}s")
                time.sleep(espera)
                st, d = ou.upload(p, token, folder_id=1, autor=nome)
                if st != 429:
                    break
        if st in (200, 201):
            ok += 1
            print(f"[OK] {p.name} -> bookId {d.get('bookId')}")
            try:
                p.unlink()
            except OSError:
                pass
        elif st == 409:
            # duplicata real: ja existe no Orbit com esse nome
            falhou += 1
            print(f"[409-DUP] {p.name}: {str(d.get('message'))[:90]}")
        else:
            falhou += 1
            print(f"[FALHOU {st}] {p.name}: {str(d)[:140]}")
        time.sleep(args.pausa)

    print(f"\nenviados={ok} falhas={falhou} de {len(arquivos)}")
    return 0 if falhou == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
