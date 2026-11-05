import json, glob, os, re

KEY = re.compile(r'(fic[çc][ãa]o|livro de fic|romance|leitura)', re.I)

paths = sorted(glob.glob('/home/willian/study-agent/sessions/*.jsonl'), key=os.path.getmtime)
for p in paths:
    if 'sk_v1_' in p:
        continue
    hits = []
    for line in open(p, errors='replace'):
        try:
            d = json.loads(line)
        except Exception:
            continue
        r = d.get('role')
        if r not in ('user', 'assistant'):
            continue
        c = d.get('content')
        t = c if isinstance(c, str) else ' '.join(x.get('text', '') for x in (c or []) if isinstance(x, dict))
        if t and KEY.search(t):
            hits.append((r, t[:700]))
    if hits:
        print('=' * 20, os.path.basename(p), len(hits))
        for r, t in hits[:6]:
            print('###', r, ':', t.replace('\n', ' ')[:700])
            print()
