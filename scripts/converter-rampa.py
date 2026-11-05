#!/usr/bin/env python3
"""Converte os EPUBs da _incoming/ em .md dentro de data/biblioteca/literatura-mundial-classica/
e depois move os ebooks para o Orbit (data/biblioteca/_incoming é temporário).

Uso: python3 converter-rampa.py
"""
import subprocess
import sys
from pathlib import Path

ROOT = Path("/home/willian/study-agent")
EPUB2MD = ROOT / "data" / "perfil" / "bibliotecario" / "biblioteca-orbit" / "epub2md.py"
INCOMING = ROOT / "data" / "biblioteca" / "_incoming"
DEST = ROOT / "data" / "biblioteca" / "literatura-mundial-classica"
DEST.mkdir(parents=True, exist_ok=True)

# subpastas por eixo (ficcao classica mundial em PT)
SUBDIRS = {
    "Dostoievski": "dostoievski",
    "Tolstoi": "tolstoi",
    "Austen": "austen",
    "Brontë": "bronte",
    "Dickens": "dickens",
    "Agostinho": "agostinho",
    "Dante": "dante",
    "Flaubert": "frances",
    "Proust": "proust",
    "Homero": "antigos",
    "Virgilio": "antigos",
    "Goethe": "antigos",
    "Hugo": "frances",
    "Melville": "anglo-saxoes",
    "Eliot": "anglo-saxoes",
    "Shelley": "anglo-saxoes",
    "Twain": "anglo-saxoes",
    "Orwell": "anglo-saxoes",
    "Joyce": "anglo-saxoes",
    "Woolf": "anglo-saxoes",
    "Maupassant": "contos",
    "Kipling": "anglo-saxoes",
    "Chesterton": "cristiana",
    "Lewis": "cristiana",
    "Bunyan": "cristiana",
    "Greene": "cristiana",
    "OConnor": "cristiana",
}


def subdir_de(slug):
    for k, v in SUBDIRS.items():
        if slug.startswith(k):
            return v
    return "outros"


def main():
    epubs = sorted(INCOMING.glob("*.epub"))
    if not epubs:
        print("nada na _incoming")
        return
    print(f"{len(epubs)} epub(s) para converter\n")
    ok, fail = 0, 0
    for e in epubs:
        sub = DEST / subdir_de(e.stem)
        sub.mkdir(parents=True, exist_ok=True)
        r = subprocess.run([sys.executable, str(EPUB2MD), "--dest", str(sub), str(e)],
                           capture_output=True, text=True, timeout=900)
        # o nome gerado usa o stem do epub -> preenche com metadado depois
        saida = sub / f"{e.stem}.md"
        if r.returncode != 0:
            print(f"[FALHA] {e.name}: {r.stderr[-300:]}")
            fail += 1
            continue
        # o epub2md nomeia pelo stem; se o arquivo existir com outro nome, localiza
        mds = sorted(sub.glob(f"{e.stem}*.md"))
        if not mds:
            print(f"[FALHA] {e.name}: nenhum .md gerado")
            print(r.stdout[-400:])
            fail += 1
            continue
        for md in mds:
            txt = md.read_text(encoding="utf-8", errors="ignore")
            linhas = txt.count("\n")
            print(f"[OK] {md.name}  {md.stat().st_size//1024} KB  {linhas} linhas  "
                  f"-> {sub.name}/")
            ok += 1
    print(f"\n=== convertidos: {ok} | falhas: {fail} ===")


if __name__ == "__main__":
    main()
