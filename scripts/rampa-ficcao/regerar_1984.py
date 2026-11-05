#!/usr/bin/env python3
"""Regenera UM .md perdido na rampa de ficcao (1984) sem tocar nos demais.

Converte o EPUB em tempdir, valida (tamanho minimo + titulo no corpo),
move para o destino final e cataloga na KB se ainda faltar.

Uso: python3 scripts/rampa-ficcao/regerar_1984.py
"""
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import unicodedata
from pathlib import Path

ROOT = Path("/home/willian/study-agent")
BIB = ROOT / "data" / "biblioteca"
INCOMING = BIB / "_incoming"
DEST = BIB / "literatura-mundial-classica"
EPUB2MD = ROOT / "data" / "perfil" / "bibliotecario" / "biblioteca-orbit" / "epub2md.py"
KB = BIB / "global" / "kb-literatura.yaml"
LOG = ROOT / "data" / "perfil" / "bibliotecario" / "logs" / "rampa-ficcao-downloads.jsonl"

SLUG = "Orwell-1984"
TITULO = "1984"
AUTOR = "George Orwell"
SUB = "anglo-saxoes"
TAGS = ["literatura", "literatura-mundial", "romance", "canon-literario", "ingles", "distopia"]
ANO = 1949
MIN_BYTES = 40000
MIN_LINHAS = 800


def sem_acento(s):
    return "".join(c for c in unicodedata.normalize("NFKD", s or "")
                   if not unicodedata.combining(c))


def slug_canonico(titulo, autor):
    s = f"{titulo} - {autor}"
    s = sem_acento(s).replace("\u00a0", " ").replace("\u202f", " ").replace("\u2014", "-")
    s = re.sub(r"[^\w\s-]", "", s)
    s = re.sub(r"[\s_]+", "-", s)
    s = re.sub(r"-{2,}", "-", s).strip("-")
    return s[:70].strip("-")


def frontmatter(titulo, autor, tags, ano):
    t = ", ".join(f'"{x}"' for x in tags)
    return ("---\n"
            f'titulo: "{titulo}"\n'
            f'autor: "{autor}"\n'
            "idioma: Portuguese\n"
            f"ano: {ano}\n"
            f"tags: [{t}]\n"
            "tipo: literatura\n"
            "origem: rampa-ficcao-2026-11\n"
            "---\n\n")


def conteudo_confere(texto, titulo):
    t = sem_acento(titulo).lower()
    corpo = sem_acento(texto).lower()
    if t in corpo:
        return True
    partes = [p for p in re.split(r"\s+", t) if len(p) > 3 and p not in ("de", "da", "do", "e")]
    if partes and all(p in corpo for p in partes[:3]):
        return True
    return False


def cataloga_kb(entrada):
    txt = KB.read_text(encoding="utf-8")
    if entrada["caminho_md"] in txt:
        return "ja-catalogado"
    linha = (f"  - titulo: {entrada['titulo']}\n"
             f"    caminho_md: {entrada['caminho_md']}\n"
             f"    tamanho_md: {entrada['tamanho_md']}\n"
             f"    linhas_md: {entrada['linhas_md']}\n"
             "    idioma: Portuguese\n"
             f"    tags: [{entrada['tags_yaml']}]\n"
             f"    ano: {entrada['ano']}\n"
             "    status: indexado_auto\n"
             "    nota: Adquirido 2026-11-05 (rampa de ficcao, traducao PT-BR).\n")
    m = re.search(r"^knowledge_base_literatura:\n(?:.*\n)*?\s*materiais:\n", txt, re.M)
    if not m:
        return "falha-bloco"
    KB.write_text(txt[:m.end()] + linha + txt[m.end():], encoding="utf-8")
    return "catalogado"


def main():
    src = INCOMING / f"{SLUG}.epub"
    if not src.exists():
        print(f"FALHA: {src} nao existe")
        sys.exit(1)

    destino = DEST / SUB / f"{slug_canonico(TITULO, AUTOR)}.md"
    destino.parent.mkdir(parents=True, exist_ok=True)

    tmp = Path(tempfile.mkdtemp(prefix="rampa-conv-1984-"))
    try:
        r = subprocess.run([sys.executable, str(EPUB2MD), "--dest", str(tmp), str(src)],
                           capture_output=True, text=True, timeout=1800)
        mds = list(tmp.glob("*.md"))
        if not mds:
            print(f"FALHA-CONV: sem .md gerado. stdout={r.stdout[-300:]} stderr={r.stderr[-300:]}")
            sys.exit(2)
        gerado = max(mds, key=lambda p: p.stat().st_size)
        txt = gerado.read_text(encoding="utf-8", errors="ignore")
        linhas = txt.count("\n")
        tam = gerado.stat().st_size
        if tam < MIN_BYTES or linhas < MIN_LINHAS:
            print(f"FALHA-CONV: texto curto demais ({tam//1024} KB, {linhas} lin)")
            sys.exit(3)
        if not conteudo_confere(txt, TITULO):
            print("FALHA-CONV: titulo '1984' nao aparece no texto extraido — conteudo divergente")
            sys.exit(4)
        shutil.move(str(gerado), str(destino), copy_function=os.replace)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    txt = destino.read_text(encoding="utf-8", errors="ignore")
    if not txt.lstrip().startswith("---"):
        destino.write_text(frontmatter(TITULO, AUTOR, TAGS, ANO) + txt, encoding="utf-8")
    final = destino.read_text(encoding="utf-8", errors="ignore")
    entrada = {
        "titulo": f"LT {TITULO} - {AUTOR}",
        "caminho_md": f"./data/biblioteca/literatura-mundial-classica/{SUB}/{destino.name}",
        "tamanho_md": f"{destino.stat().st_size // 1024} KB",
        "linhas_md": final.count("\n"),
        "tags_yaml": ", ".join(TAGS),
        "ano": ANO,
    }
    st = cataloga_kb(entrada)
    print(f"[OK] {destino.relative_to(ROOT)}  {entrada['tamanho_md']}  {entrada['linhas_md']} lin | KB={st}")
    with LOG.open("a", encoding="utf-8") as f:
        f.write(json_line := '{"ts": "%s", "event": "finalizado", "arquivo": "%s", "kb": "%s"}\n'
                 % (time.strftime("%Y-%m-%dT%H:%M:%S"), entrada["caminho_md"].lstrip("./"), st))


if __name__ == "__main__":
    main()
