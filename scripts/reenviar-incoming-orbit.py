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
import hashlib
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

# Fallback de autor por prefixo do nome do arquivo.
# 2026-11-05: PDF e MOBI nao tem dc:creator nos metadados — o script mandava
#Virgilio-A-Eneida.pdf e Orwell-A-Revolucao-dos-Animais.mobi como
# "_unorganized" (sem autor, sem pasta). A fila foi montada pelo
# scripts/finalizar-rampa.py com o padrao "<Autor>-<Titulo>.<ext>".
AUTOR_POR_PREFIXO = {
    "Agostinho": "Agostinho de Hipona",
    "Austen": "Jane Austen",
    "Brontë": "Charlotte Brontë",
    "Dante": "Dante Alighieri",
    "Dickens": "Charles Dickens",
    "Dostoievski": "Fiódor Dostoiévski",
    "Eliot": "George Eliot",
    "Flaubert": "Gustave Flaubert",
    "Goethe": "Johann Wolfgang von Goethe",
    "Homero": "Homero",
    "Melville": "Herman Melville",
    "Orwell": "George Orwell",
    "Proust": "Marcel Proust",
    "Shelley": "Mary Shelley",
    "Tolstoi": "Lev Tolstói",
    "Twain": "Mark Twain",
    "Virgilio": "Virgílio",
    "Woolf": "Virginia Woolf",
}


def autor_por_nome(p: Path) -> str:
    """Autor inferido do prefixo do nome do arquivo ('Austen-Emma.epub')."""
    prefixo = p.stem.split("-")[0].strip()
    return AUTOR_POR_PREFIXO.get(prefixo, "")


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
        # 2026-11-05: `pdfinfo` (poppler-utils) NAO existe nesta LXC — o
        # fallback silencioso mandava o PDF para "_unorganized". Usa pypdf.
        try:
            import pypdf
            r = pypdf.PdfReader(str(p))
            meta = r.metadata or {}
            autor = str(meta.get("/Author") or "").strip()
            if autor:
                return autor
            titulo = str(meta.get("/Title") or "").strip()
            if titulo:
                return titulo
        except Exception:
            pass
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

    # DEDUPLICACAO POR CONTEUDO (2026-11-05).
    # A fila tinha 'TESTE-Crime-e-Castigo.epub' e 'Dostoievski-Crime-e-Castigo.epub'
    # byte-a-byte identicos (mesmo md5) — subiria o mesmo livro 2x no app.
    # O duplicado NAO e' enviado. Ele so e' apagado do disco DEPOIS que o
    # original for enviado com sucesso (nada se perde se o upload falhar).
    vistos: dict[str, Path] = {}
    dups: dict[Path, Path] = {}   # duplicado -> original
    for p in arquivos:
        try:
            h = hashlib.md5(p.read_bytes()).hexdigest()
        except OSError:
            continue
        if h in vistos:
            dups[p] = vistos[h]
        else:
            vistos[h] = p
    for dup, orig in dups.items():
        print(f"[dedup] {dup.name} e' copia identica de {orig.name} — "
              f"nao sera enviado")
        log("dedup_detectado", arquivo=dup.name, igual_a=orig.name)
    if dups:
        arquivos = [p for p in arquivos if p not in dups]

    total = sum(p.stat().st_size for p in arquivos)
    print(f"{len(arquivos)} ebook(s) em _incoming/ ({total//1024//1024} MB)\n")

    ok = falhou = 0
    for p in arquivos:
        autor = autor_do_ebook(p) or autor_por_nome(p) or "_unorganized"
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
            # Duplicados byte-a-byte deste arquivo: agora que o original
            # subiu com sucesso, o duplicado pode ser apagado do disco.
            for dup, orig in dups.items():
                if orig == p:
                    try:
                        dup.unlink()
                        print(f"[dedup] {dup.name} removido (copia identica "
                              f"de {p.name}, ja enviado)")
                        log("dedup_removido", arquivo=dup.name, original=p.name)
                    except OSError:
                        pass
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
