#!/usr/bin/env python3
"""Medidor da rampa de ficcao — 3 eixos + detector de idioma.

Eixos:
  LING    : dificuldade linguistica (metodo da nota 10, comparavel)
  SUBORD  : % de frases com conectivo causal/condicional (carga de inferencia)
  DENS    : nomes proprios por 1.000 palavras (carga de personagens/entidades)
  TAM     : numero de sessoes de 25 min (~12.500 palavras)

Filtro de idioma: obras em ingles sao excluidas da rampa PT-BR (o William le
apenas portugues).

NAO escreve nada no repo: saida em /tmp.
"""
import re, glob, os, json, unicodedata, random
from collections import Counter

SILABAS = re.compile(r'[aeiouy]+', re.I)

CONECT = [r'\bmas\b', r'\bque\b', r'\bembora\b', r'\bporque\b', r'\bportanto\b',
          r'\bporém\b', r'\bporem\b', r'\bpois\b', r'\bquando\b', r'\bse\b',
          r'\bcaso\b', r'\bcaso contrario\b', r'\bconquanto\b', r'\bainda que\b',
          r'\bde modo que\b', r'\bafim de\b', r'\buma vez que\b', r'\bvisto que\b',
          r'\bja que\b', r'\bdesde que\b', r'\bpara que\b', r'\bantes que\b',
          r'\bcomo que\b', r'\bconforme\b', r'\bsegundo\b', r'\bemquanto\b',
          r'\bcontanto que\b']
C = re.compile('|'.join(CONECT), re.I)

STOP = set("""a o e de do da das dos em no na nos nas um uma uns umas que se por
com nao os as ao aos ou mais como mas foi ser seu sua seus suas ele ela eles elas
isso este esta isto meu minha te tu voce voces nos nossa nosso la le les ja muito
tambem so ainda quando onde qual porque entao sim nao sou estou estao tinha foi
estar fez fazer disse ver pode ter sabia veio dar homem mulher moca rapariga velho
dona senhor senhora ate cada toda todo todos todas outro outra nenhum um
mas sim nao sera serao foi ha isso aquela aquele disse disse""".split())

# stopwords inglesas para o detector de idioma
EN_STOP = set("""the of and to in a is that it he was for on are as with his they
at be this have from or one had by word but not what all were we when your can
said there use an each which she do how their if will up other about out many
then them these so some her would make like him into time has look two more
write go see number no way could people my than first water been call who oil
its now find long down day did get come made may part over new sound take only
little work know place year live me back give most very after thing our just
name good sentence man think say great where help through much before line right
too mean old any same tell boy follow came want show also around form three small
set put end does another well large must big even such because turn here why ask
went men read need land different home us move try kind hand picture again change
off play spell air away animal house point page letter mother answer found study
still learn should world high every near add food between own below country plant
last school father keep tree never same show both paper together got group often
important until children side feet car mile night walk white sea began grow took
river four carry state once book hear stop without second later miss idea enough
eat face watch far really almost let above girl sometimes mountain cut young talk
soon list song being leave family it's body music color stand sun question fish
area mark dog horse birds problem complete room knew since ever piece told usually
didn't friends easy heard order door sure become ship top across today during
short better best however low hours black products happened whole measure remember
early waves reached listen wind rock space covered fast several hold himself
toward five step morning passed vowel true hundred against pattern numeral table
north slowly money map farm pulled draw voice seen cold cried plan notice south
sing war ground fall king town i'll unit figure certain field travel wood fire
upon done english road halt ten fly gave box finally wait correct oh quickly
person became shown minutes strong verb stars front feel fact inches street
decided contain course surface produce building ocean class note nothing rest
care door being whose ball cold cry plan though language among sail rolling
bear wonder laughed shout itself coast band desire float freezing degree
""".split())


def remove_acentos(s):
    return ''.join(c for c in unicodedata.normalize('NFD', s)
                   if unicodedata.category(c) != 'Mn')


def n_silabas(pal):
    return max(1, len(SILABAS.findall(remove_acentos(pal))))


def norm(s):
    s = unicodedata.normalize('NFC', s.lower())
    return re.sub(r'[^a-zà-ÿ]', '', s)


def texto_prosa(path):
    t = open(path, encoding='utf-8', errors='ignore').read()
    if t.startswith('---'):
        p = t.split('---', 2)
        t = p[2] if len(p) >= 3 else t
    ls = []
    for ln in t.split('\n'):
        s = ln.strip()
        if not s or s.startswith('#') or len(s) < 60:
            continue
        if re.match(r'^[\d\[\]\(\)\*·—\-\s]+$', s):
            continue
        if re.search(r'\[\d+\]|\(\d+\)', s) and len(re.findall(r'\[\d+\]|\(\d+\)', s)) > 2:
            continue
        ls.append(s)
    return ' '.join(ls)


def detectar_idioma(t):
    """Retorna ('pt'|'en'|'outro', fracao_pt, fracao_en)"""
    toks = re.findall(r"[A-Za-zÀ-ÿ]+", t.lower())
    if len(toks) < 300:
        return ('desconhecido', 0, 0)
    n_pt = sum(1 for w in toks if w in STOP)
    n_en = sum(1 for w in toks if w in EN_STOP)
    tot = n_pt + n_en
    if tot < 40:
        return ('desconhecido', 0, 0)
    return ('pt' if n_pt >= n_en else 'en', n_pt / tot, n_en / tot)


# ---- corpus de referencia (frequencia global de palavra) ----
ref = Counter()
files = [f for f in glob.glob('data/biblioteca/**/*.md', recursive=True)
         if os.path.getsize(f) > 40000]
random.seed(7)
random.shuffle(files)
for f in files[:420]:
    t = open(f, encoding='utf-8', errors='ignore').read()
    for w in re.findall(r"[A-Za-zÀ-ÿ][A-Za-zÀ-ÿ'’-]{2,}", t):
        n = norm(w)
        if len(n) >= 3:
            ref[n] += 1


def medir(path):
    t = texto_prosa(path)
    t = re.sub(r'\[\d+\]|\(\d+\)', ' ', t)
    t = re.sub(r'[—–\-]{2,}', ' ', t)
    frases = [f for f in re.split(r'(?<=[.!?…])\s+', t) if len(f.split()) >= 3]
    if not frases:
        return None
    pl = [len(f.split()) for f in frases]
    palavras = re.findall(r"[A-Za-zÀ-ÿ][A-Za-zÀ-ÿ'’-]*", t)
    n_p = len(palavras)
    if n_p < 1500:
        return None
    hard = sum(1 for p in palavras if n_silabas(p) >= 4)
    longas = sum(1 for p in palavras if len(p) >= 11)
    raros = sum(1 for w in palavras if len(norm(w)) >= 4 and ref.get(norm(w), 0) <= 5)
    cnt = Counter(norm(w) for w in palavras)
    hapax = sum(v for v in cnt.values() if v == 1)
    proprios = set()
    for w in palavras:
        lw = w.lower()
        if w[0].isupper() and lw not in STOP and len(w) >= 3 and not w.isupper():
            proprios.add(norm(w))
    sub = sum(1 for x in frases if C.search(x))
    lang, fpt, fen = detectar_idioma(t)
    return {
        'palavras': n_p,
        'pfrase': round(sum(pl) / len(pl), 1),
        '%_silabas4+': round(100 * hard / n_p, 1),
        '%_long11': round(100 * longas / n_p, 1),
        '%_raro': round(100 * raros / n_p, 1),
        '%_hapax': round(100 * hapax / n_p, 1),
        'nomes_proprios': len(proprios),
        'prop_por_1k': round(1000 * len(proprios) / n_p, 1),
        'frac_subord': round(100 * sub / len(frases), 1),
        'sessoes25': max(1, round(n_p / 12500, 1)),
        'idioma': lang,
        'frac_pt': round(fpt, 2),
        'frac_en': round(fen, 2),
    }


alvos = sorted(set(
    glob.glob('data/biblioteca/literatura-mundial-classica/**/*.md', recursive=True) +
    glob.glob('data/biblioteca/literatura-brasileira/*.md') +
    glob.glob('data/biblioteca/literatura/*.md')))

# obras que nao sao ficcao (teologia, historia da literatura, guias)
NAO_FICCAO = re.compile(
    r'Como-ler-livros|LT-Como-ler|O-Demonio-da-Teoria|Deuses-falsos|Homens-de-verdade|'
    r'Projeto-videira|Reformando-a-Familia|Terra-de-Deus|Historia-Concisa|'
    r'Historia-Literatura-Brasileira|Historia-concisa-da-Literatura|'
    r'estante-william|Nossa-Suficiencia|Com-Vergonha|'
    r'City-of-God|Confessions-Augustine', re.I)

res = []
for f in alvos:
    if NAO_FICCAO.search(f):
        continue
    try:
        m = medir(f)
    except Exception as e:
        m = None
    if m and m['palavras'] > 3000:
        m['nome'] = os.path.basename(f)[:-3]
        m['arquivo'] = f.replace('data/biblioteca/', '')
        res.append(m)


def score_ling(m):
    """Metodo da nota 10 (mesmo, para comparabilidade)."""
    sintaxe = 0.45 * m['pfrase'] + 0.35 * m['%_silabas4+'] * 1.2 + 0.20 * m['%_long11'] * 1.5
    raridade = m['%_raro'] * 2.2
    tamanho = m['palavras'] / 100000 * 8
    return round(0.35 * sintaxe + 0.40 * raridade + 0.25 * tamanho, 2)


def score_rampa(m):
    """Score COMBINADO: linguagem + inferencia + carga de personagens.

    Normaliza cada eixo para 0-10 e pondera:
      LING   (0.35) - o que o William pediu: 'linguisticamente'
      INFER  (0.40) - subordinacao (o que separa 'facil de ler' de 'facil de entender')
      CARGA  (0.25) - nomes proprios por 1k (carga intelectual)
    Menor = mais facil. Eixo DENS e o mais pesado na pratica (segundo a nota 14).
    """
    ling = score_ling(m)
    # normaliza LING de 0..~15 para 0..10
    l10 = min(10, ling / 1.2)
    i10 = min(10, m['frac_subord'] / 7.0)          # 70% -> 10
    c10 = min(10, m['prop_por_1k'] / 2.5)           # 25/1k -> 10
    return round(0.35 * l10 + 0.40 * i10 + 0.25 * c10, 2)


pt = [m for m in res if m['idioma'] == 'pt']
en = [m for m in res if m['idioma'] == 'en']
out = [m for m in res if m['idioma'] not in ('pt', 'en')]

for m in res:
    m['score_ling'] = score_ling(m)
    m['score_rampa'] = score_rampa(m)

pt.sort(key=lambda x: x['score_rampa'])
en.sort(key=lambda x: x['score_rampa'])

print("=" * 110)
print(f"ACERVO FICCAO MEDIDO: {len(res)} obras  |  PT: {len(pt)}  EN: {len(en)}  indefinido: {len(out)}")
print("=" * 110)
print(f"{'#':>3} {'obra':46} {'pal':>7} {'LING':>6} {'SUB%':>6} {'prop/1k':>8} {'sess':>5} {'RAMPA':>6}")
for i, m in enumerate(pt, 1):
    m['rank_rampa'] = i
    print(f"{i:3d} {m['nome'][:46]:46} {m['palavras']:7d} {m['score_ling']:6.2f} "
          f"{m['frac_subord']:6.1f} {m['prop_por_1k']:8.1f} {m['sessoes25']:5.1f} {m['score_rampa']:6.2f}")

print("\n--- EM INGLES (fora da rampa PT-BR) ---")
for m in en:
    print(f"    {m['nome'][:52]:52} {m['palavras']:7d} RAMPA {m['score_rampa']:6.2f}")

if out:
    print("\n--- IDIOMA INDEFINIDO ---")
    for m in out:
        print(f"    {m['nome'][:52]:52} {m['palavras']:7d} pt={m['frac_pt']} en={m['frac_en']}")

json.dump({'pt': pt, 'en': en, 'out': out}, open('/tmp/medicao-rampa.json', 'w'),
          ensure_ascii=False, indent=1)
print(f"\nJSON -> /tmp/medicao-rampa.json")
