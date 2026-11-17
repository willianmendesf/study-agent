#!/usr/bin/env python3
"""Sobe UM ebook para o BookOrbit com TITULO e AUTOR corretos no nome.

POR QUE EXISTE (2026-11-17 — regra do William)
  "os arquivos baixados precisam ser renomeado e ter o nome do livro."
  O BookOrbit monta o nome do livro pelo METADADO INTERNO do arquivo
  (precedencia `embedded`), nao pelo nome do multipart. Um download do
  z-library traz `dc:title` comprido ("Didaque: O catecismo dos primeiros
  cristaos para as comunidades de hoje") e `dc:creator` = editora ("Paulus"),
  e o livro aparece assim no app, em /books/Paulus/.

O QUE FAZ
  1. Reescreve o metadado interno (EPUB -> content.opf; PDF -> /Title /Author).
  2. Sobe pelo caminho de LOTE (1 login, sem 429).
  3. Imprime o bookId e confere o resultado na API.

USO
  python3 scripts/orbit-subir-livro.py arquivo.epub "Didaque" "Padres Apostolicos"
  python3 scripts/orbit-subir-livro.py arquivo.epub "Didaque" --sem-autor
"""
import argparse
import importlib.util
import json
import shutil
import subprocess
import sys
import tempfile
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
META = ROOT / "scripts" / "renomear-metadata-ebook.py"
LOTE = ROOT / "scripts" / "orbit-upload-lote.py"
OU = ROOT / "scripts" / "orbit-upload.py"


def _ou():
    spec = importlib.util.spec_from_file_location("orbit_upload", OU)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("arquivo")
    ap.add_argument("titulo")
    ap.add_argument("autor", nargs="?", default="")
    ap.add_argument("--sem-autor", action="store_true",
                    help="grava 'Desconhecido' como autor em vez de vazio")
    a = ap.parse_args()

    src = Path(a.arquivo)
    if not src.exists():
        print(f"ERRO: {src} nao existe")
        return 2
    autor = "Desconhecido" if a.sem_autor else a.autor
    nome = a.titulo if not autor else f"{autor} - {a.titulo}"

    tmp = Path(tempfile.mkdtemp(prefix="orbit-"))
    destino = tmp / f"{nome}{src.suffix.lower()}"
    r = subprocess.run([sys.executable, str(META), str(src), a.titulo, autor,
                        "-o", str(destino)], capture_output=True, text=True)
    if r.returncode != 0:
        print(f"ERRO ao reescrever metadados: {r.stderr[-300:]}")
        return 2
    print(r.stdout.strip())

    r = subprocess.run([sys.executable, str(LOTE), "--dir", str(tmp)],
                       capture_output=True, text=True)
    print(r.stdout.strip())
    if r.returncode != 0:
        print(r.stderr[-300:])

    # confere o resultado na API (titulo/autor/pasta)
    try:
        m = _ou()
        tok, _ = m.login()
        req = urllib.request.Request(
            f"{m.ORBIT_URL}/api/v1/books/search?q={urllib.parse.quote(a.titulo)}",
            method="GET")
        req.add_header("Authorization", f"Bearer {tok}")
        with urllib.request.urlopen(req, timeout=30) as resp:
            itens = json.loads(resp.read())
        for it in itens[:3]:
            print(f"  Orbit: {it['id']} | {it['title']} | {it['authors']}")
    except Exception as e:
        print(f"  (nao consegui conferir na API: {e})")

    shutil.rmtree(tmp, ignore_errors=True)
    return r.returncode


if __name__ == "__main__":
    sys.exit(main())
