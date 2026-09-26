#!/usr/bin/env python3
"""Cria/atualiza o índice de texto completo dos livros (data/.indice/livros.db).

Incremental: só reprocessa arquivos novos/alterados (tamanho, mtime ou tags do KB) e remove os apagados.

    python3 .claude/skills/study-busca-livros/indexar.py            # atualiza
    python3 .claude/skills/study-busca-livros/indexar.py --refazer  # apaga e recria do zero
"""
import argparse
import os
import sqlite3
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lib_indice as L  # noqa: E402


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--refazer', action='store_true', help='apaga o índice e recria do zero')
    args = ap.parse_args()

    if not os.path.isdir(L.DATA):
        print(f'ERRO: pasta data/ não encontrada em {L.RAIZ} (rode o setup — CLAUDE.md Regra 7).', file=sys.stderr)
        return 2
    if args.refazer:
        for sufixo in ('', '-wal', '-shm'):
            try:
                os.remove(L.DB_PATH + sufixo)
            except FileNotFoundError:
                pass

    con = L.abrir_db(criar=True)
    inicio = time.time()

    def progresso(n, total, arq):
        if n == 1 or n % 25 == 0 or n == total:
            print(f'  [{n}/{total}] {time.time() - inicio:5.0f}s  {arq[:90]}', flush=True)

    try:
        reindexados, removidos, chunks = L.sincronizar(con, progresso, migrar_norm=True)
    except sqlite3.Error as exc:
        print(f'ERRO no índice: {exc}. Tente --refazer.', file=sys.stderr)
        return 1
    total_docs = con.execute('SELECT COUNT(*) FROM docs').fetchone()[0]
    total_chunks = L.contar_chunks(con)
    sem_tag = con.execute("SELECT COUNT(*) FROM docs WHERE tags='  '").fetchone()[0]
    con.close()
    tam_mb = os.path.getsize(L.DB_PATH) / 1048576
    print(
        f'OK em {time.time() - inicio:.0f}s: {reindexados} arquivo(s) (re)indexado(s), {removidos} removido(s), '
        f'+{chunks} trechos. Índice: {total_docs} documentos, {total_chunks} trechos, {tam_mb:.0f} MB '
        f'({sem_tag} sem tag de KB — só aparecem quando NÃO há especialista ativo).'
    )
    return 0


if __name__ == '__main__':
    sys.exit(main())
