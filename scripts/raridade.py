import re, glob, os, json, unicodedata
from collections import Counter

def norm(s):
    s = unicodedata.normalize('NFC', s.lower())
    return re.sub(r'[^a-zà-ÿ]', '', s)

# corpus de referencia: amostra do acervo (para freq de palavra)
ref = Counter()
files = [f for f in glob.glob('data/biblioteca/**/*.md', recursive=True)
         if os.path.getsize(f) > 40000 and 'legibilidade' not in f]
import random
random.seed(7)
random.shuffle(files)
for f in files[:420]:
    t = open(f, encoding='utf-8', errors='ignore').read()
    for w in re.findall(r"[A-Za-zÀ-ÿ][A-Za-zÀ-ÿ'’-]{2,}", t):
        n = norm(w)
        if len(n) >= 3: ref[n] += 1

def texto_prosa(path):
    t = open(path, encoding='utf-8', errors='ignore').read()
    if t.startswith('---'):
        p = t.split('---', 2); t = p[2] if len(p) >= 3 else t
    ls = []
    for ln in t.split('\n'):
        s = ln.strip()
        if not s or s.startswith('#') or len(s) < 60: continue
        if re.search(r'\[\d+\]|\(\d+\)', s) and len(re.findall(r'\[\d+\]|\(\d+\)', s)) > 2: continue
        ls.append(s)
    return ' '.join(ls)

def medir(path):
    t = texto_prosa(path)
    t = re.sub(r'\[\d+\]|\(\d+\)', ' ', t)
    frases = [f for f in re.split(r'(?<=[.!?…])\s+', t) if len(f.split()) >= 3]
    pl = [len(f.split()) for f in frases]
    palavras = re.findall(r"[A-Za-zÀ-ÿ][A-Za-zÀ-ÿ'’-]*", t)
    if len(palavras) < 400 or not pl: return None
    # hapax: palavra que nao aparece em mais de X outros livros do corpus
    docfreq = Counter()
    for w in set(norm(x) for x in palavras):
        if len(w) >= 4: docfreq[w] += 1
    # raridade: % de palavras cuja freq global no corpus <= 5 ocorrencias
    raros = sum(1 for w in palavras if len(norm(w)) >= 4 and ref.get(norm(w), 0) <= 5)
    # hapax do proprio livro (so aparece 1x no livro)
    cnt = Counter(norm(w) for w in palavras)
    hapax = sum(v for v in cnt.values() if v == 1)
    return {
        'palavras': len(palavras),
        'pfrase': round(sum(pl)/len(pl), 1),
        'mediana_frase': sorted(pl)[len(pl)//2],
        '%_raro': round(100*raros/len(palavras), 1),
        '%_hapax': round(100*hapax/len(palavras), 1),
        'n_anos_1900': None,
    }

alvos = sorted(set(glob.glob('data/biblioteca/literatura-mundial-classica/*/*.md') +
                   glob.glob('data/biblioteca/literatura-brasileira/*.md')))
res = []
for f in alvos:
    try: m = medir(f)
    except Exception: m = None
    if m and m['palavras'] > 8000:
        m['nome'] = os.path.basename(f)[:-3]; m['arquivo'] = f
        res.append(m)

print(f"{'obra':56} {'palav':>7} {'pfr':>5} {'med':>4} {'raro%':>6} {'hapax%':>7}")
for m in sorted(res, key=lambda x: x['%_raro']):
    print(f"{m['nome'][:56]:56} {m['palavras']:7d} {m['pfrase']:5.1f} {m['mediana_frase']:4d} {m['%_raro']:6.1f} {m['%_hapax']:7.1f}")
json.dump(res, open('/tmp/raridade.json','w'), ensure_ascii=False, indent=1)
