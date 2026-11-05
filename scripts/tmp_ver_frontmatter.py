from pathlib import Path

for p in [
    "/home/willian/study-agent/data/biblioteca/literatura-mundial-classica/dostoievski/Dostoievski-O-Jogador.md",
    "/home/willian/study-agent/data/biblioteca/literatura-mundial-classica/Cervantes-Dom-Quixote.md",
]:
    f = Path(p)
    print("=" * 70)
    print(f.name, "|", f.stat().st_size // 1024, "KB")
    print("-" * 70)
    print(f.read_text(encoding="utf-8", errors="ignore")[:900])
