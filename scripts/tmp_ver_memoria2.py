from pathlib import Path

p = Path("/home/willian/study-agent/memory/MEMORY.md")
t = p.read_text(encoding="utf-8")
i = t.find("Rampa de leitura — estante de casa")
print(t[max(0, i - 100):i + 3000])
