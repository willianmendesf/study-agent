import subprocess
from pathlib import Path

ROOT = Path("/home/willian/study-agent")
print("=== estrutura literatura-mundial-classica ===")
for d in sorted((ROOT / "data/biblioteca/literatura-mundial-classica").iterdir()):
    if d.is_dir():
        fs = sorted(d.glob("*.md"))
        tot = sum(f.stat().st_size for f in fs)
        print(f"  {d.name:14s} {len(fs):2d} .md  {tot//1024//1024:4d} MB")
        for f in fs:
            print(f"      {f.name}")

print("\n=== _incoming restante ===")
inc = ROOT / "data/biblioteca/_incoming"
for f in sorted(inc.iterdir()):
    print(f"  {f.name:52s} {f.stat().st_size//1024:6d} KB")

print("\n=== pdftotext disponivel? ===")
r = subprocess.run(["which", "pdftotext"], capture_output=True, text=True)
print(" ", r.stdout.strip() or "NAO ENCONTRADO")
