#!/usr/bin/env python3
"""Reescreve os metadados internos de um EPUB/PDF (titulo + autor).

POR QUE EXISTE (2026-11-17, pedido do William)
  O BookOrbit nomeia o livro pelo METADADO INTERNO do arquivo (precedencia
  `embedded`), nao pelo nome do arquivo enviado. Por isso um download do
  z-library com `dc:title` longo e `dc:creator` = editora aparece no app como
  "Didaque: O catecismo ..." na pasta "/books/Paulus/".
  Regra do William: o arquivo baixado tem de ser renomeado e ter o NOME DO
  LIVRO.

USO
  python3 scripts/renomear-metadata-ebook.py entrada.epub "Didaque" "Padres Apostolicos" -o saida.epub
  python3 scripts/renomear-metadata-ebook.py livro.pdf "Titulo" "Autor" -o saida.pdf
"""
import argparse
import re
import shutil
import sys
import zipfile
from pathlib import Path


def epub_metadados(src: Path, titulo: str, autor: str, out: Path) -> Path:
    tmp = out.with_suffix(".tmp.epub")
    with zipfile.ZipFile(src) as zin, zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as zout:
        for item in zin.infolist():
            dados = zin.read(item.filename)
            if item.filename.lower().endswith(".opf"):
                txt = dados.decode("utf-8", "ignore")
                if re.search(r"<dc:title[^>]*>.*?</dc:title>", txt, re.S):
                    txt = re.sub(r"<dc:title[^>]*>.*?</dc:title>",
                                 f"<dc:title>{titulo}</dc:title>", txt, count=1, flags=re.S)
                else:
                    txt = txt.replace("</metadata>",
                                      f"<dc:title>{titulo}</dc:title></metadata>", 1)
                if re.search(r"<dc:creator[^>]*>.*?</dc:creator>", txt, re.S):
                    txt = re.sub(r"<dc:creator[^>]*>.*?</dc:creator>",
                                 f"<dc:creator>{autor}</dc:creator>", txt, count=1, flags=re.S)
                else:
                    txt = txt.replace("</metadata>",
                                      f"<dc:creator>{autor}</dc:creator></metadata>", 1)
                dados = txt.encode("utf-8")
            zout.writestr(item, dados)
    shutil.move(str(tmp), str(out))
    return out


def pdf_metadados(src: Path, titulo: str, autor: str, out: Path) -> Path:
    from pypdf import PdfReader, PdfWriter
    r = PdfReader(str(src))
    w = PdfWriter()
    for p in r.pages:
        w.add_page(p)
    w.add_metadata({"/Title": titulo, "/Author": autor})
    with open(out, "wb") as f:
        w.write(f)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("origem")
    ap.add_argument("titulo")
    ap.add_argument("autor", nargs="?", default="")
    ap.add_argument("-o", "--saida", required=True)
    a = ap.parse_args()

    src = Path(a.origem)
    out = Path(a.saida)
    out.parent.mkdir(parents=True, exist_ok=True)
    if src.suffix.lower() == ".epub":
        epub_metadados(src, a.titulo, a.autor, out)
    elif src.suffix.lower() == ".pdf":
        pdf_metadados(src, a.titulo, a.autor, out)
    else:
        print(f"extensao nao suportada: {src.suffix}")
        return 2
    print(f"[ok] {out} — titulo='{a.titulo}' autor='{a.autor}' "
          f"({out.stat().st_size//1024} KB)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
