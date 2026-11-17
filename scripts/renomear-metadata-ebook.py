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
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path


def _escapar(s: str) -> str:
    return (s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))


def _trocar_tag(txt: str, tag: str, valor: str) -> str:
    """Troca o CONTEUDO de <dc:tag ...>...</dc:tag> PRESERVANDO os atributos.

    BUG CORRIGIDO 2026-11-17 (livro do Leeman nao abria no BookOrbit):
    a versao anterior reescrevia `<dc:title xmlns:dc="...">X</dc:title>` como
    `<dc:title>Y</dc:title>` e DESCARTAVA a declaracao de namespace que estava
    no proprio elemento. Como o `<package>` daquele EPUB nao declara xmlns:dc,
    o XML ficava invalido -> "Namespace prefix dc on title is not defined".
    """
    pat = re.compile(rf"(<{tag}\b[^>]*>)(.*?)(</{tag}>)", re.S)
    if pat.search(txt):
        # tag LIMPA, sem atributos. O BookOrbit so reconhece `<dc:creator>` puro:
        # quando o atributo (id="creator01", xmlns:dc=...) fica no elemento, o
        # livro sobe com authors=[] e cai em /books/Unknown Author/.
        # A declaracao xmlns:dc vai para o <package> (ver _garantir_ns_dc), o
        # que mantem o XML valido sem precisar do atributo no elemento.
        return pat.sub(lambda m: f"<{tag}>{_escapar(valor)}</{tag}>", txt, count=1)
    return txt.replace("</metadata>", f"<{tag}>{_escapar(valor)}</{tag}></metadata>", 1)


def _garantir_ns_dc(txt: str) -> str:
    """Garante xmlns:dc declarado no <package> (raiz do OPF)."""
    m = re.search(r"<package\b[^>]*>", txt)
    if not m:
        return txt
    raiz = m.group(0)
    if "xmlns:dc" in raiz:
        return txt
    nova = raiz[:-1].rstrip() + ' xmlns:dc="http://purl.org/dc/elements/1.1/">'
    return txt[: m.start()] + nova + txt[m.end():]


def epub_metadados(src: Path, titulo: str, autor: str, out: Path) -> Path:
    tmp = out.with_suffix(".tmp.epub")
    with zipfile.ZipFile(src) as zin, zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as zout:
        for item in zin.infolist():
            dados = zin.read(item.filename)
            if item.filename.lower().endswith(".opf"):
                txt = dados.decode("utf-8", "ignore")
                txt = _garantir_ns_dc(txt)
                txt = _trocar_tag(txt, "dc:title", titulo)
                txt = _trocar_tag(txt, "dc:creator", autor)
                # validacao: OPF tem de continuar sendo XML bem formado
                try:
                    ET.fromstring(txt.encode("utf-8"))
                except ET.ParseError as e:
                    raise SystemExit(f"ERRO: OPF invalido apos reescrita: {e}")
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
