"""Testa o finalizador num unico epub (sem push) para validar frontmatter + KB."""
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path("/home/willian/study-agent")
INC = ROOT / "data/biblioteca/_incoming"
TESTE = INC / "Dostoievski-O-Jogador.epub"

# backup da KB
KB = ROOT / "data/biblioteca/global/kb-literatura.yaml"
bk = KB.with_suffix(".yaml.bak-teste")
shutil.copy2(KB, bk)

# roda o finalizador so com esse arquivo
r = subprocess.run([sys.executable, str(ROOT / "scripts/finalizar-rampa.py"), "--sem-push"],
                   capture_output=True, text=True, timeout=900, cwd=str(ROOT / "scripts"))
print(r.stdout[-3000:])
print("STDERR:", r.stderr[-1500:])

print("\n=== KB: primeiras 25 linhas do bloco materiais ===")
t = KB.read_text(encoding="utf-8")
i = t.find("materiais:")
print(t[i:i + 1600])

print("\n=== .md gerado: frontmatter ===")
md = ROOT / "data/biblioteca/literatura-mundial-classica/dostoievski"
for f in sorted(md.glob("*.md")):
    print(f.name)
    print(f.read_text(encoding="utf-8")[:500])

# restaura KB
shutil.copy2(bk, KB)
bk.unlink()
print("\nKB restaurada do backup.")
