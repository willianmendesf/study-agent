from pathlib import Path

LOG = Path("/home/willian/study-agent/data/perfil/bibliotecario/logs/rampa-dl.log")
INC = Path("/home/willian/study-agent/data/biblioteca/_incoming")

if LOG.exists():
    linhas = LOG.read_text(encoding="utf-8").splitlines()
    print(f"--- log ({len(linhas)} linhas) ---")
    for l in linhas[-35:]:
        print(l)
else:
    print("log ainda nao criado")

print("\n--- _incoming ---")
if INC.exists():
    fs = sorted(INC.iterdir())
    print(f"{len(fs)} arquivos")
    tot = 0
    for f in fs:
        sz = f.stat().st_size
        tot += sz
        print(f"  {f.name:52s} {sz//1024:6d} KB")
    print(f"total: {tot//1024//1024} MB")
else:
    print("pasta nao existe")
