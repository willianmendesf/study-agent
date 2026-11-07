import re, glob, os, unicodedata, json

def remove_acentos(s):
    return ''.join(c for c in unicodedata.normalize('NFD', s) if unicodedata.category(c)!='Mn')

SILABAS = re.compile(r'[aeiouy]+', re.I)
def n_silabas(pal):
    m = SILABAS.findall(remove_acentos(pal))
    return max(1, len(m))

def texto_prosa(path):
    txt = open(path, encoding='utf-8', errors='ignore').read()
    # remove frontmatter
    if txt.startswith('---'):
        partes = txt.split('---', 2)
        if len(partes) >= 3: txt = partes[2]
    linhas = []
    for ln in txt.split('\n'):
        s = ln.strip()
        if not s: continue
        if s.startswith('#'): continue
        if len(s) < 60: continue          # apparatus / titulos curtos
        if re.match(r'^[\d\[\]\(\)\*·—\-\s]+$', s): continue
        if re.search(r'\[\d+\]|\(\d+\)', s) and len(re.findall(r'\[\d+\]|\(\d+\)', s)) > 2: continue
        linhas.append(s)
    return ' '.join(linhas)

def medir(path):
    t = texto_prosa(path)
    # remove numeros de nota e marcas
    t = re.sub(r'\[\d+\]|\(\d+\)', ' ', t)
    t = re.sub(r'[—–\-]{2,}', ' ', t)
    # frases
    frases = [f for f in re.split(r'(?<=[.!?…])\s+', t) if len(f.split()) >= 3]
    if not frases: return None
    palavras = [p for p in re.findall(r"[A-Za-zÀ-ÿ][A-Za-zÀ-ÿ'’-]*", t)]
    n_p = len(palavras)
    if n_p < 400: return None
    pl = [len(f.split()) for f in frases]
    Hard = 0
    for p in palavras:
        pl2 = p.lower()
        if n_silabas(p) >= 4: Hard += 1
    palavras_longas = sum(1 for p in palavras if len(p) >= 11)
    return {
        'palavras': n_p,
        'frases': len(frases),
        'palavras_por_frase': round(sum(pl)/len(pl), 1),
        'frase_mais_longa': max(pl),
        '%_silabas4+': round(100*Hard/n_p, 1),
        '%_palavras_11+chars': round(100*palavras_longas/n_p, 1),
        'nomes_proprios_palavra': round(100*sum(1 for p in palavras if p[0].isupper() and not p.isupper())/n_p,1),
    }

alvos = []
for pat in ['data/biblioteca/literatura-mundial-classica/*/*.md',
            'data/biblioteca/literatura-brasileira/*.md',
            'data/biblioteca/literatura-mundial-classica/*.md']:
    alvos += glob.glob(pat)

res = {}
for f in sorted(set(alvos)):
    try:
        m = medir(f)
    except Exception as e:
        m = None
    if m:
        m['arquivo'] = f
        m['nome'] = os.path.basename(f).replace('.md','')
        res[m['nome']] = m

# score de dificuldade: media ponderada
def score(m):
    return round(0.45*m['palavras_por_frase'] + 0.35*m['%_silabas4+']*1.2 + 0.20*m['%_palavras_11+chars']*1.5, 1)

print(f"{'obra':62} {'palav':>6} {'p/frase':>7} {'sil4+':>6} {'long11':>6} {'SCORE':>6}")
rank = sorted(res.values(), key=score)
for m in rank:
    s = score(m)
    m['score'] = s
    print(f"{m['nome'][:62]:62} {m['palavras']:6d} {m['palavras_por_frase']:7.1f} {m['%_silabas4+']:6.1f} {m['%_palavras_11+chars']:6.1f} {s:6.1f}")

json.dump(rank, open('/tmp/legibilidade.json','w'), ensure_ascii=False, indent=1)
