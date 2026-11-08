#!/usr/bin/env python3
"""Cruzamento: canonicos referidos (4 listas do William) x acervo medido x estante.

Entrada:
  - data/biblioteca/canones-referidos-listas-leitura.md (as 4 listas)
  - /tmp/rampa-final.json  (prosa/teatro medidos, com RAMPA)
  - /tmp/poe-contos.json   (contos do Poe medidos)
  - data/perfil/bibliotecario/estante-william.yaml (58 da estante)
Saida: /tmp/canon-cruzamento.json + relatorio no stdout.
"""
import json, re, unicodedata, yaml, os

RAIZ = '/home/willian/study-agent'


def squash(s):
    s = ''.join(c for c in unicodedata.normalize('NFD', s) if unicodedata.category(c) != 'Mn')
    return re.sub(r'[^a-z0-9]', '', s.lower())


def toks(s):
    s = ''.join(c for c in unicodedata.normalize('NFD', s.lower()) if unicodedata.category(c) != 'Mn')
    return set(w for w in re.findall(r'[a-z0-9]+', s) if len(w) > 2)


# ---------- 1. canonicos ----------
txt = open(f'{RAIZ}/data/biblioteca/canones-referidos-listas-leitura.md', encoding='utf-8').read()
canon = {}
for linha in txt.splitlines():
    m = re.match(r'^#{2} (Lista [A-D])', linha)
    if m:
        atual = m.group(1)
        canon[atual] = []
        continue
    if 'canon' not in dir():
        continue
    m = re.match(r'^(\d+)[.)]\s+(.+)$', linha.strip())
    if m and 'atual' in dir():
        n = int(m.group(1))
        resto = m.group(2).strip()
        # separa "Titulo, Autor"
        if ',' in resto:
            titulo, autor = resto.split(',', 1)
        else:
            titulo, autor = resto, ''
        canon[atual].append({'n': n, 'titulo': titulo.strip(), 'autor': autor.strip()})

# ---------- 2. acervo medido ----------
acervo = {}
rf = json.load(open('/tmp/rampa-final.json'))
for bloco in ('prosa', 'teatro'):
    for m in rf.get(bloco, []):
        acervo[m['nome']] = {'rampa': round(0.35 * m.get('score_ling', 0) + 0.40 * m.get('frac_subord', 0) / 10 + 0.25 * m.get('prop_por_1k', 0) / 10, 2)
                             if 'score_rampa' not in m else m.get('score_rampa'),
                             'bloco': bloco, 'palavras': m.get('palavras'),
                             'arquivo': m.get('arquivo'), 'dados': m}
# score_rampa existe nos registros? calculo igual ao do agregar
for m in rf.get('prosa', []) + rf.get('teatro', []):
    if 'score_rampa' not in m:
        m['score_rampa'] = round(0.35 * m.get('score_ling', 0) + 0.40 * m.get('frac_subord', 0) / 10 + 0.25 * m.get('prop_por_1k', 0) / 10, 2)
    acervo[m['nome']]['rampa'] = m['score_rampa']

# nomes do acervo (para titulos)
nomes_acervo = sorted(acervo.keys())

# sherlock por unidade
sherlock = json.load(open('/tmp/sherlock-contos.json'))
poe = json.load(open('/tmp/poe-contos.json'))

# ---------- 3. estante ----------
est = yaml.safe_load(open(f'{RAIZ}/data/perfil/bibliotecario/estante-william.yaml'))
estante = est['livros']

# ---------- 4. matching ----------
def melhor(titulo, autor, universo):
    """universo: lista de (nome, chaves). devolve melhor score e nome."""
    tt, ta = toks(titulo), toks(autor)
    best = (0.0, None)
    for nome in universo:
        nt = toks(nome.replace('-', ' '))
        if not nt:
            continue
        cov = len(tt & nt) / max(1, len(tt))
        bonus = 0.0
        if ta and (ta & nt):
            bonus = 0.10
        s = cov + bonus
        if s > best[0]:
            best = (s, nome)
    return best

resultado = {'listas': {}, 'resumo': {}}
for nome_lista, itens in canon.items():
    linhas = []
    for it in itens:
        s, hit = melhor(it['titulo'], it['autor'], nomes_acervo)
        # estante
        se, hit_e = melhor(it['titulo'], it['autor'], [e['titulo'] for e in estante])
        reg = dict(it)
        reg['acervo_hit'] = hit if s >= 0.6 else None
        reg['acervo_score'] = round(s, 2)
        reg['acervo_rampa'] = acervo[hit]['rampa'] if (hit in acervo and s >= 0.6) else None
        reg['acervo_bloco'] = acervo[hit]['bloco'] if (hit in acervo and s >= 0.6) else None
        reg['estante_hit'] = hit_e if se >= 0.75 else None
        reg['estante_score'] = round(se, 2)
        linhas.append(reg)
    resultado['listas'][nome_lista] = linhas

# ---------- 5. resumo ----------
todos = {}
for nome_lista, itens in resultado['listas'].items():
    for it in itens:
        chave = it['titulo'].lower()
        rec = todos.setdefault(chave, {'titulo': it['titulo'], 'autor': it['autor'], 'listas': [], 'acervo': None, 'rampa': None, 'estante': False})
        rec['listas'].append(nome_lista)
        if it['acervo_hit'] and not rec['acervo']:
            rec['acervo'] = it['acervo_hit']
            rec['rampa'] = it['acervo_rampa']
            rec['bloco'] = it['acervo_bloco']
        if it['estante_hit']:
            rec['estante'] = True
resultado['unicos'] = sorted(todos.values(), key=lambda r: (r['rampa'] is None, r['rampa'] if r['rampa'] is not None else 99))
json.dump(resultado, open('/tmp/canon-cruzamento.json', 'w'), ensure_ascii=False, indent=1)

n_acervo = sum(1 for r in resultado['unicos'] if r['acervo'])
n_est = sum(1 for r in resultado['unicos'] if r['estante'])
print(f'CANONICOS UNICOS: {len(resultado["unicos"])}')
print(f'  no acervo (medido): {n_acervo}')
print(f'  so na estante (candidato a aquisicao): {sum(1 for r in resultado["unicos"] if not r["acervo"] and r["estante"])}')
print(f'  nem acervo nem estante: {sum(1 for r in resultado["unicos"] if not r["acervo"] and not r["estante"])}')
print()
print('=== NO ACERVO, por dificuldade RAMPA (menor = mais facil) ===')
for r in resultado['unicos']:
    if r['acervo']:
        print(f"  {r['rampa']:.2f}  {r['titulo'][:52]:54s} | {r['autor'][:30]:32s} | {r['listas']}")
print()
print('=== SO NA ESTANTE (nao esta no acervo do agente) ===')
for r in resultado['unicos']:
    if not r['acervo'] and r['estante']:
        print(f"  --  {r['titulo'][:52]:54s} | {r['autor'][:30]:32s} | {r['listas']}")
