import subprocess
from pathlib import Path

ROOT = Path("/home/willian/study-agent")
print("--- epub2md ---")
r = subprocess.run(["find", str(ROOT), "-name", "epub2md*", "-not", "-path", "*/node_modules/*"],
                   capture_output=True, text=True)
print(r.stdout or "(nada)")

print("--- referencias em scripts ---")
for pat in ["epub2md.py", "organizar-rodada", "rodada-diaria.sh"]:
    r = subprocess.run(["grep", "-rln", pat, str(ROOT / "data" / "perfil" / "bibliotecario"),
                        str(ROOT / ".claude" / "skills" / "study-gerenciar-bibliotecas")],
                       capture_output=True, text=True)
    print(f"  {pat}: {r.stdout.strip()[:400] or '(nada)'}")
