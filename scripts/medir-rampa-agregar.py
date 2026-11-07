#!/usr/bin/env python3
"""RAMPA FINAL — versao consolidada.

Filtros aplicados (todos medidos, nao opinados):
  1. IDIOMA: so PT-BR (detector de 6 idiomas, scripts/detectar-idioma.py).
     O detector anterior classificou 'Germinal' (FR) e 'A Religiosa' (ES)
     como portugues.
  2. INTEGRIDADE: fora arquivos corrompidos (bytes nulos / traceback do
     extrator / so a folha de rosto).
  3. GENERO: teatro (drama) sai da trilha de PROSA — a metrica premia o
     teatro (rubricas curtas) e teatro nao treina prosa.
  4. DEDUPE por titulo normalizado.
  5. Sherlock = DEGRAU 0, ordenado por DIFICULDADE das unidades.
     Poe (matriz do genero) vem logo depois, tambem por dificuldade.

Saida: /tmp/rampa-final.json + tabela no stdout.
"""
import json, re, unicodedata, os

def squash(s):
    s = ''.join(c for c in unicodedata.normalize('NFD', s) if unicodedata.category(c) != 'Mn')
    return re.sub(r'[^a-z]', '', s.lower())

ACERVO = json.load(open('/tmp/medicao-rampa.json'))
SHERLOCK = json.load(open('/tmp/sherlock-contos.json'))
POE = json.load(open('/tmp/poe-contos.json'))
IDIOMAS = json.load(open('/tmp/idiomas.json'))

# integridade verificada nesta sessao (bytes de prosa / tracebacks)
CORROMPIDOS = {
    'Cervantes-Dom-Quixote.md': '104 tracebacks do extrator - nao e o Dom Quixote',
    'Graciliano-Ramos-Vidas-Secas.md': '279 bytes - so a capa',
    'Machado-Assis-Dom-Casmurro.md': '15 KB - so traceback',
    'idiota-fiodor-dostoievski.md': '1,6 MB de bytes nulos',
    'anna-karenina-liev-tolstoi.md': '1,9 MB de bytes nulos',
    'The-Charles-Dickens-Collection-Volume-One-Oliver-Twist-Great-Expectations-and-Bleak-House.md': '81 KB - so o CSS do EPUB',
}

TEATRO = ['Casa-de-Bonecas', 'escola-mulheres', 'As-Tres-Irmas', 'Maria-Stuart',
          'Longa-Jornada-Noite-Adentro', 'A-Morte-em-Veneza', 'morte-veneza',
          'Nostradamus', '1919-john-dos-passos', 'As-Flores-do-Mal', 'Fausto-Johann',
          'Dom-Quixote', 'O-Demonio-da-Teoria']


def eh_teatro(nome):
    n = nome.lower()
    return any(t.lower() in n for t in TEATRO)


nomes_canon = {m['nome']: m for m in ACERVO['pt'] + ACERVO['en']}
selecionadas, descartadas = [], []
for nome, info in IDIOMAS.items():
    m = nomes_canon.get(nome)
    if m is None:
        continue
    if nome in CORROMPIDOS:
        descartadas.append((nome, 'CORROMPIDO: ' + CORROMPIDOS[nome]))
        continue
    if info['idioma'] != 'pt':
        descartadas.append((nome, f"IDIOMA {info['idioma'].upper()} ({info['pct'][info['idioma']]}%)"))
        continue
    selecionadas.append(m)

print(f"104 avaliadas -> {len(selecionadas)} PT-BR integras | {len(descartadas)} descartadas")
print("\nDESCARTADAS:")
for n, r in sorted(descartadas):
    print(f"  - {n[:58]:60} {r}")


def dedupe(lst):
    """dedupe por titulo normalizado, ignorando artigo inicial ('A ', 'O ')
    e sufixo de autor repetido ('-Nathaniel-Hawthorne' duas vezes)."""
    def chave(m):
        n = squash(m['nome'])
        for pref in ('ao', 'a', 'o', 'as', 'os'):
            if n.startswith(pref) and len(n) > len(pref) + 3:
                n = n[len(pref):]
                break
        # corta o sufixo de autor repetido (o mesmo nome 2x no acervo)
        for sep in ('hawthorne', 'svevo', 'james', 'tolstoi', 'dostoievski'):
            if n.count(sep) >= 2:
                i = n.find(sep)
                n = n[:i + len(sep)]
                break
        return n
    v = {}
    for m in lst:
        k = chave(m)
        if k not in v or m['score_rampa'] < v[k]['score_rampa']:
            v[k] = m
    return sorted(v.values(), key=lambda x: x['score_rampa'])


prosa = dedupe([m for m in selecionadas if not eh_teatro(m['nome'])])
teatro = dedupe([m for m in selecionadas if eh_teatro(m['nome'])])
ingles = dedupe([m for m in ACERVO['en']])

SHERLOCK_ORDEM = [
    'Doyle-Um-Estudo-em-Vermelho', 'Doyle-O-Signo-dos-Quatro',
    'Doyle-O-Cao-dos-Baskerville', 'Doyle-O-Vale-do-Medo',
    'Doyle-As-Aventuras-de-Sherlock-Holmes', 'Doyle-As-Memorias-de-Sherlock-Holmes',
    'Doyle-A-Volta-de-Sherlock-Holmes', 'Doyle-O-Ultimo-Adeus-de-Sherlock-Holmes',
]
sherlock = []
for k in SHERLOCK_ORDEM:
    u = SHERLOCK.get(k, [])
    if not u:
        continue
    tot = sum(x['palavras'] for x in u)
    sherlock.append({
        'nome': k.replace('Doyle-', '').replace('-', ' '),
        'unidades': u, 'n_unidades': len(u), 'palavras': tot,
        'score_rampa': round(sum(x['score_rampa'] * x['palavras'] for x in u) / tot, 2),
        'score_ling': round(sum(x['score_ling'] * x['palavras'] for x in u) / tot, 2),
        'conta_mais_facil': u[0]['titulo'], 'conta_mais_dificil': u[-1]['titulo'],
        'palavras_min': min(x['palavras'] for x in u),
        'palavras_max': max(x['palavras'] for x in u),
    })
sherlock.sort(key=lambda x: x['score_rampa'])

poe_sorted = sorted(POE, key=lambda x: x['score_rampa'])
poe = {
    'nome': 'Poe - Os Mysteries de Poe (contos avulsos)',
    'n_contos': len(poe_sorted), 'unidades': poe_sorted,
    'score_rampa': round(sum(c['score_rampa'] for c in poe_sorted) / len(poe_sorted), 2),
    'conta_mais_facil': poe_sorted[0]['titulo'],
    'conta_mais_dificil': poe_sorted[-1]['titulo'],
    'palavras_mediana': sorted(c['palavras'] for c in poe_sorted)[len(poe_sorted) // 2],
}


def fmt(m):
    return (f"{m['nome'][:42]:44} pal={m['palavras']:7d} LING={m.get('score_ling',0):5.2f} "
            f"SUB={m.get('frac_subord', m.get('subord%',0)):5.1f} "
            f"pr/1k={m.get('prop_por_1k', m.get('prop_1k',0)):5.1f} RAMPA={m['score_rampa']:5.2f}")


print("\n" + "=" * 116)
print("DEGRAU 0 - SHERLOCK (ordem por DIFICULDADE das unidades)")
print("=" * 116)
for i, s in enumerate(sherlock, 1):
    print(f"{i:3d} {s['nome'][:42]:44} RAMPA={s['score_rampa']:5.2f} LING={s['score_ling']:5.2f} "
          f"| {s['n_unidades']:2d}u | {s['palavras']:6d} pal | mais facil: {s['conta_mais_facil'][:32]}")

print("\n" + "=" * 116)
print("DEGRAU 1 - POE (contos avulsos, ordem por dificuldade) - 15 mais faceis")
print("=" * 116)
for i, c in enumerate(poe_sorted[:15], 1):
    print(f"{i:3d} {c['titulo'][:44]:46} ({c['ano']}) pal={c['palavras']:6d} "
          f"LING={c['score_ling']:5.2f} SUB={c['subord%']:5.1f} pr/1k={c['prop_1k']:5.1f} RAMPA={c['score_rampa']:5.2f}")

print("\n" + "=" * 116)
print(f"DEGRAU 2+ - PROSA PT-BR ({len(prosa)} obras) - 30 mais faceis")
print("=" * 116)
for i, m in enumerate(prosa[:30], 1):
    print(f"{i:3d} {fmt(m)}")

print("\n" + "=" * 116)
print(f"TRILHA PARALELA - TEATRO ({len(teatro)})")
print("=" * 116)
for i, m in enumerate(teatro, 1):
    print(f"{i:3d} {fmt(m)}")

print("\nEM INGLES (fora da rampa - o ingles do William e' pessimo):")
for m in ingles:
    print(f"    {m['nome'][:56]:58} RAMPA={m['score_rampa']:5.2f}")

json.dump({'prosa': prosa, 'teatro': teatro, 'sherlock': sherlock, 'poe': poe,
           'ingles': ingles, 'descartadas': descartadas},
          open('/tmp/rampa-final.json', 'w'), ensure_ascii=False, indent=1)
print("\nJSON -> /tmp/rampa-final.json")
