"""Núcleo do índice de texto completo (SQLite FTS5) dos livros do Study-Agent.

Só stdlib + PyYAML vendorizado (`.claude/scripts/vendor`). O índice é DERIVADO dos
markdowns (nunca é fonte de verdade): pode ser apagado e recriado a qualquer momento.
"""
import os
import re
import sqlite3
import sys
import unicodedata

RAIZ = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
DATA = os.path.join(RAIZ, 'data')
DB_PATH = os.path.join(DATA, '.indice', 'livros.db')

VERSAO_ESQUEMA = '1'
DIRS_INDEXADOS = ('estudos', 'biblioteca')
EXTENSOES = ('.md', '.txt')
DIRS_IGNORADOS = {'.git', '.processing', 'node_modules', '_tools', '__pycache__'}
ALVO_CHUNK = 1400   # caracteres: fecha o chunk na próxima quebra de parágrafo
MAX_CHUNK = 2400    # teto duro: parte no limite de linha (ou de caractere, se a linha for gigante)
RE_TITULO = re.compile(r'^\s{0,3}#{1,6}\s+(.*\S)\s*$')


def abrir_db(criar=False):
    if not criar and not os.path.exists(DB_PATH):
        return None
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    con = sqlite3.connect(DB_PATH)
    con.execute('PRAGMA journal_mode=WAL')
    con.execute('PRAGMA synchronous=NORMAL')
    if criar:
        criar_esquema(con)
    return con


def criar_esquema(con):
    con.executescript(
        """
        CREATE TABLE IF NOT EXISTS meta (k TEXT PRIMARY KEY, v TEXT);
        CREATE TABLE IF NOT EXISTS docs (
            id INTEGER PRIMARY KEY,
            arquivo TEXT UNIQUE NOT NULL,   -- relativo a data/, com '/'
            titulo TEXT,
            tags TEXT NOT NULL DEFAULT ' ',  -- ' a b c ' (busca por ' a ')
            kbs TEXT NOT NULL DEFAULT '',
            tamanho INTEGER, mtime_ns INTEGER, linhas INTEGER,
            rowid_ini INTEGER, rowid_fim INTEGER
        );
        CREATE VIRTUAL TABLE IF NOT EXISTS chunks USING fts5(
            texto, secao, doc_id UNINDEXED, ini UNINDEXED, fim UNINDEXED,
            tokenize = 'unicode61 remove_diacritics 2'
        );
        """
    )
    con.execute("INSERT OR REPLACE INTO meta VALUES ('esquema', ?)", (VERSAO_ESQUEMA,))
    con.commit()


def rel_data(caminho):
    return os.path.relpath(caminho, DATA).replace(os.sep, '/')


def normalizar_caminho_kb(valor):
    """Converte o `caminho_md` de um KB (absoluto de qualquer máquina, ou relativo) em 'estudos/...'."""
    if not valor:
        return None
    v = str(valor).replace('\\', '/')
    marca = v.rfind('/data/')
    if marca >= 0:
        v = v[marca + len('/data/'):]
    elif v.startswith('data/'):
        v = v[len('data/'):]
    return v.lstrip('/')


def _yaml():
    vendor = os.path.join(RAIZ, '.claude', 'scripts', 'vendor')
    if vendor not in sys.path:
        sys.path.insert(0, vendor)
    import yaml  # noqa: E402  (vendorizado)
    return yaml


def carregar_kbs():
    """Devolve {arquivo_rel: {'tags': set, 'kbs': set, 'titulo': str}} a partir dos KBs do pool."""
    yaml = _yaml()
    mapa = {}
    pasta = os.path.join(DATA, 'biblioteca')
    for base, dirs, arquivos in os.walk(pasta):
        dirs[:] = [d for d in dirs if d not in DIRS_IGNORADOS and not d.startswith('.')]
        for nome in arquivos:
            if not nome.endswith(('.yaml', '.yml')):
                continue
            try:
                with open(os.path.join(base, nome), encoding='utf-8') as fh:
                    doc = yaml.safe_load(fh) or {}
            except Exception as exc:  # KB quebrado não derruba a indexação
                print(f'aviso: KB ilegível {nome}: {exc}', file=sys.stderr)
                continue
            if not isinstance(doc, dict):
                continue
            tags = {str(t).strip().lower() for t in (doc.get('tags') or []) if str(t).strip()}
            for item in doc.get('materiais') or []:
                if not isinstance(item, dict):
                    continue
                alvo = normalizar_caminho_kb(item.get('caminho_md'))
                if not alvo:
                    continue
                reg = mapa.setdefault(alvo, {'tags': set(), 'kbs': set(), 'titulo': ''})
                reg['tags'] |= tags
                reg['kbs'].add(nome.rsplit('.', 1)[0])
                reg['titulo'] = reg['titulo'] or str(item.get('titulo') or '')
    return mapa


def mtime_kbs():
    """Maior mtime (ns) entre os KBs do pool — barato; detecta mudança de tags sem reparsear."""
    maior = 0
    for base, dirs, arquivos in os.walk(os.path.join(DATA, 'biblioteca')):
        dirs[:] = [d for d in dirs if d not in DIRS_IGNORADOS and not d.startswith('.')]
        for nome in arquivos:
            if nome.endswith(('.yaml', '.yml')):
                try:
                    maior = max(maior, os.stat(os.path.join(base, nome)).st_mtime_ns)
                except OSError:
                    pass
    return maior


def listar_arquivos():
    """Todos os .md/.txt indexáveis: {arquivo_rel: (caminho_abs, tamanho, mtime_ns)}."""
    achados = {}
    for topo in DIRS_INDEXADOS:
        for base, dirs, arquivos in os.walk(os.path.join(DATA, topo)):
            dirs[:] = [d for d in dirs if d not in DIRS_IGNORADOS and not d.startswith('.')]
            for nome in arquivos:
                if not nome.lower().endswith(EXTENSOES) or nome.startswith('.'):
                    continue
                cam = os.path.join(base, nome)
                try:
                    st = os.stat(cam)
                except OSError:
                    continue
                achados[rel_data(cam)] = (cam, st.st_size, st.st_mtime_ns)
    return achados


def fatiar(texto):
    """Gera (texto_chunk, linha_ini, linha_fim, secao) — linhas 1-indexadas, fechadas."""
    linhas = texto.split('\n')
    secao = ''
    buf, ini, tam = [], 1, 0
    for i, linha in enumerate(linhas, start=1):
        m = RE_TITULO.match(linha)
        if m:
            if buf and tam > 200:  # título abre chunk novo, sem picotar seções curtas
                yield '\n'.join(buf), ini, i - 1, secao
                buf, tam = [], 0
            secao = m.group(1)[:120]
        # linha gigante (OCR sem quebra): parte por caractere, mantendo o número da linha
        while len(linha) > MAX_CHUNK:
            if buf:
                yield '\n'.join(buf), ini, max(ini, i - 1), secao
                buf, tam = [], 0
            yield linha[:MAX_CHUNK], i, i, secao
            linha = linha[MAX_CHUNK:]
        if not buf:
            ini = i
        buf.append(linha)
        tam += len(linha) + 1
        if (linha.strip() == '' and tam >= ALVO_CHUNK) or tam >= MAX_CHUNK:
            yield '\n'.join(buf), ini, i, secao
            buf, tam = [], 0
    if buf and ''.join(buf).strip():
        yield '\n'.join(buf), ini, len(linhas), secao


def _titulo_do_arquivo(texto, nome):
    for linha in texto.split('\n', 60)[:60]:
        m = RE_TITULO.match(linha)
        if m:
            return m.group(1)[:160]
    base = os.path.splitext(os.path.basename(nome))[0].replace('.pdf', '')
    return base.replace('_', ' ').replace('-', ' ')


def _apagar_doc(con, arquivo):
    r = con.execute('SELECT id, rowid_ini, rowid_fim FROM docs WHERE arquivo=?', (arquivo,)).fetchone()
    if not r:
        return
    if r[1] is not None:
        con.execute('DELETE FROM chunks WHERE rowid BETWEEN ? AND ?', (r[1], r[2]))
    con.execute('DELETE FROM docs WHERE id=?', (r[0],))


def indexar_arquivo(con, arquivo, caminho, tamanho, mtime_ns, kbs):
    """(Re)indexa um arquivo: apaga o intervalo de rowids anterior e insere o novo."""
    with open(caminho, encoding='utf-8', errors='replace') as fh:
        texto = fh.read()
    _apagar_doc(con, arquivo)
    info = kbs.get(arquivo, {})
    tags = ' ' + ' '.join(sorted(info.get('tags', []))) + ' '
    titulo = info.get('titulo') or _titulo_do_arquivo(texto, arquivo)
    cur = con.execute(
        'INSERT INTO docs (arquivo, titulo, tags, kbs, tamanho, mtime_ns, linhas) VALUES (?,?,?,?,?,?,?)',
        (arquivo, titulo, tags, ','.join(sorted(info.get('kbs', []))), tamanho, mtime_ns, texto.count('\n') + 1),
    )
    doc_id = cur.lastrowid
    prox = con.execute('SELECT COALESCE(MAX(rowid),0) FROM chunks').fetchone()[0] + 1
    linhas_db = [
        (prox + n, c, secao, doc_id, ini, fim)
        for n, (c, ini, fim, secao) in enumerate(x for x in fatiar(texto) if x[0].strip())
    ]
    if linhas_db:
        con.executemany('INSERT INTO chunks (rowid, texto, secao, doc_id, ini, fim) VALUES (?,?,?,?,?,?)', linhas_db)
        con.execute('UPDATE docs SET rowid_ini=?, rowid_fim=? WHERE id=?', (linhas_db[0][0], linhas_db[-1][0], doc_id))
    return len(linhas_db)


def diferencas(con):
    """(novos_ou_alterados, removidos, kbs) comparando disco × índice (inclui mudança de tags)."""
    disco = listar_arquivos()
    ja = {r[0]: (r[1], r[2], r[3]) for r in con.execute('SELECT arquivo, tamanho, mtime_ns, tags FROM docs')}
    kbs = carregar_kbs()
    mudou = []
    for arq, (cam, tam, mt) in disco.items():
        tags_novas = ' ' + ' '.join(sorted(kbs.get(arq, {}).get('tags', []))) + ' '
        atual = ja.get(arq)
        if atual is None or atual[0] != tam or atual[1] != mt or atual[2] != tags_novas:
            mudou.append((arq, cam, tam, mt))
    removidos = [a for a in ja if a not in disco]
    return mudou, removidos, kbs


def sincronizar(con, progresso=None):
    """Aplica as diferenças. Devolve (reindexados, removidos, chunks)."""
    mudou, removidos, kbs = diferencas(con)
    for arq in removidos:
        _apagar_doc(con, arq)
    total_chunks = 0
    for n, (arq, cam, tam, mt) in enumerate(mudou, start=1):
        total_chunks += indexar_arquivo(con, arq, cam, tam, mt, kbs)
        con.commit()
        if progresso:
            progresso(n, len(mudou), arq)
    con.execute("INSERT OR REPLACE INTO meta VALUES ('atualizado_em', datetime('now'))")
    con.execute("INSERT OR REPLACE INTO meta VALUES ('kbs_mtime_ns', ?)", (str(mtime_kbs()),))
    con.commit()
    return len(mudou), len(removidos), total_chunks


def normalizar_texto(s):
    """Para comparar citações: NFC, junta hifenização de fim de linha, colapsa espaços."""
    s = unicodedata.normalize('NFC', s)
    s = re.sub(r'-\s*\n\s*', '', s)
    return re.sub(r'\s+', ' ', s).strip()
