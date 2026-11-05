#!/usr/bin/env python3
"""Regera A Revolucao dos Animais (o .md atual tem o TEXTO DO 1984 — bug do fallback).

Causa: o epub2md.py nao suporta .mobi; o finalizador caiu no fallback e pegou o
.md de outro livro. Aqui o texto vem do mobi2txt.py (novo) e a validacao por
conteudo e feita contra marcadores distintivos da obra.

Uso: python3 scripts/rampa-ficcao/regenerar_revolucao.py
"""
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path("/home/willian/study-agent")
SRC = ROOT / "data/biblioteca/_incoming/Orwell-A-Revolucao-dos-Animais.mobi"
MOBI2TXT = ROOT / "data/perfil/bibliotecario/biblioteca-orbit/mobi2txt.py"
DEST = ROOT / "data/biblioteca/literatura-mundial-classica/anglo-saxoes/A-Revolucao-dos-Animais-George-Orwell.md"
KB = ROOT / "data/biblioteca/global/kb-literatura.yaml"
LOG = ROOT / "data/perfil/bibliotecario/logs/rampa-ficcao-downloads.jsonl"

TITULO = "A Revolução dos Animais"
AUTOR = "George Orwell"
TAGS = ["literatura", "literatura-mundial", "romance", "canon-literario", "ingles", "distopia"]
ANO = 1945
MIN_BYTES = 40000

# marcadores que so aparecem nesta obra
# a traducao PT-BR usa nomes TRANSLITERADOS (Napoleao, Bola de Neve, Guinchento),
# por isso os marcadores sao em portugues — os ingleses nao dariam match.
MARCADORES = ["fazenda dos animais", "napoleao", "bola de neve", "guinchento",
              "boxer", "azezinha" , "whymper", "mandamento", "sete mandamentos",
              "animalismo", "moinho de vento", "pilkington", "jones",
              "revolucao", "comandante", "lider"]


def main():
    tmp = Path("/tmp/revolucao_texto.md")
    r = subprocess.run([sys.executable, str(MOBI2TXT), str(SRC), "-o", str(tmp)],
                       capture_output=True, text=True, timeout=900)
    if r.returncode != 0:
        print(f"FALHA: mobi2txt retornou {r.returncode}\n{r.stderr[-500:]}")
        return 2
    txt = tmp.read_text(encoding="utf-8", errors="ignore")
    tam = tmp.stat().st_size
    if tam < MIN_BYTES:
        print(f"FALHA: texto curto demais ({tam} bytes)")
        return 3

    low = txt.lower()
    achados = [m for m in MARCADORES if m in low]
    print(f"texto: {tam} bytes, {txt.count(chr(10))+1} linhas")
    print(f"marcadores achados: {len(achados)}/{len(MARCADORES)} -> {achados}")
    if len(achados) < 4:
        print("FALHA: conteudo nao confere (marcadores insuficientes)")
        return 4
    if "1984" in low and "fazenda dos animais" not in low:
        print("FALHA: parece ser o 1984")
        return 5

    fm = ("---\n"
          f'titulo: "{TITULO}"\n'
          f'autor: "{AUTOR}"\n'
          "idioma: Portuguese\n"
          f"ano: {ANO}\n"
          f"tags: [{', '.join(chr(34) + t + chr(34) for t in TAGS)}]\n"
          "tipo: literatura\n"
          "origem: rampa-ficcao-2026-11\n"
          "---\n\n")
    DEST.parent.mkdir(parents=True, exist_ok=True)
    novo = fm + txt
    tmp_dest = DEST.with_suffix(".md.tmp")
    tmp_dest.write_text(novo, encoding="utf-8")
    os.replace(tmp_dest, DEST)          # substituicao atomica
    tmp.unlink(missing_ok=True)

    # atualiza a KB
    kbtxt = KB.read_text(encoding="utf-8")
    rel = "./data/biblioteca/literatura-mundial-classica/anglo-saxoes/A-Revolucao-dos-Animais-George-Orwell.md"
    if rel not in kbtxt:
        print("AVISO: caminho nao encontrado na KB")
    else:
        tam_kb = f"{DEST.stat().st_size // 1024} KB"
        lin_kb = DEST.read_text(encoding='utf-8', errors='ignore').count("\n")
        kbtxt = re.sub(
            r"(  - titulo: LT A Revolução dos Animais - George Orwell\n"
            r"    caminho_md: " + re.escape(rel) + r"\n)"
            r"    tamanho_md: .+?\n    linhas_md: \d+\n",
            r"\1    tamanho_md: " + tam_kb + "\n    linhas_md: " + str(lin_kb) + "\n",
            kbtxt)
        KB.write_text(kbtxt, encoding="utf-8")

    print(f"[OK] {DEST.relative_to(ROOT)} — {DEST.stat().st_size//1024} KB, "
          f"{lin_kb} linhas | KB atualizada")
    with LOG.open("a", encoding="utf-8") as f:
        f.write('{"ts": "%s", "event": "finalizado", "arquivo": "%s", "kb": "corrigido-mobi"}\n'
                % (time.strftime("%Y-%m-%dT%H:%M:%S"),
                   rel.lstrip("./")))
    return 0


if __name__ == "__main__":
    sys.exit(main())
