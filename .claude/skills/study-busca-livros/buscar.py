#!/usr/bin/env python3
"""Busca nos livros da biblioteca (índice FTS5) e verifica citações literais.

    python3 .claude/skills/study-busca-livros/buscar.py "justificação pela fé"
    python3 .claude/skills/study-busca-livros/buscar.py justific* fé --tags teologia,soteriologia -k 10
    python3 .claude/skills/study-busca-livros/buscar.py --frase "somente pela fé" --json
    python3 .claude/skills/study-busca-livros/buscar.py --verificar "a fé sem obras é morta" [--arquivo tiago]
    python3 .claude/skills/study-busca-livros/buscar.py --info

Sem distinção de acento/caixa; AND entre termos (cai para OU se nada casar); `termo*` é prefixo;
termos são reduzidos ao radical (justificar → justific*) — `--exato` desliga.
`--tags` aplica o escopo do especialista (Regra 8): só livros cujas tags cruzam. Sem `--tags`: pool inteiro.
"""
import argparse
import bisect
import json
import os
import re
import sqlite3
import sys
import unicodedata

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lib_indice as L  # noqa: E402

LIMITE_AUTO_ATUALIZAR = 25  # acima disso, manda rodar indexar.py em vez de travar a busca
STOP = {
    'a', 'o', 'as', 'os', 'de', 'da', 'do', 'das', 'dos', 'e', 'em', 'no', 'na', 'nos', 'nas', 'um', 'uma',
    'que', 'por', 'pela', 'pelo', 'pelas', 'pelos', 'para', 'com', 'se', 'ao', 'aos', 'à', 'às', 'é', 'the', 'of',
}


def sem_acento(s):
    return ''.join(c for c in unicodedata.normalize('NFD', s) if unicodedata.category(c) != 'Mn')


def termos(consulta, manter_stop=False):
    """Tokens da consulta. Frase exata mantém as stopwords (senão a adjacência quebra)."""
    brutos = re.findall(r'\w+\*?', unicodedata.normalize('NFC', ' '.join(consulta)))
    if manter_stop:
        return brutos
    uteis = [t for t in brutos if t.lower() not in STOP]
    return uteis or brutos


# sufixos (sem acento) do português, do mais longo ao mais curto: radical leve, sem dicionário
SUFIXOS = sorted(
    ['amentos', 'imentos', 'amento', 'imento', 'acoes', 'acao', 'ucoes', 'ucao', 'icoes', 'icao', 'mente',
     'idades', 'idade', 'istas', 'ismo', 'ista', 'adores', 'adoras', 'ador', 'antes', 'ante', 'ados', 'adas',
     'ado', 'ada', 'idos', 'idas', 'ido', 'ida', 'ando', 'endo', 'indo', 'aram', 'eram', 'iram', 'amos', 'emos',
     'avam', 'iam', 'ava', 'ia', 'am', 'em', 'ar', 'er', 'ir', 'os', 'as', 'es', 'oes', 'ao', 's', 'o', 'a', 'e'],
    key=len, reverse=True)
RADICAL_MINIMO = 4  # nunca reduz abaixo disso (evita "deus" → "deu*")


def radical(termo):
    """Radical com prefixo para achar flexões (justificar → justific), ou None se não há o que reduzir."""
    base = sem_acento(termo.lower())
    for suf in SUFIXOS:
        if base.endswith(suf) and len(base) - len(suf) >= RADICAL_MINIMO:
            return base[:-len(suf)]
    return None


def montar_match(tokens, frase=False, ou=False, radicais=False):
    def um(t):
        if t.endswith('*'):
            return f'"{t[:-1]}"*'
        r = radical(t) if radicais else None
        return f'"{r}"*' if r else f'"{t}"'
    if frase:
        return '"' + ' '.join(t.rstrip('*') for t in tokens) + '"'
    return (' OR ' if ou else ' AND ').join(um(t) for t in tokens)


def garantir_indice(sem_atualizar):
    con = L.abrir_db()
    if con is None:
        print('Sem índice ainda. Crie com: python3 .claude/skills/study-busca-livros/indexar.py '
              '(leva alguns minutos na primeira vez).', file=sys.stderr)
        return None
    if sem_atualizar:
        return con
    disco = L.listar_arquivos()
    ja = {r[0]: (r[1], r[2]) for r in con.execute('SELECT arquivo, tamanho, mtime_ns FROM docs')}
    pendentes = [a for a, (_, tam, mt) in disco.items() if ja.get(a) != (tam, mt)]
    removidos = [a for a in ja if a not in disco]
    kb_mudou = L.mtime_kbs() != int(dict(con.execute('SELECT k, v FROM meta')).get('kbs_mtime_ns', 0))
    total = len(pendentes) + len(removidos)
    if not total and not kb_mudou:
        return con
    if total > LIMITE_AUTO_ATUALIZAR:
        print(f'aviso: {total} arquivo(s) novos/alterados/removidos desde a última indexação — resultados podem '
              f'estar defasados. Rode indexar.py.', file=sys.stderr)
        return con
    r, rem, _ = L.sincronizar(con)
    print(f'(índice atualizado: {r} reindexado(s), {rem} removido(s))', file=sys.stderr)
    return con


def consultar(con, match, tags, arquivo, limite):
    sql = ("SELECT docs.arquivo, docs.titulo, docs.tags, chunks.ini, chunks.fim, chunks.secao, "
           "snippet(chunks, 0, '«', '»', ' … ', 40), bm25(chunks, 1.0, 0.6) AS r, chunks.rowid "
           "FROM chunks JOIN docs ON docs.id = chunks.doc_id WHERE chunks MATCH ?")
    params = [match]
    if tags:
        sql += ' AND (' + ' OR '.join('docs.tags LIKE ?' for _ in tags) + ')'
        params += [f'% {t} %' for t in tags]
    if arquivo:
        sql += ' AND docs.arquivo LIKE ?'
        params.append(f'%{arquivo}%')
    sql += ' ORDER BY r LIMIT ?'
    params.append(limite)
    return con.execute(sql, params).fetchall()


def diversificar(linhas, top_k, max_por_livro):
    contagem, saida = {}, []
    for lin in linhas:
        if contagem.get(lin[0], 0) >= max_por_livro:
            continue
        contagem[lin[0]] = contagem.get(lin[0], 0) + 1
        saida.append(lin)
        if len(saida) >= top_k:
            break
    return saida


def cmd_buscar(args, con):
    tokens = termos(args.consulta, manter_stop=args.frase)
    if not tokens:
        print('Consulta vazia.', file=sys.stderr)
        return 2
    tags = [t.strip().lower() for t in (args.tags or '').split(',') if t.strip()]
    modo = 'frase' if args.frase else ('OU' if args.ou else 'E')
    rad = not (args.exato or args.frase)
    expansoes = [f'{t}→{radical(t)}*' for t in tokens if rad and not t.endswith('*') and radical(t)]
    linhas = consultar(con, montar_match(tokens, args.frase, args.ou, rad), tags, args.arquivo, args.top_k * 12)
    if not linhas and modo == 'E' and len(tokens) > 1:
        modo = 'OU (aproximado — nenhum trecho tem todos os termos)'
        linhas = consultar(con, montar_match(tokens, ou=True, radicais=rad), tags, args.arquivo, args.top_k * 12)
    achados = diversificar(linhas, args.top_k, args.max_por_livro)
    if args.json:
        chaves = ('arquivo', 'titulo', 'tags', 'linha_inicio', 'linha_fim', 'secao', 'trecho', 'bm25', 'rowid')
        print(json.dumps([dict(zip(chaves, x)) for x in achados], ensure_ascii=False, indent=1))
        return 0 if achados else 3
    if not achados:
        esc = f' no escopo das tags [{", ".join(tags)}]' if tags else ''
        print(f'Nenhum trecho encontrado{esc}. Dica: variações/sinônimos, `termo*` (prefixo) ou sem --tags. '
              f'Se realmente não há material, diga isso ao usuário (Regra 9.4).')
        return 3
    print(f'Busca «{" ".join(tokens)}» · modo {modo} · {len(achados)} resultado(s)'
          + (f' · escopo tags: {", ".join(tags)}' if tags else ' · pool inteiro')
          + (f' · radicais: {", ".join(expansoes)}' if expansoes else ''))
    for n, (arq, tit, tg, ini, fim, secao, trecho, _r, _rid) in enumerate(achados, start=1):
        tit = tit if len(tit) <= 90 else tit[:87] + '…'  # títulos de Z-Library vêm enormes
        print(f'\n[{n}] {tit} — data/{arq}:{ini}-{fim}' + (f' · seção «{secao}»' if secao else '')
              + (f' · tags:{tg.rstrip()}' if tg.strip() else ''))
        print('    ' + re.sub(r'\s+', ' ', trecho).strip())
    print('\nPara ler mais: Read do arquivo com offset/limit ao redor das linhas citadas (nunca o livro inteiro).')
    return 0


def _texto_normalizado_com_linhas(caminho):
    """Texto normalizado + vetores paralelos (offset no normalizado, nº da linha de origem)."""
    partes, offs, lins, pos = [], [], [], 0
    with open(caminho, encoding='utf-8', errors='replace') as fh:
        for n, linha in enumerate(fh, start=1):
            t = re.sub(r'\s+', ' ', linha).strip()
            if not t:
                continue
            t = t[:-1] if t.endswith('-') else t + ' '  # hifenização de fim de linha: cola na próxima
            offs.append(pos)
            lins.append(n)
            partes.append(t)
            pos += len(t)
    return ''.join(partes), offs, lins


def candidatos_por_janelas(con, tokens, largura=3, max_janelas=8, max_docs=12):
    """Arquivos que contêm alguma janela de `largura` termos da citação (frase exata no FTS).

    Janelas deslizantes toleram palavra partida por hifenização no fim da linha, que o FTS indexa
    como dois tokens; a confirmação final é sempre feita no texto do arquivo.
    """
    janelas = [tokens[i:i + largura] for i in range(max(1, len(tokens) - largura + 1))][:max_janelas]
    docs = {}
    for janela in janelas:
        for r in consultar(con, montar_match(janela, frase=True), [], None, 30):
            docs[r[0]] = docs.get(r[0], 0) + 1
    ordenados = sorted(docs, key=lambda a: -docs[a])  # mais janelas casadas primeiro
    return ordenados[:max_docs]


def cmd_verificar(args, con):
    alvo = L.normalizar_texto(args.verificar)
    if not alvo:
        print('Frase vazia.', file=sys.stderr)
        return 2
    if args.arquivo:
        docs = [r[0] for r in con.execute('SELECT arquivo FROM docs WHERE arquivo LIKE ?', (f'%{args.arquivo}%',))]
    else:
        docs = candidatos_por_janelas(con, termos([alvo], manter_stop=True))
    alvo_fold = sem_acento(alvo).casefold()
    for arq in docs:
        texto, offs, lins = _texto_normalizado_com_linhas(os.path.join(L.DATA, arq))
        tentativas = (('EXATA', texto, alvo),
                      ('APROXIMADA — difere em caixa/acentos', sem_acento(texto).casefold(), alvo_fold))
        for rotulo, base, chave in tentativas:
            i = base.find(chave)
            if i >= 0:
                linha = lins[max(0, bisect.bisect_right(offs, i) - 1)]
                print(f'CONFIRMADA ({rotulo}): data/{arq}, a partir da linha {linha}.')
                print('  …' + texto[max(0, i - 60): i + len(chave) + 60].strip() + '…')
                return 0
    onde = f'em {len(docs)} arquivo(s) candidato(s)' if docs else 'em nenhum arquivo candidato'
    print(f'NÃO CONFIRMADA {onde}. Apresente como paráfrase/resumo, sem aspas de citação literal (Regra 9.3).')
    return 3


def cmd_info(con):
    meta = dict(con.execute('SELECT k, v FROM meta'))
    docs = con.execute('SELECT COUNT(*) FROM docs').fetchone()[0]
    chunks = L.contar_chunks(con)
    sem = con.execute("SELECT COUNT(*) FROM docs WHERE tags='  '").fetchone()[0]
    print(f'Índice: {L.DB_PATH}\n  {docs} documentos, {chunks} trechos, {os.path.getsize(L.DB_PATH) / 1048576:.0f} MB\n'
          f'  atualizado em (UTC): {meta.get("atualizado_em", "?")}\n  sem tag de KB: {sem}')
    return 0


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('consulta', nargs='*')
    ap.add_argument('-k', '--top-k', type=int, default=8)
    ap.add_argument('--tags', help='escopo do especialista: tags separadas por vírgula (cruza por qualquer uma)')
    ap.add_argument('--arquivo', help='restringe a arquivos cujo caminho contém este texto')
    ap.add_argument('--frase', action='store_true', help='frase exata (termos adjacentes, na ordem)')
    ap.add_argument('--ou', action='store_true', help='qualquer termo (em vez de todos)')
    ap.add_argument('--exato', action='store_true', help='não reduz termos ao radical (justificar ≠ justificação)')
    ap.add_argument('--max-por-livro', type=int, default=2)
    ap.add_argument('--json', action='store_true')
    ap.add_argument('--verificar', metavar='FRASE', help='confirma se a citação literal existe no(s) livro(s)')
    ap.add_argument('--info', action='store_true')
    ap.add_argument('--sem-atualizar', action='store_true', help='não checa arquivos novos antes de buscar')
    args = ap.parse_args()

    con = garantir_indice(args.sem_atualizar)
    if con is None:
        return 2
    try:
        if args.info:
            return cmd_info(con)
        if args.verificar:
            return cmd_verificar(args, con)
        if not args.consulta:
            ap.print_usage(sys.stderr)
            return 2
        return cmd_buscar(args, con)
    except sqlite3.OperationalError as exc:
        print(f'ERRO na consulta: {exc}. Termos com símbolos? Tente palavras simples.', file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
