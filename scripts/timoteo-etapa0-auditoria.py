#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Auditoria INDEPENDENTE da Etapa 0 de 1-2 Timoteo.

Recomputa do ZERO, direto das fontes, tudo o que o documento
  data/estudos/aulas/ebd-adolescentes-1-2-timoteo/01-etapa-0-leitura-propria.md
afirma. Nao usa o documento como entrada (so a forma de comparacao).

Fontes:
  data/biblioteca/biblias/grc/trparsed.txt                        (TR com Strong+morfologia)
  data/biblioteca/biblias/pt/almeida_ra.txt                        (ARC)
  data/biblioteca/referencias-biblicas/Dicionario-Biblico-Strong.md

Uso: python3 scripts/timoteo-etapa0-auditoria.py [--json]
"""
import json
import os
import re
import sys
import unicodedata
from collections import Counter, defaultdict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TRP = os.path.join(ROOT, 'data/biblioteca/biblias/grc/trparsed.txt')
PTP = os.path.join(ROOT, 'data/biblioteca/biblias/pt/almeida_ra.txt')
STP = os.path.join(ROOT, 'data/biblioteca/referencias-biblicas/Dicionario-Biblico-Strong.md')

BOOKS = (('1 Timothy', '1 Timóteo', 39832, 40441),
         ('2 Timothy', '2 Timóteo', 40442, 40908))

# verbetes cujo numero Strong nao e grego (hebraico) -> ignorar
GREEK_RANGE = (1000, 5625)


# ------------------------------------------------------------------ TR
def parse_tr():
    """-> {book_pt: {cap: {v: [{'w','g','m'}]}}}  (Strong elíptico resolvido)"""
    lines = open(TRP, encoding='utf-8', errors='replace').read().split('\n')
    out = defaultdict(lambda: defaultdict(dict))
    for en, pt, a, b in BOOKS:
        book = None
        chap = None
        # 1) junta as linhas de cada versiculo
        verses = {}          # (cap, v) -> texto
        order = []
        for ln in lines[a - 1:b]:
            s = ln.strip()
            if not s:
                continue
            if s == en:
                book = pt
                chap = None
                continue
            cm = re.match(r'^Chapter (\d+)$', s)
            if cm:
                chap = int(cm.group(1))
                continue
            vm = re.match(r'^(\d+)\s+(.*)$', s)
            if vm and book and chap is not None:
                key = (chap, int(vm.group(1)))
                verses[key] = vm.group(2)
                order.append(key)
            elif book and chap is not None and order:
                # continuacao do versiculo anterior
                verses[order[-1]] += ' ' + s
        # 2) tokeniza cada versiculo
        #    formato real: <palavra grega> [G#### ...] <TAG morfologica>
        for (c, v), txt in verses.items():
            toks = []
            raw = txt.split()
            pending = None
            gs = []
            for w in raw:
                if re.match(r'^G\d+$', w):
                    gs.append('G%d' % int(w[1:]))
                    continue
                if re.match(r'^[A-Z][A-Z0-9-]*$', w) and pending is not None:
                    # tag morfologica -> fecha a palavra
                    pending['g'] = gs[0] if gs else None
                    pending['g2'] = gs[1] if len(gs) > 1 else None
                    pending['m'] = w
                    toks.append(pending)
                    pending = None
                    gs = []
                    continue
                # nova palavra grega
                if pending is not None:
                    toks.append(pending)
                pending = {'w': w, 'g': None, 'g2': None, 'm': None}
                gs = []
            if pending is not None:
                toks.append(pending)
            out[pt][c][v] = toks
    return out


# ------------------------------------------------------------------ ARC
def parse_pt():
    """-> {book_pt: {cap: [linhas do ARC]}}  (corte por linha, nao por regex de proximo livro)"""
    lines = open(PTP, encoding='utf-8', errors='replace').read().split('\n')
    # localiza o titulo de cada livro e o proximo livro pelo titulo em caixa alta
    titulos = {}
    for i, l in enumerate(lines):
        s = l.strip()
        for _en, ptb, _a, _b in BOOKS:
            if s == ptb:
                titulos[ptb] = i
    # fim de cada livro = proxima linha que é titulo de livro em caixa alta solta
    fim = {}
    for ptb, i in titulos.items():
        for j in range(i + 1, len(lines)):
            s = lines[j].strip()
            if s and re.match(r'^[A-ZÁÉÍÓÚÂÊÔÃÕÇ][A-Za-zÀ-ú]{2,25}$', s) and not re.match(r'^(Capítulo|Capitulo|\d)', s):
                # so conta se for realmente um livro: linha vazia antes e depois
                if not lines[j - 1].strip() and (j + 1 >= len(lines) or not lines[j + 1].strip() or lines[j + 1].strip().startswith('Capítulo')):
                    fim[ptb] = j
                    break
        fim.setdefault(ptb, len(lines))
    res = {}
    for ptb, i in titulos.items():
        caps = {}
        cur = None
        for l in lines[i + 1:fim[ptb]]:
            s = l.strip()
            cm = re.match(r'^Cap[ií]tulo (\d+)$', s)
            if cm:
                cur = int(cm.group(1))
                caps[cur] = []
                continue
            if cur is not None and s:
                if re.match(r'^\d+\s*[A-ZÁÉÍÓÚÂÊÔÃÕÇ][a-zà-ú ]{3,25}$', s) and not re.match(r'^\d+\s', s):
                    continue
                caps[cur].append(s)
        res[ptb] = caps
    return res


# ------------------------------------------------------------------ Strong
def parse_strong():
    """-> {Gnum: {'defs': [..], 'raw': '..'}} para verbetes GREGOS."""
    txt = open(STP, encoding='utf-8', errors='replace').read()
    out = {}
    for m in re.finditer(r'(?m)^(\d{4})\s+([Ͱ-Ͽἀ-῿][^\n]*)$', txt):
        num = int(m.group(1))
        if not (GREEK_RANGE[0] <= num <= GREEK_RANGE[1]):
            continue
        nxt = re.search(r'(?m)^\d{4}\s+', txt[m.end():])
        body = txt[m.end(): m.end() + nxt.start()] if nxt else txt[m.end():m.end() + 3000]
        items = re.findall(r'(?m)^\s*(\d)\)\s*(.+?)\s*$', body)
        if not items:
            continue
        out['G%d' % num] = {
            'defs': [d.strip() for _, d in items],
            'head': m.group(2).strip(),
            'body': body.strip(),
        }
    return out


def norm(s):
    s = unicodedata.normalize('NFC', s).replace('\xa0', ' ')
    return re.sub(r'\s+', ' ', s).strip()


# ------------------------------------------------------------------ main
def main():
    tr = parse_tr()
    pt = parse_pt()
    sdef = parse_strong()

    R = {}

    # ---- 1. versiculos ----
    R['versiculos'] = {}
    for _en, ptb, _a, _b in BOOKS:
        caps = {c: len(v) for c, v in sorted(tr[ptb].items())}
        R['versiculos'][ptb] = {'total': sum(caps.values()), 'por_capitulo': caps}

    # ---- 2. ARC: versiculos por capitulo (conferencia cruzada) ----
    R['arc_por_capitulo'] = {}
    for ptb in tr:
        d = {}
        for c, lines in sorted(pt[ptb].items()):
            n = 0
            for l in lines:
                if re.match(r'^\d+\s', l):
                    n += 1
            d[c] = n
        R['arc_por_capitulo'][ptb] = d

    # ---- 2b. palavras do ARC (contagem real) ----
    R['arc_palavras'] = {}
    for ptb in pt:
        n = 0
        for c, ls in pt[ptb].items():
            buf = []
            for l in ls:
                if re.match(r'^\d+\s', l):
                    buf.append(re.sub(r'^\d+\s+', '', l))
                else:
                    buf.append(l)
            txt = unicodedata.normalize('NFC', ' '.join(buf))
            n += len([w for w in txt.split() if re.search(r'\w', w)])
        R['arc_palavras'][ptb] = n
    R['arc_palavras']['total'] = sum(R['arc_palavras'][b] for b in ('1 Timóteo', '2 Timóteo'))

    # ---- 3. tokens totais e formas lexicais ----
    tok_total = 0
    lemmas = set()
    verb_tokens = 0
    verb_forms = set()
    for ptb in tr:
        for c in tr[ptb].values():
            for v in c.values():
                for t in v:
                    if not t['g']:
                        continue
                    tok_total += 1
                    lemmas.add(t['g'])
                    if t['m'].startswith('V-'):
                        verb_tokens += 1
                        verb_forms.add(t['w'])
    R['tokens_com_strong'] = tok_total
    R['formas_lexicais_distintas'] = len(lemmas)
    R['verbos_tokens'] = verb_tokens
    R['verbos_formas_distintas'] = len(verb_forms)

    # ---- 4. VERBOS: finitos x infinitos x participios + IMPERATIVOS ----
    # tag: V-<tempo><voz><modo>-<pessoa><numero>   (modo: I indicativo, M imperativo,
    #       S subjuntivo, O optativo, N infinitivo, P participio)
    FINITE = set('IMSO')
    verb_tokens = 0
    verb_forms = set()
    fin_tokens = 0
    fin_forms = set()
    imp = []
    for ptb in tr:
        for c in sorted(tr[ptb]):
            for v in sorted(tr[ptb][c]):
                for t in tr[ptb][c][v]:
                    m = t['m'] or ''
                    if not m.startswith('V-'):
                        continue
                    verb_tokens += 1
                    verb_forms.add(t['w'])
                    parts = m.split('-')
                    bloco = parts[1]
                    modo = bloco[-1]
                    pn = parts[2] if len(parts) > 2 else ''
                    if modo in FINITE:
                        fin_tokens += 1
                        fin_forms.add(t['w'])
                    if modo == 'M':
                        imp.append((ptb, c, v, t['w'], t['g'], m, pn))
    R['verbos'] = {
        'tokens_totais': verb_tokens,
        'formas_distintas': len(verb_forms),
        'tokens_finitos': fin_tokens,
        'formas_finitas_distintas': len(fin_forms),
    }
    imp_2s = [x for x in imp if x[6] == '2S']
    R['imperativos'] = {
        'total': len(imp),
        'segunda_pessoa_singular': len(imp_2s),
        'por_livro': dict(Counter(x[0] for x in imp)),
        'por_capitulo': {'%s %d' % (x[0], x[1]): 0 for x in imp},
        'versiculos_com_imperativo': len({(x[0], x[1], x[2]) for x in imp}),
        'lista': ['%s %d:%d %s %s' % (x[0], x[1], x[2], x[3], x[5]) for x in imp],
    }
    pc = Counter('%s %d' % (x[0], x[1]) for x in imp)
    R['imperativos']['por_capitulo'] = dict(sorted(pc.items()))

    # ---- 4b. FALSO-CONTROLE: 2a pessoa do singular NAO-imperativo ----
    ind_2s = []
    for ptb in tr:
        for c in sorted(tr[ptb]):
            for v in sorted(tr[ptb][c]):
                for t in tr[ptb][c][v]:
                    m = t['m'] or ''
                    if not m.startswith('V-'):
                        continue
                    parts = m.split('-')
                    pn = parts[2] if len(parts) > 2 else ''
                    if pn == '2S' and parts[1][-1] != 'M':
                        ind_2s.append((ptb, c, v, t['w'], m))
    R['segunda_pessoa_singular_indicativas'] = {
        'total': len(ind_2s),
        'exemplos': ['%s %d:%d %s %s' % (x[0], x[1], x[2], x[3], x[4]) for x in ind_2s[:12]],
    }

    # ---- 5. versiculos que mencionam Jesus/Cristo/kurios ----
    def vers_com(gs):
        out = []
        for ptb in tr:
            for c in sorted(tr[ptb]):
                for v in sorted(tr[ptb][c]):
                    gl = {t['g'] for t in tr[ptb][c][v] if t['g']}
                    if gl & gs:
                        out.append((ptb, c, v))
        return out

    jesus = {'G2424'}            # Iesous
    christos = {'G5547'}         # Christos
    kurios = {'G2962'}           # kyrios
    vj = vers_com(jesus)
    vc = vers_com(christos)
    vk = vers_com(kurios)
    vj_or_vc = vers_com(jesus | christos)
    nenhum = []
    for ptb in tr:
        for c in sorted(tr[ptb]):
            for v in sorted(tr[ptb][c]):
                gl = {t['g'] for t in tr[ptb][c][v] if t['g']}
                if not (gl & (jesus | christos | kurios)):
                    nenhum.append((ptb, c, v))
    ambos = []
    for ptb in tr:
        for c in sorted(tr[ptb]):
            for v in sorted(tr[ptb][c]):
                gl = {t['g'] for t in tr[ptb][c][v] if t['g']}
                if (gl & (jesus | christos)) and (gl & kurios):
                    ambos.append((ptb, c, v))
    jc_e_k = []
    for ptb in tr:
        for c in sorted(tr[ptb]):
            for v in sorted(tr[ptb][c]):
                gl = {t['g'] for t in tr[ptb][c][v] if t['g']}
                if (gl & jesus) and (gl & christos):
                    jc_e_k.append((ptb, c, v))
    total_v = sum(R['versiculos'][b]['total'] for b in R['versiculos'])
    R['jesus_cristo_kurios'] = {
        'total_versiculos': total_v,
        'jesus': len(vj),
        'christos': len(vc),
        'jesus_ou_christos': len(vj_or_vc),
        'kurios': len(vk),
        'jesus_e_christos': len(jc_e_k),
        'jc_e_kurios': len(ambos),
        'nenhum_dos_tres': len(nenhum),
        'pct_nenhum': round(100.0 * len(nenhum) / total_v, 1),
        'pct_iesous': round(100.0 * len(vj) / total_v, 1),
        'pct_christos': round(100.0 * len(vc) / total_v, 1),
        'pct_kurios': round(100.0 * len(vk) / total_v, 1),
    }

    # ---- 6. contagem por Strong (para conferir a tabela de lexico) ----
    cnt_g = Counter()
    loc_g = defaultdict(list)
    for ptb in tr:
        for c in sorted(tr[ptb]):
            for v in sorted(tr[ptb][c]):
                seen = set()
                for t in tr[ptb][c][v]:
                    if t['g']:
                        cnt_g[t['g']] += 1
                        if t['g'] not in seen:
                            seen.add(t['g'])
                            loc_g[t['g']].append('%s %d:%d' % (ptb, c, v))
    R['contagem_por_strong'] = {k: {'n': cnt_g[k],
                                     'n_versiculos': len(loc_g[k]),
                                     'locais': loc_g[k]}
                                for k in sorted(cnt_g, key=lambda x: -cnt_g[x])}

    # ---- 7. verbetes Strong: definicao completa ----
    R['verbetes'] = {}
    for g in sorted(sdef):
        R['verbetes'][g] = {'defs': sdef[g]['defs'], 'head': sdef[g]['head']}

    if '--json' in sys.argv:
        print(json.dumps(R, ensure_ascii=False, indent=1))
        return

    # ---- relatorio ----
    print('=' * 70)
    print('AUDITORIA INDEPENDENTE — Etapa 0 de 1-2 Timoteo')
    print('=' * 70)
    print('\n[1] VERSICULOS (TR)')
    for b, d in R['versiculos'].items():
        print('  %s: %d versiculos | %s' % (b, d['total'], d['por_capitulo']))
    print('\n[2] VERBOS (tokens / formas)')
    print('  tokens verbais: %d | formas distintas: %d | tokens com Strong: %d'
          % (R['verbos_tokens'], R['verbos_formas_distintas'], R['tokens_com_strong']))
    print('  formas lexicais distintas (Strong): %d' % R['formas_lexicais_distintas'])
    print('\n[3] IMPERATIVOS (modo M na tag morfologica)')
    i = R['imperativos']
    print('  total: %d | 2a pessoa do singular: %d | por livro: %s'
          % (i['total'], i['segunda_pessoa_singular'], i['por_livro']))
    print('  versiculos com imperativo: %d' % i['versiculos_com_imperativo'])
    print('  FALSO-CONTROLE: formas 2S nao-imperativas (indicativas): %d'
          % R['segunda_pessoa_singular_indicativas']['total'])
    print('\n[4] JESUS / CRISTO / KURIOS')
    for k, v in R['jesus_cristo_kurios'].items():
        print('  %s: %s' % (k, v))
    print('\n[5] CONTAGENS CHAVE POR STRONG (para conferir a tabela de lexico)')
    for g in ('G3852', 'G3056', 'G4102', 'G26', 'G2150', 'G1108', 'G1922', 'G225',
              'G1985', 'G1984', 'G1249', 'G1247', 'G1248', 'G3623', 'G3624',
              'G3908', 'G3872', 'G3866', 'G652', 'G4151', 'G2316', 'G2962', 'G5547',
              'G2424', 'G1228', 'G4567', 'G1985', 'G5023', 'G3306', 'G665', 'G5279'):
        c = R['contagem_por_strong'].get(g)
        if c:
            print('  %-7s %3d  %s' % (g, c['n'], ' '.join(c['locais'][:6])))
        else:
            print('  %-7s   0  (ausente)' % g)
    print('\n[6] VERBETES STRONG — completeza das definicoes')
    trunc = 0
    for g, v in R['verbetes'].items():
        for d in v['defs']:
            if not d.endswith(('.', ':', ';')):
                trunc += 1
    print('  verbetes gregos no dicionario: %d | definicoes truncadas na fonte: %d'
          % (len(R['verbetes']), trunc))


if __name__ == '__main__':
    main()
