import json
from pathlib import Path

LOG = Path("/home/willian/study-agent/data/perfil/bibliotecario/logs/rampa-ficcao-downloads.jsonl")
if not LOG.exists():
    print("JSONL ainda nao criado")
else:
    recs = [json.loads(l) for l in LOG.read_text(encoding="utf-8").splitlines() if l.strip()]
    ok = [r for r in recs if r["event"] == "baixado"]
    bad = [r for r in recs if r["event"] != "baixado"]
    print(f"registros: {len(recs)} | baixados: {len(ok)} | outros: {len(bad)}")
    print("\n--- BAIXADOS ---")
    for r in ok:
        print(f"  {r['slug']:42s} {r.get('info','')[:14]:14s} <- {str(r.get('zlib_title'))[:48]}")
    print("\n--- PROBLEMAS ---")
    for r in bad:
        print("  ", {k: v for k, v in r.items() if k != "ts"})
