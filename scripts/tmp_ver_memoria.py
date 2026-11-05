from pathlib import Path

p = Path("/home/willian/study-agent/memory/MEMORY.md")
t = p.read_text(encoding="utf-8")
i = t.find("Rampa de leitura")
if i > 0:
    print("=== ACHOU em", i, "===")
    print(t[max(0, i - 300):i + 1500])
else:
    print("=== NAO ACHOU. headers: ===")
    for ln in t.splitlines():
        if ln.startswith("#"):
            print(ln)
