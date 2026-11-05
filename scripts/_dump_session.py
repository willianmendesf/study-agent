import json, glob, os

paths = sorted(glob.glob('/home/willian/study-agent/sessions/sk_v1_*.jsonl'), key=os.path.getmtime)
p = paths[-1]
print('FILE:', p)
for line in open(p):
    try:
        d = json.loads(line)
    except Exception:
        continue
    r = d.get('role') or d.get('type')
    if r not in ('user', 'assistant'):
        continue
    c = d.get('content')
    if isinstance(c, str):
        t = c
    else:
        t = ' '.join(x.get('text', '') for x in (c or []) if isinstance(x, dict))
    if not t.strip():
        continue
    print('###', r, ':', t[:1200])
    print()
