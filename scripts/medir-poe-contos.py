#!/usr/bin/env python3
"""Mede os CONTOS do Poe (um por um) — 'Os Misterios de Poe' (Hyperion).

O volume tem ~80 obras datadas num so arquivo. Medir o VOLUME mede o
container (90 obras + bio + ensaios + 19 poemas), nao o que o leitor le.
Por isso: um conto = uma unidade.

ESTRUTURA REAL do corpo (verificada nas linhas 4668+ e 6964+):
    <titulo PT>
    <titulo EN>
    (AAAA)
    ...texto...

Usa o mesmo corpus de referencia e as mesmas formulas do
scripts/medir-sherlock-contos.py (comparabilidade entre as series).

NAO escreve nada no repo. Saida: /tmp/poe-contos.json
"""
import re, os, json, unicodedata
from collections import Counter

SIL = re.compile(r'[aeiouy]+', re.I)


def ra(s):
    return ''.join(c for c in unicodedata.normalize('NFD', s) if unicodedata.category(c) != 'Mn')


def nsil(p):
    return max(1, len(SIL.findall(ra(p))))


def norm(s):
    return re.sub(r'[^a-zà-ÿ]', '', unicodedata.normalize('NFC', s.lower()))


def squash(s):
    return ''.join(ch for ch in ra(s).lower() if ch.isalpha() and ch.isascii())


def prosa(txt):
    ls = []
    for ln in txt.split('\n'):
        s = ln.strip()
        if not s or s.startswith('#') or len(s) < 60:
            continue
        if re.match(r'^[\d\[\]\(\)\*·—\-\s]+$', s):
            continue
        ls.append(s)
    return ' '.join(ls)


CACHE = '/tmp/corpus-ref-rampa.json'
ref = Counter(json.load(open(CACHE))) if os.path.exists(CACHE) else Counter()

CONECT = [r'\bmas\b', r'\bque\b', r'\bembora\b', r'\bporque\b', r'\bportanto\b', r'\bporém\b',
          r'\bporem\b', r'\bpois\b', r'\bquando\b', r'\bse\b', r'\bcaso\b', r'\bconquanto\b',
          r'\bde modo que\b', r'\bvisto que\b', r'\bja que\b', r'\bdesde que\b', r'\bpara que\b',
          r'\bconforme\b', r'\bsegundo\b', r'\bemquanto\b']
C = re.compile('|'.join(CONECT), re.I)
STOP = set("""a o e de do da das dos em no na nos nas um uma uns umas que se por com nao os as ao aos
ou mais como mas foi ser seu sua seus suas ele ela eles elas isso este esta isto meu minha te tu voce
nos nossa nosso ja muito tambem so ainda quando onde qual porque entao sim sou estou estao tinha
estar fez fazer disse ver pode ter sabia veio dar homem mulher moca rapariga velho dona senhor senhora
ate cada toda todo todos todas outro outra nenhum sera serao foi ha aquela aquele
""".split())


def medir(txt):
    t = re.sub(r'\[\d+\]|\(\d+\)', ' ', txt)
    fr = [f for f in re.split(r'(?<=[.!?…])\s+', t) if len(f.split()) >= 3]
    if len(fr) < 12:
        return None
    pl = [len(f.split()) for f in fr]
    pw = re.findall(r"[A-Za-zÀ-ÿ][A-Za-zÀ-ÿ'’-]*", t)
    if len(pw) < 350:
        return None
    sil4 = sum(1 for p in pw if nsil(p) >= 4)
    l11 = sum(1 for p in pw if len(p) >= 11)
    raros = sum(1 for w in pw if len(norm(w)) >= 4 and ref.get(norm(w), 0) <= 5)
    proprios = set()
    for w in pw:
        if w[0].isupper() and w.lower() not in STOP and len(w) >= 3 and not w.isupper():
            proprios.add(norm(w))
    sub = sum(1 for x in fr if C.search(x))
    sint = 0.45 * (sum(pl) / len(pl)) + 0.35 * sil4 / len(pw) * 1.2 + 0.20 * l11 / len(pw) * 1.5
    ling = round(0.35 * sint + 0.40 * (100 * raros / len(pw)) * 2.2 + 0.25 * (len(pw) / 100000 * 8), 2)
    l10 = min(10, ling / 1.2)
    i10 = min(10, 100 * sub / len(fr) / 7.0)
    c10 = min(10, 1000 * len(proprios) / len(pw) / 2.5)
    return {
        'palavras': len(pw), 'frases': len(fr), 'pfrase': round(sum(pl) / len(pl), 1),
        'raro%': round(100 * raros / len(pw), 1),
        'subord%': round(100 * sub / len(fr), 1),
        'prop_1k': round(1000 * len(proprios) / len(pw), 1),
        'nomes': len(proprios),
        'score_ling': ling,
        'score_rampa': round(0.35 * l10 + 0.40 * i10 + 0.25 * c10, 2),
    }


PATH = 'data/biblioteca/literatura-mundial-classica/portugues/Poe-Edgar-Allan-Os-Misterios-de-Poe.md'
linhas = open(PATH, encoding='utf-8', errors='ignore').read().split('\n')

# 1) acha os blocos <titulo PT> / <titulo EN> / (AAAA)
#    heuristica: linha i = titulo PT (curta, sem ponto final), i+1 = titulo EN,
#    i+2 = (AAAA)
ANOS = re.compile(r'^\(\s*(\d{4})\s*\)$')
contos = []
for i in range(len(linhas) - 2):
    pt = linhas[i].strip()
    en = linhas[i + 1].strip()
    yr = linhas[i + 2].strip()
    if not pt or not en or not ANOS.match(yr):
        continue
    if len(pt) > 70 or len(en) > 70 or len(pt) < 3:
        continue
    # titulo PT: comeca com letra maiuscula e tem ao menos 2 palavras
    if not pt[0].isupper() or len(pt.split()) < 2:
        continue
    # titulo EN: comeca com letra maiuscula E tem palavra inglesa-ish
    if not en[0].isupper() or len(en.split()) < 2:
        continue
    if pt == en:
        continue
    contos.append((pt, en, int(ANOS.match(yr).group(1)), i))

# dedupe por titulo PT
vistos = set()
uniq = []
for c in contos:
    k = squash(c[0])
    if k in vistos:
        continue
    vistos.add(k)
    uniq.append(c)
print(f"contos datados detectados: {len(uniq)}")

res = []
for k, (pt, en, ano, i0) in enumerate(uniq):
    f0 = uniq[k + 1][3] if k + 1 < len(uniq) else len(linhas)
    m = medir(prosa('\n'.join(linhas[i0:f0])))
    if m:
        m['titulo'] = pt
        m['titulo_en'] = en
        m['ano'] = ano
        m['linha_ini'] = i0 + 1
        m['linha_fim'] = f0
        res.append(m)

res.sort(key=lambda x: x['score_rampa'])
print(f"\n{'conto':48} {'ano':>5} {'pal':>6} {'LING':>6} {'SUB':>5} {'pr/1k':>6} {'RAMPA':>6}")
for m in res:
    print(f"{m['titulo'][:48]:48} {m['ano']:5d} {m['palavras']:6d} {m['score_ling']:6.2f} "
          f"{m['subord%']:5.1f} {m['prop_1k']:6.1f} {m['score_rampa']:6.2f}")
json.dump(res, open('/tmp/poe-contos.json', 'w'), ensure_ascii=False, indent=1)
print(f"\nJSON -> /tmp/poe-contos.json ({len(res)} contos)")
