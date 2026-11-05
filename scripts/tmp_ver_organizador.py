from pathlib import Path

ROOT = Path("/home/willian/study-agent")
# ver como oorganizar-rodada monta o frontmatter
p = ROOT / "data/perfil/bibliotecario/biblioteca-orbit/organizar-rodada.py"
t = p.read_text(encoding="utf-8")
i = t.lower().find("frontmatter")
if i > 0:
    print(t[max(0, i - 1500):i + 2500])
else:
    print("=== sem 'frontmatter'; procurando 'titulo:' ===")
    i = t.find("titulo:")
    print(t[max(0, i - 1200):i + 2000] if i > 0 else t[:3000])
