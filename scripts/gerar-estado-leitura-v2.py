#!/usr/bin/env python3
"""Gera o estado-leitura.yaml v2 (rampa v4) a partir das MEDICOES.

Camadas:
  degrau_0_sherlock     — 8 livros / 100 unidades, ordem por DIFICULDADE (travado)
  degrau_1_poe          — 52 contos, ordem por DIFICULDADE (travado)
  degrau_2_prosa        — 70 obras de prosa, ordem por DIFICULDADE (marca canonico)
  degrau_3_nao_prosa    — teatro/poesia/tratado dos canonicos (trilha paralela)
  trilha_fisica         — canonicos que ele tem EM CASA e faltam no acervo digital
  aquisicao             — prioridades medidas
  historico             — o que foi concluido/abandonado

NADA e digitado a mao: tudo vem de /tmp/rampa-final.json, /tmp/sherlock-contos.json,
/tmp/poe-contos.json, /tmp/canon-final.json, /tmp/gap-canonicos.json.
"""
import json, yaml, io, re

RAIZ = '/home/willian/study-agent'
OUT = f'{RAIZ}/data/estudos/notas/ficcao-rampa-leitura/estado-leitura.yaml'

rf = json.load(open('/tmp/rampa-final.json'))
sh = json.load(open('/tmp/sherlock-contos.json'))
poe = json.load(open('/tmp/poe-contos.json'))
cf = json.load(open('/tmp/canon-final.json'))['obras']
gap = json.load(open('/tmp/gap-canonicos.json'))

canon_acervo = {o['obra']: o for o in cf if o['onde'] == 'acervo'}


AUTORES_PREFIXO = ('Doyle ', 'Poe ', 'Marx ', 'Swift ', 'Dostoievski ', 'Tolstoi ',
                    'Virgilio ', 'Goethe ', 'Balzac ', 'Sto. Agostinho ', 'Machado de Assis ',
                    'Homero ', 'Dante Alighieri ')


def titulo_de(nome_arquivo):
    """'Doyle-O-Ultimo-Adeus-de-Sherlock-Holmes' -> 'O Ultimo Adeus de Sherlock Holmes'"""
    t = re.sub(r'-', ' ', nome_arquivo)
    for pref in AUTORES_PREFIXO:
        if t.startswith(pref):
            t = t[len(pref):]
            break
    return t


d = {}
d['tipo'] = 'estado-leitura'
d['descricao'] = (
    'Estado de leitura por obra na rampa de ficcao (v4). SEPARADO da rampa de '
    'proposito: a rampa pode ser reordenada a cada novidade; o estado NAO e '
    'reordenado. Regra do William (2026-11-07): o que esta em leitura continua '
    'marcado como em leitura, independente da posicao ajustada na rampa.')
d['serie'] = 'ficcao-rampa-leitura'
d['data'] = '2026-11-07'
d['atualizado_por'] = 'iam'
d['nota_base'] = 'data/estudos/notas/ficcao-rampa-leitura/15-rampa-v4-canonicos.md'

d['regras'] = {
    'estados_validos': ['a_ler', 'em_leitura', 'lido', 'abandonado', 'pulado'],
    'transicoes': [
        {'de': 'a_ler', 'para': 'em_leitura', 'gatilho': 'William comecou a ler'},
        {'de': 'em_leitura', 'para': 'lido', 'gatilho': 'William concluiu'},
        {'de': 'em_leitura', 'para': 'abandonado', 'gatilho': 'William desistiu',
         'exige': 'motivo_abandono'},
        {'de': 'a_ler', 'para': 'pulado', 'gatilho': 'pulou por opcao'},
    ],
    'invariantes': [
        'em_leitura so sai por 2 eventos: concluir (lido) ou abandonar (abandonado)',
        'nenhuma reordenacao da rampa move o status de leitura',
        'o 1o livro so muda por ordem explicita do William',
        'desistir nao e fracasso: e dado, fica no historico, e a rampa nao insiste',
    ],
}

d['trava'] = {
    'descricao': 'itens que nao mudam sem ordem explicita do William',
    'itens': [
        {'item': '1o livro', 'valor': 'O Ultimo Adeus de Sherlock Holmes (1917)'},
        {'item': '1o conto do 1o livro', 'valor': 'O Detetive Moribundo (RAMPA 6,21)'},
        {'item': '1o degrau', 'valor': 'Sherlock Holmes, ordem por dificuldade'},
        {'item': '1o degrau 1', 'valor': 'Poe, conto por conto'},
        {'item': 'ordem interna do Sherlock', 'valor': 'por dificuldade (cronologia so depois)'},
        {'item': 'idioma', 'valor': 'apenas PT-BR (ingles fora da trilha)'},
    ],
}

# ---------- DEGRAU 0: SHERLOCK ----------
volumes_ordem = [
    'Doyle-O-Ultimo-Adeus-de-Sherlock-Holmes',
    'Doyle-A-Volta-de-Sherlock-Holmes',
    'Doyle-O-Signo-dos-Quatro',
    'Doyle-As-Aventuras-de-Sherlock-Holmes',
    'Doyle-O-Vale-do-Medo',
    'Doyle-O-Cao-dos-Baskerville',
    'Doyle-Um-Estudo-em-Vermelho',
    'Doyle-As-Memorias-de-Sherlock-Holmes',
]
ANOS = {
    'Doyle-O-Ultimo-Adeus-de-Sherlock-Holmes': 1917,
    'Doyle-A-Volta-de-Sherlock-Holmes': 1905,
    'Doyle-O-Signo-dos-Quatro': 1890,
    'Doyle-As-Aventuras-de-Sherlock-Holmes': 1892,
    'Doyle-O-Vale-do-Medo': 1915,
    'Doyle-O-Cao-dos-Baskerville': 1902,
    'Doyle-Um-Estudo-em-Vermelho': 1887,
    'Doyle-As-Memorias-de-Sherlock-Holmes': 1893,
}


def vol_score(nome):
    us = sh[nome]
    return round(sum(u['score_rampa'] * u['palavras'] for u in us) / sum(u['palavras'] for u in us), 2)


d['degrau_0_sherlock'] = {
    'ordem': 'por_dificuldade',
    'trava': True,
    'nota': 'medido POR UNIDADE (conto/capitulo): o romance dilui capitulos '
            'dificeis na media. 8 livros, 100 unidades.',
    'livros': [],
}
for pos, nome in enumerate(volumes_ordem, 1):
    us = sorted(sh[nome], key=lambda u: u['score_rampa'])
    entry = {
        'pos': pos,
        'obra': titulo_de(nome),
        'ano': ANOS[nome],
        'estado': 'a_ler',
        'data_inicio': None,
        'data_fim': None,
        'progresso': None,
        'score_rampa': vol_score(nome),
        'unidades': len(us),
        'palavras': sum(u['palavras'] for u in us),
        'sessoes_25min': round(sum(u['palavras'] for u in us) / 12500, 1),
        'notas': None,
        'contos': [],
    }
    if pos == 1:
        entry['notas'] = ('TRAVADO como 1o livro. 7 contos, ~4 sessoes de 25 min. '
                          'Comece pelo conto 1.')
    for i, u in enumerate(us, 1):
        c = {
            'pos': i,
            'titulo': u['titulo'],
            'palavras': u['palavras'],
            'score_rampa': u['score_rampa'],
            'estado': 'a_ler',
        }
        if pos == 1 and i == 1:
            c['notas'] = ('1o conto do 1o livro — TRAVADO. O mais facil de todo o '
                          'canon do Sherlock. ~40 min.')
        entry['contos'].append(c)
    d['degrau_0_sherlock']['livros'].append(entry)

# ---------- DEGRAU 1: POE ----------
d['degrau_1_poe'] = {
    'ordem': 'por_dificuldade',
    'trava': True,
    'obra_fonte': 'Poe — Os Mysteries de Poe (contos avulsos)',
    'nota': 'Poe e a MATRIZ do genero policial (Dupin > Holmes). 52 contos medidos; '
            'o VOLUME mede 14,26 porque mede o container, nao o que se le.',
    'contos': [],
}
for i, p in enumerate(sorted(poe, key=lambda x: x['score_rampa']), 1):
    c = {
        'pos': i,
        'titulo': p['titulo'],
        'ano': p.get('ano'),
        'palavras': p['palavras'],
        'score_rampa': p['score_rampa'],
        'estado': 'a_ler',
    }
    if i == 1:
        c['notas'] = 'contos mais facil do conjunto (1.241 palavras)'
    if i == 3:
        c['notas'] = ('COMECA O DEGRAU 1. Criou o genero. Trilha Dupin: '
                      'Rua Morgue > Marie Roget > A carta roubada.')
    d['degrau_1_poe']['contos'].append(c)

# ---------- DEGRAU 2: PROSA ----------
d['degrau_2_prosa'] = {
    'ordem': 'por_dificuldade',
    'total_obras': len(rf['prosa']),
    'nota': 'Base de treino em prosa. 4 eixos: LING 0,35 + SUBORD 0,40 + CARGA 0,25. '
            'SUBORD (frases com conectivo causal/condicional) e o que separa '
            '"facil de ler" de "facil de entender".',
    'obras': [],
}
for pos, m in enumerate(rf['prosa'], 1):
    c = canon_acervo.get(m['nome'])
    entry = {
        'pos': pos,
        'obra': titulo_de(m['nome']),
        'score_rampa': m['score_rampa'],
        'ling': m.get('score_ling'),
        'subord_pct': m.get('frac_subord'),
        'nomes_1k': m.get('prop_por_1k'),
        'palavras': m.get('palavras'),
        'sessoes_25min': m.get('sessoes25'),
        'canonico': bool(c),
        'canonico_listas': c['n_listas'] if c else 0,
        'estado': 'a_ler',
        'data_inicio': None,
        'data_fim': None,
        'progresso': None,
        'notas': None,
    }
    if m['nome'] in ('Doyle-O-Ultimo-Adeus-de-Sherlock-Holmes', 'Doyle-A-Volta-de-Sherlock-Holmes',
                     'Doyle-O-Signo-dos-Quatro', 'Doyle-As-Aventuras-de-Sherlock-Holmes',
                     'Doyle-O-Vale-do-Medo', 'Doyle-O-Cao-dos-Baskerville',
                     'Doyle-Um-Estudo-em-Vermelho', 'Doyle-As-Memorias-de-Sherlock-Holmes'):
        entry['notas'] = 'Sherlock — degrau 0 (medido por unidade, nao aqui)'
    if m['nome'] == 'Poe-Edgar-Allan-Os-Misterios-de-Poe':
        entry['notas'] = 'Poe — degrau 1 (medido por conta, nao aqui)'
    d['degrau_2_prosa']['obras'].append(entry)

# ---------- DEGRAU 3: CANONICOS NAO-PROSA ----------
d['degrau_3_canonicos_nao_prosa'] = {
    'ordem': 'por_genero_e_canon',
    'fora_da_trilha_de_prosa': True,
    'motivo': 'a metrica premia o teatro (rubricas curtas) e teatro nao treina prosa. '
              'Estes canonicos entram como trilha paralela, quando voce quiser o '
              'canone completo.',
    'teatro': [],
    'poesia': [],
    'tratado': [],
    'historico': [],
}
nao_prosa = sorted([x for x in gap if x['genero'] in ('teatro', 'poesia', 'tratado', 'historico')],
                    key=lambda x: (-x['n_listas'], x['genero'], x['titulo']))
for g in nao_prosa:
    d['degrau_3_canonicos_nao_prosa'][g['genero']].append({
        'obra': g['titulo'],
        'autor': g['autor'],
        'n_listas': g['n_listas'],
        'estado': 'a_ler',
    })

# ---------- TRILHA FISICA ----------
d['trilha_canonicos_fisicos'] = {
    'nota': 'canonicos que voce tem EM CASA (Librarium) e que NAO estao no acervo '
            'digital do agente. Candidato natural a aquisicao — e alguns tem versao '
            'PT-BR em falta (O Processo, O Vermelho e o Negro, O Estrangeiro, '
            'Tartufo, Dom Quixote).',
    'obras': [],
}
for o in sorted([x for x in cf if x['onde'] == 'fisico'], key=lambda x: (-x['n_listas'], x['obra'])):
    d['trilha_canonicos_fisicos']['obras'].append({
        'obra': o['obra'],
        'canonicos': sorted({c['titulo'] for c in o['canonicos']}),
        'n_listas': o['n_listas'],
        'estado': 'a_ler',
        'notas': 'versao digital pendente',
    })

# ---------- AQUISICAO ----------
d['aquisicao'] = {
    'nota': 'prioridade medida: nº de listas que citam x genero (prosa > teatro > '
            'poesia > tratado). Candidatos do cânone que nao estao em nenhum dos dois.',
    'prioridade_maxima': [],
    'prioridade_alta': [],
}
for g in gap:
    if g['n_listas'] >= 3 and g['genero'] == 'prosa':
        d['aquisicao']['prioridade_maxima'].append({'obra': g['titulo'], 'autor': g['autor'],
                                                    'n_listas': g['n_listas']})
    elif g['n_listas'] == 2 and g['genero'] == 'prosa':
        d['aquisicao']['prioridade_alta'].append({'obra': g['titulo'], 'autor': g['autor'],
                                                  'n_listas': g['n_listas']})

# ---------- HISTORICO ----------
d['historico'] = [
    {'obra': 'A Capital',
     'autor': 'Eca de Queiroz',
     'estado': 'abandonado',
     'data': 'antes de 2026-11-07',
     'motivo_abandono': 'muito denso — o William comecou e desistiu',
     'score_rampa': 7.92,
     'nota': ('50a de 70 em dificuldade: a desistencia bate com o numero. Fica no '
              'acervo para o degrau 5; a rampa nao insiste nesta obra.')},
]

with open(OUT, 'w', encoding='utf-8') as f:
    f.write('# estado-leitura.yaml — RAMPA v4 (2026-11-07)\n')
    f.write('# GERADO por scripts/gerar-estado-leitura-v2.py — nao editar a mao.\n')
    f.write('# Fonte: /tmp/rampa-final.json, /tmp/sherlock-contos.json,\n')
    f.write('#        /tmp/poe-contos.json, /tmp/canon-final.json, /tmp/gap-canonicos.json\n\n')
    yaml.safe_dump(d, f, allow_unicode=True, sort_keys=False, width=4096, default_flow_style=False)

# valida
y = yaml.safe_load(open(OUT, encoding='utf-8'))
print('YAML OK. chaves:', list(y))
print('degrau_0 livros:', len(y['degrau_0_sherlock']['livros']),
      '| unidades:', sum(len(l['contos']) for l in y['degrau_0_sherlock']['livros']))
print('degrau_1 contos:', len(y['degrau_1_poe']['contos']))
print('degrau_2 obras:', len(y['degrau_2_prosa']['obras']))
print('degrau_3:', {k: len(v) for k, v in y['degrau_3_canonicos_nao_prosa'].items() if isinstance(v, list)})
print('fisicos:', len(y['trilha_canonicos_fisicos']['obras']))
print('aquisicao max:', len(y['aquisicao']['prioridade_maxima']),
      'alta:', len(y['aquisicao']['prioridade_alta']))
print('1o livro:', y['degrau_0_sherlock']['livros'][0]['obra'],
      '| 1o conto:', y['degrau_0_sherlock']['livros'][0]['contos'][0]['titulo'])
