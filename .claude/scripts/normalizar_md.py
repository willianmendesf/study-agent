#!/usr/bin/env python3
"""Normaliza o markdown de livros convertidos (PDF/EPUB/OCR): junta letras espaçadas.

Conversores (pdfminer/markitdown e OCR) leem tipografia com espaçamento largo de letras e
produzem `T E O L O G IA  S I S T E M A T I C A`. Isso quebra busca, citação e leitura. Este módulo
é a correção NA ORIGEM: toda conversão deve passar por aqui (book-pipeline, ocr-pdf.py, e a
Regra 2 do CLAUDE.md para conversões manuais). O indexador de busca usa a mesma função.

Só letras LATINAS (com acento) são juntadas: grego, hebraico etc. ficam intactos (tabelas de
alfabeto `α β γ δ` são conteúdo legítimo). Blocos de código (```) são preservados. Só espaços
mudam, então a numeração de linhas do arquivo não se altera. Idempotente.

    python3 .claude/scripts/normalizar_md.py livro.md              # corrige o arquivo
    python3 .claude/scripts/normalizar_md.py data/estudos/livros --dry-run   # só conta
"""
import argparse
import os
import re
import sys

LETRA = 'A-Za-zÀ-ÖØ-öø-ÿ'
# 3+ letras soltas ("T E O L ") seguidas de um fecho de 1-3 letras ("IA"), isoladas por espaço/borda
RE_LETRAS_ESPACADAS = re.compile(rf'(?<!\S)(?:[{LETRA}] ){{3,}}[{LETRA}]{{1,3}}(?!\S)')
EXTENSOES = ('.md', '.txt')


def _juntar(m):
    return m.group(0).replace(' ', '')


def descolar_letras(texto):
    """Devolve o texto com as letras espaçadas juntas (fora de blocos de código)."""
    dentro_codigo, saida = False, []
    for linha in texto.split('\n'):
        if linha.lstrip().startswith('```'):
            dentro_codigo = not dentro_codigo
            saida.append(linha)
        else:
            saida.append(linha if dentro_codigo else RE_LETRAS_ESPACADAS.sub(_juntar, linha))
    return '\n'.join(saida)


def normalizar_arquivo(caminho, dry_run=False):
    """Normaliza um arquivo. Devolve o nº de linhas alteradas (0 = já limpo). Grava de forma atômica."""
    # surrogateescape: bytes inválidos em utf-8 atravessam a leitura/escrita sem serem trocados por �
    with open(caminho, encoding='utf-8', errors='surrogateescape', newline='') as fh:
        original = fh.read()
    novo = descolar_letras(original)
    if novo == original:
        return 0
    alteradas = sum(1 for a, b in zip(original.split('\n'), novo.split('\n')) if a != b)
    if not dry_run:
        tmp = caminho + '.norm.tmp'
        with open(tmp, 'w', encoding='utf-8', errors='surrogateescape', newline='') as fh:
            fh.write(novo)
        try:
            os.chmod(tmp, os.stat(caminho).st_mode)
        except OSError:
            pass
        os.replace(tmp, caminho)
    return alteradas


def _arquivos(alvos):
    for alvo in alvos:
        if os.path.isdir(alvo):
            for base, dirs, nomes in os.walk(alvo):
                dirs[:] = [d for d in dirs if not d.startswith('.') and d != '_staging']
                for nome in sorted(nomes):
                    if nome.lower().endswith(EXTENSOES) and not nome.startswith('.'):
                        yield os.path.join(base, nome)
        elif os.path.isfile(alvo):
            yield alvo
        else:
            print(f'aviso: {alvo} não existe', file=sys.stderr)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('alvos', nargs='+', help='arquivo(s) ou pasta(s) (recursivo, .md/.txt)')
    ap.add_argument('--dry-run', action='store_true', help='só conta; não grava')
    args = ap.parse_args()
    arquivos = afetados = linhas = 0
    for caminho in _arquivos(args.alvos):
        arquivos += 1
        n = normalizar_arquivo(caminho, dry_run=args.dry_run)
        if n:
            afetados += 1
            linhas += n
            print(f'  {n:6d} linha(s)  {caminho}')
    modo = 'a corrigir' if args.dry_run else 'corrigido(s)'
    print(f'{arquivos} arquivo(s) verificado(s); {afetados} {modo}; {linhas} linha(s) com letras espaçadas.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
