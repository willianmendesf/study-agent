#!/usr/bin/env python3
"""Mede a dificuldade UNIDADE A UNIDADE dos livros do Sherlock Holmes.

Unidade = conto (colecoes) OU capitulo (romances).

Os EPUBs da Zahar fragmentam TUDO:
  - o rotulo do sumario vem em 2 linhas ('S' + 'UMARIO')
  - os titulos vem em small-caps com quebra no meio da palavra
    ('E' / 'SCANDALO NA' / 'B' / 'OEMIA')
  - o sumario pode ter o titulo partido em 2 linhas
    ('A Tragedia do' + 'Gloria Scott')
  - a apresentacao vem em 2 linhas ('A' + 'PRESENTACAO')

Estrategia: faz um SQUASH GLOBAL do arquivo (só letras, sem acento) com um
mapa char->linha. Assim qualquer rotulo fragmentado casa como um todo, e a
posicao no squash vira linha no arquivo original.

NAO escreve nada no repo. Saida: /tmp/sherlock-contos.json
"""
import re, glob, os, json, unicodedata, random
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
if os.path.exists(CACHE):
    ref = Counter(json.load(open(CACHE)))
else:
    ref = Counter()
    files = [f for f in glob.glob('data/biblioteca/**/*.md', recursive=True) if os.path.getsize(f) > 40000]
    random.seed(7)
    random.shuffle(files)
    for f in files[:420]:
        t = open(f, encoding='utf-8', errors='ignore').read()
        for w in re.findall(r"[A-Za-zÀ-ÿ][A-Za-zÀ-ÿ'’-]{2,}", t):
            n = norm(w)
            if len(n) >= 3:
                ref[n] += 1
    json.dump(dict(ref), open(CACHE, 'w'))

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


ROMAN = re.compile(r'^([IVXLC]{1,5})[\.\)]\s+(.+)$')
ROMAN_SO = re.compile(r'^[IVXLC]{1,5}$')
CONNECT = re.compile(r'\b(do|da|de|dos|das|no|na|nos|nas|e|a|o|em|y)$', re.I)
FIM_BLOCO = ('apresentacao', 'preface', 'fonte', 'sobreoautor', 'introducao', 'notadoeditor')


def squash_com_mapa(linhas, inicio=0):
    buf, mapa = [], []
    for i in range(inicio, len(linhas)):
        for ch in ra(linhas[i]).lower():
            if ch.isalpha() and ch.isascii():
                buf.append(ch)
                mapa.append(i)
    return ''.join(buf), mapa


def main():
    ARQUIVOS = sorted(glob.glob('data/biblioteca/literatura-mundial-classica/portugues/Doyle-*.md'))
    resultado = {}
    for arq in ARQUIVOS:
        nome = os.path.basename(arq)[:-3]
        linhas = open(arq, encoding='utf-8', errors='ignore').read().split('\n')
        buf, mapa = squash_com_mapa(linhas)

        # 1) achar o sumario
        p = -1
        for marker in ('sumario', 'umario'):
            q = buf.find(marker)
            if q >= 0 and mapa[q] < 250:
                p = q
                break
        if p < 0:
            print(f"\n=== {nome}\n    [sumario nao encontrado]")
            continue
        line_sum_end = mapa[p + len(marker) - 1]

        # 2) achar o fim do bloco do sumario (apresentacao / prefacio / fonte)
        fim_idx = len(buf)
        for marker in FIM_BLOCO:
            q = buf.find(marker, p + 8)
            if q >= 0:
                fim_idx = min(fim_idx, q)
        line_fim = mapa[fim_idx] if fim_idx < len(buf) else len(linhas)

        # 3) extrair entradas do sumario
        brutos = [l.strip() for l in linhas[line_sum_end + 1:line_fim] if l.strip()]
        entradas = []
        i = 0
        while i < len(brutos):
            s = brutos[i]
            if squash(s).startswith(FIM_BLOCO):
                i += 1
                continue
            m = ROMAN.match(s)
            if m:
                entradas.append(m.group(2).strip())
                i += 1
                continue
            if ROMAN_SO.match(s):
                entradas.append(s)
                i += 1
                continue
            t = s
            if i + 1 < len(brutos) and CONNECT.search(t):
                prox = brutos[i + 1]
                if not ROMAN_SO.match(prox) and prox[:1].isupper() and len(prox) < 60:
                    t = t + ' ' + prox
                    i += 1
            entradas.append(t)
            i += 1

        print(f"\n=== {nome}")
        print(f"    sumario: linhas {line_sum_end+1}-{line_fim} | {len(entradas)} entradas")

        # 4) casar cada entrada no corpo (apos o sumario)
        corpo, cmap = squash_com_mapa(linhas, line_fim)
        achados = []
        cursor = 0
        for t in entradas:
            alvo = squash(t)
            if len(alvo) < 6:
                continue
            q = corpo.find(alvo, cursor)
            if q < 0:
                q = corpo.find(alvo)
            if q < 0:
                print(f"      ? NAO ACHADO: {t[:60]}")
                continue
            achados.append((t, cmap[q]))
            cursor = q + len(alvo)

        # 5) medir
        contos = []
        for k, (t, i0) in enumerate(achados):
            f0 = achados[k + 1][1] if k + 1 < len(achados) else len(linhas)
            m = medir(prosa('\n'.join(linhas[i0:f0])))
            if m:
                m['titulo'] = t
                m['linha_ini'] = i0 + 1
                m['linha_fim'] = f0
                contos.append(m)
        contos.sort(key=lambda x: x['score_rampa'])
        print(f"    {len(contos)}/{len(entradas)} unidades medidas")
        for c in contos:
            print(f"      {c['titulo'][:50]:50} pal={c['palavras']:6d} LING={c['score_ling']:5.2f} "
                  f"SUB={c['subord%']:5.1f} pr/1k={c['prop_1k']:5.1f} RAMPA={c['score_rampa']:5.2f}")
        resultado[nome] = contos

    json.dump(resultado, open('/tmp/sherlock-contos.json', 'w'), ensure_ascii=False, indent=1)
    print("\nJSON -> /tmp/sherlock-contos.json")


if __name__ == '__main__':
    main()
