import re
from pathlib import Path

ROOT = Path("/home/willian/study-agent")
DEST = ROOT / "data/biblioteca/literatura-mundial-classica"

print("=== .md por pasta ===")
vistos = {}
for d in sorted(DEST.iterdir()):
    if not d.is_dir():
        continue
    for f in sorted(d.glob("*.md")):
        txt = f.read_text(encoding="utf-8", errors="ignore")
        m = re.search(r'^titulo:\s*"(.*?)"', txt, re.M)
        a = re.search(r'^autor:\s*"(.*?)"', txt, re.M)
        print(f"  {d.name:14s} {f.name[:56]:56s} | {m.group(1) if m else '(sem fm)':30s} | {a.group(1) if a else ''}")
        vistos[f.name] = (d.name, f)

print("\n=== KB: caminhos que NAO existem ===")
KB = ROOT / "data/biblioteca/global/kb-literatura.yaml"
txt = KB.read_text(encoding="utf-8")
paths = re.findall(r"caminho_md:\s*(\S+)", txt)
quebrados = [p for p in paths if not (ROOT / p.lstrip("./")).exists()]
print(f"total caminhos: {len(paths)} | quebrados: {len(quebrados)}")
for p in quebrados[:40]:
    print("   ", p)

print("\n=== .md duplicados (mesmo tamanho, subpastas diferentes) ===")
from collections import defaultdict
por_tam = defaultdict(list)
for d in DEST.iterdir():
    if d.is_dir():
        for f in d.glob("*.md"):
            por_tam[f.stat().st_size].append(f"{d.name}/{f.name}")
for tam, fs in por_tam.items():
    if len(fs) > 1:
        print(f"  {tam//1024} KB:")
        for f in fs:
            print("     ", f)
