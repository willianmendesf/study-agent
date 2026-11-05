#!/usr/bin/env python3
"""Reenvia ao BookOrbit os ebooks que ficaram parados em `_incoming/`.

CONTEXTO (2026-11-05): o lote de rampa de ficção (01:52-01:59) baixou 30
ebooks, converteu e catalogou os `.md` — mas o **push ao Orbit falhou** (LXC 26
offline / sem chave SSH). Os originais ficaram em `data/biblioteca/_incoming/`
(96 MB), esperando o envio. O `.md` já está no acervo; falta o ebook no app
de leitura.

Este script reenvia tudo que estiver em `_incoming/`:
  - detecta o autor pelos metadados do EPUB/PDF (mesma logica do
    `biblioteca-push.sh`)
  - envia via API HTTP (`scripts/orbit-upload.py`)
  - **só apaga o arquivo local depois do upload confirmado**

Nao consome cota do z-library (e' so upload).

Uso:
  python3 scripts/reenviar-incoming-orbit.py            # envia tudo
  python3 scripts/reenviar-incoming-orbit.py --dry      # so lista
  python3 scripts/reenviar-incoming-orbit.py --check    # so testa a permissao
"""
import argparse
import json
import re
import subprocess
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
INCOMING = ROOT / "data" / "biblioteca" / "_incoming"
UPLOAD = ROOT / "scripts" / "orbit-upload.py"
LOG = ROOT / "data" / "perfil" / "bibliotecario" / "logs" / "orbit-reenvio.jsonl"

EXTS = {".epub", ".pdf", ".mobi", ".azw3", ".azw", ".prc", ".fb2"}


def autor_do_ebook(p: Path) -> str:
    """Extrai o autor dos metadados (EPUB -> OPF dc:creator; PDF -> pdfinfo)."""
    ext = p.suffix.lower()
    if ext == ".epub":
        try:
            with zipfile.ZipFile(p) as z:
                for name in z.namelist():
                    if name.endswith(".opf"):
                        data = z.read(name).decode("utf-8", errors="ignore")
                        m = re.search(r"<dc:creator[^>]*>([^<]+)</dc:creator>", data)
                        if m:
                            return m.group(1).strip()
        except Exception:
            pass
    elif ext == ".pdf":
        r = subprocess.run(["pdfinfo", str(p)], capture_output=True, text=True)
        m = re.search(r"^Author:\s*(.+)$", r.stdout or "", re.M)
        if m:
            return m.group(1).strip()
    return ""


def log(ev, **kw):
    rec = {"ts": __import__("time").strftime("%Y-%m-%dT%H:%M:%S"), "event": ev, **kw}
    LOG.parent.mkdir(parents=True, exist_ok=True)
    with LOG.open("a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry", action="store_true")
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--manter", action="store_true",
                    help="nao apaga o local mesmo apos upload OK")
    args = ap.parse_args()

    if args.check:
        r = subprocess.run([sys.executable, str(UPLOAD), "--check"],
                           capture_output=True, text=True, timeout=120)
        print(r.stdout + r.stderr)
        return r.returncode

    if not INCOMING.exists():
        print("sem _incoming/")
        return 0
    arquivos = sorted(p for p in INCOMING.iterdir()
                      if p.is_file() and p.suffix.lower() in EXTS)
    if not arquivos:
        print("nada em _incoming/ para reenviar")
        return 0
    total = sum(p.stat().st_size for p in arquivos)
    print(f"{len(arquivos)} ebook(s) em _incoming/ ({total//1024//1024} MB)\n")

    ok = falhou = 0
    for p in arquivos:
        autor = autor_do_ebook(p) or "_unorganized"
        if args.dry:
            print(f"[dry] {p.name} ({p.stat().st_size//1024} KB) autor={autor}")
            continue
        r = subprocess.run([sys.executable, str(UPLOAD), "--file", str(p),
                            "--autor", autor],
                           capture_output=True, text=True, timeout=900)
        if r.returncode == 0:
            ok += 1
            if not args.manter:
                try:
                    p.unlink()
                except OSError:
                    pass
            print(f"[OK] {p.name} -> Orbit (autor={autor})")
            log("reenviado", arquivo=p.name, autor=autor)
        else:
            falhou += 1
            msg = (r.stdout + r.stderr)[-220:]
            print(f"[FALHOU] {p.name}: {msg}")
            log("reenvio_falhou", arquivo=p.name, erro=msg)
            if "403" in msg and "library_upload" in msg:
                print(">> FALTA a permissao 'library_upload'. Os arquivos locais "
                      "foram PRESERVADOS. Pare aqui.")
                break

    if not args.dry:
        restantes = len([p for p in INCOMING.iterdir()
                         if p.is_file() and p.suffix.lower() in EXTS])
        print(f"\n{ok} reenviado(s), {falhou} falha(s), {restantes} restante(s) "
              f"em _incoming/")
    return 0


if __name__ == "__main__":
    sys.exit(main())
