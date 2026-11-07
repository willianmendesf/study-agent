#!/usr/bin/env python3
"""RAMPA v4 — cruzamento final dos canonicos (4 listas) com o acervo medido.

Correcoes em relacao a v2:
  - "O Capital, Marx" (lista B #87) nao tem virgula: separador tambem e " - ",
    e o "Marx - O Capital" caia em "A-Capital-Eca-de-Queiroz". Agora o autor
    e verificado contra o nome do arquivo.
  - obra sem autor nomeado (ex.: "Machado de Assis", lista D #100) e
    AMBIGUA: exige casamento exato do titulo, nunca fuzzy.
Saida: /tmp/canon-final.json (dados) + relatorio.
"""
import json, re, unicodedata

RAIZ = '/home/willian/study-agent'

IGNORADOS = {
    'de', 'do', 'da', 'dos', 'das', 'e', 'o', 'a', 'um', 'uma', 'von', 'van',
    'james', 'william', 'john', 'charles', 'george', 'henry', 'jean', 'luis',
    'luiz', 'eduardo', 'maria', 'antonio', 'anton', 'd', 's', 'st', 'jr', 'sr',
    'di', 'del', 'la', 'le', 'ter', 'of',
}


def nk(s):
    s = ''.join(c for c in unicodedata.normalize('NFD', str(s).lower()) if unicodedata.category(c) != 'Mn')
    return re.sub(r'[^a-z0-9]', '', s)


def toks(s):
    s = ''.join(c for c in unicodedata.normalize('NFD', str(s).lower()) if unicodedata.category(c) != 'Mn')
    return set(w for w in re.findall(r'[a-z0-9]+', s) if len(w) > 2)


def sobrenomes(autor):
    a = re.sub(r'\b(de|da|do|dos|das|e|vander|von|van|der|den|de la|le|la|di|del)\b', ' ', autor, flags=re.I)
    return [p for p in re.findall(r"[A-Za-zÀ-ÿ']+", a) if len(p) > 2 and p.lower() not in IGNORADOS]


def casa_autor(autor_canon, texto):
    if not autor_canon.strip():
        return None, 0.0
    sobr = sobrenomes(autor_canon)
    if not sobr:
        return None, 0.0
    alvo = {nk(t) for t in toks(texto.replace('-', ' '))}
    hits = [s for s in sobr if nk(s) in alvo]
    return (len(hits) > 0), len(hits) / len(sobr)


def separar(resto):
    """separa titulo e autor: por virgula, ou por ' - ' quando nao ha virgula."""
    resto = resto.strip()
    if ',' in resto:
        a, b = resto.split(',', 1)
        return a.strip(), b.strip()
    if ' - ' in resto:
        a, b = resto.split(' - ', 1)
        return b.strip(), a.strip()   # "Marx - O Capital" -> titulo=O Capital, autor=Marx
    return resto, ''


# ---------- canonicos ----------
txt = open(f'{RAIZ}/data/biblioteca/canones-referidos-listas-leitura.md', encoding='utf-8').read()
canon, atual = {}, None
for linha in txt.splitlines():
    m = re.match(r'^#{2} (Lista [A-D])', linha)
    if m:
        atual = m.group(1)
        canon[atual] = []
        continue
    m = re.match(r'^(\d+)[.)]\s+(.+)$', linha.strip())
    if m and atual:
        tit, aut = separar(m.group(2))
        canon[atual].append({'n': int(m.group(1)), 'titulo': tit, 'autor': aut})

# ---------- acervo medido ----------
rf = json.load(open('/tmp/rampa-final.json'))
acervo = {}
for bloco in ('prosa', 'teatro'):
    for m in rf.get(bloco, []):
        acervo[m['nome']] = {'rampa': m.get('score_rampa'), 'bloco': bloco, 'palavras': m.get('palavras'),
                             'arquivo': m.get('arquivo'), 'sessoes': m.get('sessoes25')}

# ---------- librarium ----------
lib = json.load(open('/tmp/librarium_all.json'))
fisicos = []
for b in lib:
    aut = ''
    for c in b.get('contributors') or []:
        if c.get('role') == 'author':
            aut = c.get('name', '')
    fisicos.append({'titulo': b.get('title', ''), 'autor': aut, 'id': b.get('id')})


def score_titulo(alvo, nome):
    tt = toks(alvo)
    nt = toks(nome.replace('-', ' '))
    if not tt or not nt:
        return 0.0
    cov = len(tt & nt) / len(tt)
    longos = [t for t in tt if len(t) >= 5]
    cov2 = (len(set(longos) & nt) / len(longos)) if longos else cov
    return 0.55 * cov + 0.45 * cov2


unicos = {}
for lst, itens in canon.items():
    for it in itens:
        chave = nk(it['titulo']) + '|' + nk(re.sub(r'^(de|do|da|dos|das|d)\s+', '', it['autor'], flags=re.I))
        rec = unicos.setdefault(chave, {'titulo': it['titulo'], 'autor': it['autor'],
                                        'listas': [], 'variantes': []})
        rec['listas'].append(lst)
        rec['variantes'].append(it['titulo'])

for rec in unicos.values():
    best = (0.0, None)
    for v in rec['variantes']:
        for nome in acervo:
            s = score_titulo(v, nome)
            ok, frac = casa_autor(rec['autor'], nome)
            if ok is False:
                continue
            if ok is None:                       # obra sem autor: exige casamento forte
                if s < 0.95:
                    continue
            else:
                s = s * (0.5 + 0.5 * frac)
            if s > best[0]:
                best = (s, nome)
    rec['acervo_score'] = round(best[0], 2)
    rec['acervo'] = best[1] if best[0] >= 0.62 else None
    rec['rampa'] = acervo[rec['acervo']]['rampa'] if rec['acervo'] else None
    rec['bloco'] = acervo[rec['acervo']]['bloco'] if rec['acervo'] else None
    rec['arquivo'] = acervo[rec['acervo']]['arquivo'] if rec['acervo'] else None
    rec['palavras'] = acervo[rec['acervo']]['palavras'] if rec['acervo'] else None
    rec['sessoes'] = acervo[rec['acervo']]['sessoes'] if rec['acervo'] else None

    bestf = (0.0, None)
    for v in rec['variantes']:
        for f in fisicos:
            s = score_titulo(v, f['titulo'])
            ok, frac = casa_autor(rec['autor'], f['titulo'] + ' ' + f['autor'])
            if ok is False:
                continue
            if ok is None:
                if s < 0.95:
                    continue
            else:
                s = s * (0.5 + 0.5 * frac)
            if s > bestf[0]:
                bestf = (s, f['titulo'])
    rec['fisico_score'] = round(bestf[0], 2)
    rec['fisico'] = bestf[1] if bestf[0] >= 0.80 else None
    rec['em_lista'] = len(rec['listas'])
    rec['ambigua'] = not rec['autor'].strip()

# ---------- agrupamento final: uma linha por OBRA (acervo ou fisico) ----------
obras = {}
for rec in unicos.values():
    if rec['acervo']:
        chave = ('acervo', rec['acervo'])
    elif rec['fisico']:
        chave = ('fisico', rec['fisico'])
    else:
        chave = ('nenhum', rec['titulo'] + '|' + rec['autor'])
    o = obras.setdefault(chave, {'obra': chave[1], 'onde': chave[0], 'rampa': rec['rampa'],
                                 'bloco': rec['bloco'], 'arquivo': rec['arquivo'],
                                 'palavras': rec['palavras'], 'sessoes': rec['sessoes'],
                                 'canonicos': []})
    o['canonicos'].append({'titulo': rec['titulo'], 'autor': rec['autor'], 'listas': rec['listas']})
for o in obras.values():
    o['n_listas'] = len(set(sum([c['listas'] for c in o['canonicos']], [])))
    o['n_canonicos'] = len(o['canonicos'])

U = sorted(obras.values(), key=lambda r: (r['onde'] != 'acervo', r['rampa'] is None, r['rampa'] or 99, r['obra']))
json.dump({'obras': U, 'unicos': list(unicos.values())}, open('/tmp/canon-final.json', 'w'), ensure_ascii=False, indent=1)
print(f"OBRAS AGRUPADAS: {len(U)}")
print(f"  no acervo medido : {sum(1 for r in U if r['onde']=='acervo')}")
print(f"  so no fisico      : {sum(1 for r in U if r['onde']=='fisico')}")
print(f"  em nenhum         : {sum(1 for r in U if r['onde']=='nenhum')}")


print('\n=== A) NO ACERVO, por RAMPA ===')
for r in U:
    if r['onde'] == 'acervo':
        can = ', '.join(sorted({c['titulo'] for c in r['canonicos']}))[:44]
        print(f"  {r['rampa']:5.2f} {r['bloco'][:6]:6s} {r['obra'][:40]:42s} <- '{can}' ({r['n_listas']} listas)")

print('\n=== B) SO NO FISICO ===')
for r in U:
    if r['onde'] == 'fisico':
        can = ', '.join(sorted({c['titulo'] for c in r['canonicos']}))[:44]
        print(f"  --   '{can}' -> fisico '{r['obra'][:34]}' ({r['n_listas']} listas)")

print('\n=== C) EM NENHUM — por n de listas (top 45) ===')
for r in sorted([r for r in U if r['onde'] == 'nenhum'], key=lambda r: (-r['n_listas'], r['obra']))[:45]:
    can = ', '.join(sorted({c['titulo'] for c in r['canonicos']}))[:46]
    print(f"  {r['n_listas']}x  {can:48s} | {r['canonicos'][0]['autor'][:20]}")
