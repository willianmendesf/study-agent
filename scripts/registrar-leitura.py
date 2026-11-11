#!/usr/bin/env python3
"""registrar-leitura.py — registra o estado de leitura na rampa de ficcao.

Por que existe: `estado-leitura.yaml` e GERADO por `gerar-estado-leitura-v2.py`
e diz "nao editar a mao". Mas o gerador le `/tmp/*.json` que nao sobrevivem
a um reboot — roda-lo apagaria todo o estado real. Entao este script faz o
CONTRARIO: e a fonte de verdade do que o William leu.

Regra (2026-11-07, do William): "em_leitura so sai por 2 eventos: concluir
(lido) ou abandonar (abandonado)". Desistir nao e fracasso — e dado, fica no
historico, e a rampa nao insiste.

Uso:
  scripts/registrar-leitura.py --obra "O Ultimo Adeus de Sherlock Holmes" \
      --unidade "Vila Glicinia" --estado lido [--data 2026-11-11] [--nota "..."]
  scripts/registrar-leitura.py --obra "A Capital" --estado abandonado \
      --motivo "muito denso" [--data 2026-11-11]
  scripts/registrar-leitura.py --listar
"""
import argparse
import datetime
import io
import shutil
import sys
from pathlib import Path

import yaml

RAIZ = Path('/home/willian/study-agent')
YAML_PATH = RAIZ / 'data/estudos/notas/ficcao-rampa-leitura/estado-leitura.yaml'
REGISTROS = RAIZ / 'data/perfil/bibliotecario/leitura-registros.yaml'

VALIDOS = ('a_ler', 'em_leitura', 'lido', 'abandonado', 'pulado')


def normalizar(s):
    """Compara titulos ignorando acento, caixa e pontuacao."""
    import unicodedata
    s = unicodedata.normalize('NFKD', str(s or ''))
    s = ''.join(c for c in s if not unicodedata.combining(c))
    return ''.join(c for c in s.lower() if c.isalnum() or c == ' ').strip()


def achar_livro(y, nome):
    alvo = normalizar(nome)
    for l in y.get('degrau_0_sherlock', {}).get('livros', []):
        if normalizar(l.get('obra')) == alvo:
            return l
    for l in y.get('degrau_0_sherlock', {}).get('livros', []):
        if alvo and alvo in normalizar(l.get('obra')):
            return l
    return None


def achar_conto(livro, nome):
    alvo = normalizar(nome)
    for c in livro.get('contos', []):
        if normalizar(c.get('titulo')) == alvo:
            return c
    for c in livro.get('contos', []):
        if alvo and alvo in normalizar(c.get('titulo')):
            return c
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--obra')
    ap.add_argument('--unidade', help='titulo do conto/capitulo (unidade)')
    ap.add_argument('--estado', choices=VALIDOS)
    ap.add_argument('--data')
    ap.add_argument('--nota')
    ap.add_argument('--motivo', help='obrigatorio para estado=abandonado')
    ap.add_argument('--listar', action='store_true')
    args = ap.parse_args()

    if args.listar:
        y = yaml.safe_load(YAML_PATH.read_text(encoding='utf-8'))
        for l in y.get('degrau_0_sherlock', {}).get('livros', []):
            print(f"{l['pos']}. {l['obra']} [{l['estado']}] "
                  f"({len([c for c in l.get('contos', []) if c.get('estado') == 'lido'])}/"
                  f"{len(l.get('contos', []))} contos lidos)")
            for c in l.get('contos', []):
                if c.get('estado') != 'a_ler':
                    print(f"     - {c['titulo']}: {c['estado']}"
                          + (f" ({c.get('data_fim')})" if c.get('data_fim') else ''))
        return

    if not args.obra or not args.estado:
        ap.error('--obra e --estado sao obrigatorios (ou use --listar)')

    data = args.data or datetime.date.today().isoformat()
    y = yaml.safe_load(YAML_PATH.read_text(encoding='utf-8'))

    # backup datado
    bak = YAML_PATH.with_suffix(f'.yaml.bak-{data}-{args.estado}')
    shutil.copy2(YAML_PATH, bak)

    livro = achar_livro(y, args.obra)
    if not livro:
        print(f'✗ obra nao encontrada: {args.obra}', file=sys.stderr)
        sys.exit(1)

    alvo = None
    if args.unidade:
        alvo = achar_conto(livro, args.unidade)
        if not alvo:
            print(f'✗ unidade nao encontrada: {args.unidade}', file=sys.stderr)
            sys.exit(1)
        alvo['estado'] = args.estado
        alvo['data_fim'] = data if args.estado in ('lido', 'abandonado') else None
        alvo['data_inicio'] = alvo.get('data_inicio') or data
        if args.nota:
            alvo['notas'] = args.nota
    else:
        livro['estado'] = args.estado
        livro['data_fim'] = data if args.estado in ('lido', 'abandonado') else None
        livro['data_inicio'] = livro.get('data_inicio') or data
        if args.nota:
            livro['notas'] = args.nota

    # progresso do livro = contos lidos / total
    contos = livro.get('contos', [])
    if contos:
        lidos = sum(1 for c in contos if c.get('estado') == 'lido')
        livro['progresso'] = f'{lidos}/{len(contos)}'
        if lidos and livro.get('estado') == 'a_ler':
            livro['estado'] = 'em_leitura'

    # historico: conclusao ou abandono entram no historico
    hist = y.setdefault('historico', [])
    if args.estado in ('lido', 'abandonado'):
        if args.estado == 'abandonado' and not args.motivo:
            print('✗ --motivo e obrigatorio para estado=abandonado', file=sys.stderr)
            sys.exit(1)
        nome = (alvo.get('titulo') if alvo else livro.get('obra'))
        hist.append({
            'obra': nome,
            'obra_pai': livro.get('obra'),
            'autor': 'Arthur Conan Doyle' if 'Doyle' in str(livro.get('obra')) or 'Sherlock' in str(livro.get('obra')) else None,
            'estado': args.estado,
            'data': data,
            'motivo_abandono': args.motivo,
            'nota': args.nota,
        })
        hist = [h for h in hist if h.get('obra') != nome or h.get('estado') != args.estado]
        hist.append(hist[-1])

    y['atualizado_por'] = 'iam'
    y['data'] = data

    header = (
        '# estado-leitura.yaml — RAMPA v4 (2026-11-07)\n'
        '# GERADO por scripts/gerar-estado-leitura-v2.py — nao editar a mao.\n'
        '# ATUALIZACOES DE LEITURA: usar scripts/registrar-leitura.py\n'
        '#   (o gerador le /tmp/*.json que nao sobrevivem a reboot — nao roda-lo\n'
        '#    em cima deste arquivo, ou o estado real e perdido.)\n'
        '# Fonte: /tmp/rampa-final.json, /tmp/sherlock-contos.json,\n'
        '#        /tmp/poe-contos.json, /tmp/canon-final.json, /tmp/gap-canonicos.json\n\n'
    )
    with io.open(YAML_PATH, 'w', encoding='utf-8') as f:
        f.write(header)
        yaml.safe_dump(y, f, allow_unicode=True, sort_keys=False, width=4096,
                       default_flow_style=False)

    # registro persistente (fonte de verdade fora do YAML gerado)
    reg = {}
    if REGISTROS.exists():
        reg = yaml.safe_load(REGISTROS.read_text(encoding='utf-8')) or {}
    reg.setdefault('registros', [])
    reg['registros'].append({
        'data': data,
        'obra_pai': livro.get('obra'),
        'unidade': alvo.get('titulo') if alvo else None,
        'estado': args.estado,
        'nota': args.nota,
        'motivo_abandono': args.motivo,
    })
    REGISTROS.parent.mkdir(parents=True, exist_ok=True)
    with io.open(REGISTROS, 'w', encoding='utf-8') as f:
        f.write('# Registro de leituras do William (fonte de verdade do estado).\n'
                '# Escrito por scripts/registrar-leitura.py.\n\n')
        yaml.safe_dump(reg, f, allow_unicode=True, sort_keys=False, width=4096,
                       default_flow_style=False)

    # valida
    y2 = yaml.safe_load(YAML_PATH.read_text(encoding='utf-8'))
    print('✓ YAML valido. backup:', bak.name)
    print('  obra:', livro['obra'], '| estado:', livro['estado'],
          '| progresso:', livro.get('progresso'))
    if alvo:
        print('  unidade:', alvo['titulo'], '->', alvo['estado'],
              '| data_fim:', alvo.get('data_fim'))


if __name__ == '__main__':
    main()
