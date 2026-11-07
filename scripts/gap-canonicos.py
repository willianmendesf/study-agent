#!/usr/bin/env python3
"""GAP DE AQUISICAO — canonicos das 4 listas que nao estao no acervo nem na estante.

Classifica por GENERO (prosa / teatro / poesia / tratado-filosofico) e ordena
por prioridade = nº de listas que citam x genero.
Saida: /tmp/gap-canonicos.json + tabela.
"""
import json, re

CF = json.load(open('/tmp/canon-final.json'))
obras = CF['obras']

POESIA = re.compile(r'(^|\b)(poesias|poemas|odes|rimas|cantos|elegias|novos poemas|'
                    r'folhas de relva|cancoes|as iluminacoes|silvio|sonetos|'
                    r'poesia completa|lirica)\b', re.I)
TEATRO = re.compile(r'(^|\b)(hamlet|otelo|macbeth|re Lear|antigona|edipo|medeia|oresteia|'
                    r'tartufo|misantropo|rinoceronte|esperando godot|moliere|tirso|'
                    r'brecht|eugene oneill|ibsen|tchekhov|pirandello|ionesco|'
                    r'stresindberg|buechner|pinter|os noivos)\b', re.I)
TRATADO = re.compile(r'(^|\b)(apologia de socrates|banquete|menon|republica|fedro|organon|'
                      r'metafisica|etica|politica|da alma|fisica|discursos|'
                      r'meditacoes|discurso do metodo|spinoza|leibniz|heidegger|husserl|'
                      r'kant|locke|hume|berkeley|aristoteles|platao|epicteto|'
                      r'como ler um livro|em busca de sentido|rebeliao das massas|'
                      r'historia da guerra do peloponeso|memoria e reflexao)\b', re.I)
HISTORIA = re.compile(r'(^|\b)(historia de|historia da guerra|anais|decreto|tacito|'
                       r'herodoto|tucidides|declinio e queda)\b', re.I)


def genero(titulo):
    t = titulo.lower()
    if TRATADO.search(t):
        return 'tratado'
    if HISTORIA.search(t):
        return 'historico'
    if POESIA.search(t):
        return 'poesia'
    if TEATRO.search(t):
        return 'teatro'
    return 'prosa'


gap = []
for o in obras:
    if o['onde'] != 'nenhum':
        continue
    tit = o['canonicos'][0]['titulo']
    aut = o['canonicos'][0]['autor']
    g = genero(tit)
    gap.append({'titulo': tit, 'autor': aut, 'genero': g, 'n_listas': o['n_listas'],
                'variantes': sorted({c['titulo'] for c in o['canonicos']})})

# prioridade: nº de listas x genero (prosa > teatro > poesia > tratado > historico)
PESO_G = {'prosa': 3, 'teatro': 2, 'poesia': 1, 'historico': 1, 'tratado': 0}
for g in gap:
    g['prioridade'] = g['n_listas'] * 10 + PESO_G[g['genero']]

gap.sort(key=lambda x: (-x['prioridade'], x['titulo']))
json.dump(gap, open('/tmp/gap-canonicos.json', 'w'), ensure_ascii=False, indent=1)

from collections import Counter
c = Counter(g['genero'] for g in gap)
print('GAP TOTAL (canonicos em nenhum dos dois):', len(gap))
for k, v in c.most_common():
    print(f'  {k:10s} {v}')

print('\n=== PROSA — candidatos a aquisicao (prioridade >= 20 = 2+ listas) ===')
for g in [x for x in gap if x['genero'] == 'prosa']:
    marca = '***' if g['n_listas'] >= 2 else '   '
    print(f"  {marca} {g['n_listas']}x  {g['titulo'][:48]:50s} | {g['autor'][:22]}")

print('\n=== TEATRO (trilha paralela) ===')
for g in [x for x in gap if x['genero'] == 'teatro']:
    print(f"  {g['n_listas']}x  {g['titulo'][:48]:50s} | {g['autor'][:22]}")

print('\n=== POESIA ===')
for g in [x for x in gap if x['genero'] == 'poesia']:
    print(f"  {g['n_listas']}x  {g['titulo'][:48]:50s} | {g['autor'][:22]}")
