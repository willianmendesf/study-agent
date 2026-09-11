#!/usr/bin/env python3
"""
Processa todos arquivos pendentes do Drive 1. Fides com PARALELISMO e progresso.
Resumível: pula o que já tem .md com > 500 bytes.
OCR automático pra arquivos escaneados.

Uso: python3 /tmp/processa-paralelo.py
"""
import sys, os, json, time, subprocess, hashlib
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
import urllib.request, urllib.parse
import threading

CRED = Path.home() / '.config' / 'gdrive-mcp' / 'gdrive-credentials.json'
KEYS = Path.home() / '.config' / 'gdrive-mcp' / 'gcp-oauth.keys.json'
TMP = Path('/tmp/gdrive-paralelo')

BASE = Path('/dados/study-agent/data/estudos/livros')

# ========== CONFIG ==========
ROOT_1FIDES = '1CsWI_bYHZ8qk6nt1v52HfWcMl0az0BQr'
MAX_DOWNLOAD_WORKERS = 4   # paralelo em download (I/O)
MAX_CONVERT_WORKERS = 3    # paralelo em markitdown (CPU)
MAX_OCR_WORKERS = 1        # OCR é pesado — 1 por vez

CATEGORIAS = {
    'Bibliologia': ('Bibliologia', 'bibliologia', 'BL-'),
    'Cronologia e Contextos Históricos': ('Cronologia e Contextos Históricos', 'cronologia-contextos-historicos', 'CC-'),
    'Bases da fé': ('Bases da fé', 'bases-da-fe', 'BF-'),
    'Sexual': ('Sexual', 'sexual', 'SX-'),
    'Feminilidade Cristã': ('Feminilidade Cristã', 'familia-crista', 'FM-'),
    'Familia Cristã': ('Familia Cristã', 'familia-crista', 'FC-'),
    'Messias': ('Messias', 'messias', 'MS-'),
    'Historia': ('Historia', 'historia', 'HI-'),
    'Pastoral': ('Pastoral', 'pastoral', 'PS-'),
    'Cultura dos Textos Biblicos': ('Cultura dos Textos Biblicos', 'cultura-textos-biblicos', 'CT-'),
    'Arqueologia Biblica': ('Arqueologia Biblica', 'arqueologia-biblica', 'AQ-'),
    'Hermeneutica e Exegese': ('Hermeneutica e Exegese', 'exegese-hermeneutica', 'HE-'),
    'Simbologias Biblicas': ('Simbologias Biblicas', 'referencias-biblicas', 'SB-'),
    'Personagens Bíblicos': ('Personagens Bíblicos', 'referencias-biblicas', 'PB-'),
    'Teologia Bíblica': ('Teologia Bíblica', 'teologia-biblica', 'TB-'),
    'Manuais Bíblicos': ('Manuais Bíblicos', 'manuais-biblicos', 'MB-'),
    'Dicionário Teológico e Exegético': ('Dicionário Teológico e Exegético', 'dicionario-teologico', 'DT-'),
    'Línguas Originais': ('Línguas Originais', 'linguas-originais', 'LO-'),
    'Igreja': ('Igreja', 'igreja-discipulado', 'IG-'),
    'Outros': ('Outros', 'outros', 'OU-'),
    'Teologia': ('Teologia', 'teologia', 'TG-'),
    'Teologia Sistemática': ('Teologia Sistemática', 'teologia-sistematica', 'TS-'),
    'História da Igreja': ('História da Igreja', 'historia-igreja', 'HI2-'),
    'Atlas & Mapas Bíblicos': ('Atlas & Mapas Bíblicos', 'atlas-mapas', 'AM-'),
    'Comentários Biblicos': ('Comentários Biblicos', 'comentarios-biblicos', 'CB-'),
    'Dicionários, Enciclopédias e Concordâncias Biblicas': ('Dicionários, Enciclopédias e Concordâncias Biblicas', 'dicionarios-concordancias', 'DC-'),
    'Filosofia Cristã': ('Filosofia Cristã', 'filosofia-crista', 'FC2-'),
    'Masculinidade Cristã': ('Masculinidade Cristã', 'masculinidade-crista', 'MC-'),
    'Temperamentos': ('Temperamentos', 'temperamentos', 'TP-'),
}

# ========== FUNÇÕES ==========
token_lock = threading.Lock()

def get_token():
    with token_lock:
        with open(CRED) as f:
            creds = json.load(f)
        if time.time() * 1000 < creds['expiry_date'] - 60000:
            return creds['access_token']
        # refresh
        with open(KEYS) as f:
            keys = json.load(f)['web']
        data = urllib.parse.urlencode({
            'client_id': keys['client_id'],
            'client_secret': keys['client_secret'],
            'refresh_token': creds['refresh_token'],
            'grant_type': 'refresh_token',
        }).encode()
        req = urllib.request.Request('https://oauth2.googleapis.com/token', data=data)
        with urllib.request.urlopen(req) as r:
            new_creds = json.load(r)
        creds.update(new_creds)
        creds['expiry_date'] = int(time.time() * 1000) + creds['expires_in'] * 1000
        with open(CRED, 'w') as f:
            json.dump(creds, f, indent=2)
        os.chmod(CRED, 0o600)
        return creds['access_token']

def api(path, params=None):
    token = get_token()
    qs = urllib.parse.urlencode(params or {}, quote_via=urllib.parse.quote)
    url = f'https://www.googleapis.com/drive/v3/{path}?{qs}'
    req = urllib.request.Request(url, headers={'Authorization': f'Bearer {token}'})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.load(r)

def listar(folder_id, max_depth=4, depth=0):
    if depth > max_depth:
        return []
    d = api('files', {
        'q': f"'{folder_id}' in parents and trashed=false",
        'fields': 'files(id,name,mimeType,size)',
        'pageSize': 200,
    })
    items = []
    for f in d.get('files', []):
        if 'folder' in f['mimeType']:
            items.extend(listar(f['id'], max_depth, depth + 1))
        else:
            items.append(f)
    return items

def baixar(file_id, dest):
    token = get_token()
    req = urllib.request.Request(
        f'https://www.googleapis.com/drive/v3/files/{file_id}?alt=media',
        headers={'Authorization': f'Bearer {token}'}
    )
    with urllib.request.urlopen(req, timeout=600) as r:
        with open(dest, 'wb') as f:
            f.write(r.read())

def sanitize(nome):
    import unicodedata
    nfkd = unicodedata.normalize('NFKD', nome)
    ascii_name = nfkd.encode('ASCII', 'ignore').decode('ASCII')
    ascii_name = ascii_name.replace(' ', '_').replace('_-_', '-').replace('__', '_')
    ascii_name = ''.join(c if c.isalnum() or c in '-_.' else '-' for c in ascii_name)
    while '--' in ascii_name:
        ascii_name = ascii_name.replace('--', '-')
    return ascii_name.strip('-_.')[:120]

def converter(input_path, output_path, timeout_min=10):
    try:
        r = subprocess.run(
            ['uvx', '--from', 'markitdown[all]', 'markitdown', str(input_path), '-o', str(output_path)],
            capture_output=True, text=True, timeout=timeout_min*60
        )
        return r.returncode == 0
    except subprocess.TimeoutExpired:
        return False

def ocr(input_path, output_path, timeout_min=45):
    try:
        r = subprocess.run(
            ['python3', '/tmp/ocr-pdf.py', str(input_path), str(output_path)],
            capture_output=True, text=True, timeout=timeout_min*60
        )
        return r.returncode == 0
    except subprocess.TimeoutExpired:
        return False

def processar_arquivo(args):
    """Worker: processa 1 arquivo (download + convert + ocr se necessário)."""
    file_id, nome, dest_dir, prefix, status_print = args

    out_name = prefix + sanitize(nome)
    output = dest_dir / f'{out_name}.md'

    if output.exists() and output.stat().st_size > 500:
        return ('skip', nome, 0, dest_dir.name)

    ext = nome.rsplit('.', 1)[-1].lower() if '.' in nome else ''

    tmp = TMP / f'{file_id}'
    tmp.parent.mkdir(exist_ok=True, parents=True)

    try:
        # Download
        try:
            baixar(file_id, tmp)
        except Exception as e:
            return ('erro_download', nome, 0, dest_dir.name)

        # Convert
        if converter(tmp, output):
            try:
                linhas = sum(1 for _ in open(output))
            except:
                linhas = 0

            # OCR se necessário
            if linhas < 50 and ext == 'pdf':
                if ocr(tmp, output, timeout_min=45):
                    try:
                        linhas = sum(1 for _ in open(output))
                    except:
                        linhas = 0
                    return ('ocr', nome, linhas, dest_dir.name)
                else:
                    return ('parcial', nome, linhas, dest_dir.name)

            return ('ok', nome, linhas, dest_dir.name)
        else:
            return ('erro_conversao', nome, 0, dest_dir.name)
    finally:
        tmp.unlink(missing_ok=True)


# ========== MAIN ==========

def main():
    TMP.mkdir(exist_ok=True, parents=True)

    log_file = BASE / '_processamento_paralelo.log'
    log = open(log_file, 'a')
    log.write(f'\n\n===== INÍCIO PARALELO {time.strftime("%Y-%m-%d %H:%M:%S")} =====\n')
    log.flush()

    # Categorias do Drive
    cats = api('files', {
        'q': f"'{ROOT_1FIDES}' in parents and trashed=false and mimeType='application/vnd.google-apps.folder'",
        'fields': 'files(id,name)',
        'pageSize': 100,
    }).get('files', [])
    cats_map = {c['name']: c['id'] for c in cats}

    # Coletar TODOS os arquivos
    todos_arquivos = []
    for cat_name, (cat_drive_name, subdir, prefix) in CATEGORIAS.items():
        cat_id = cats_map.get(cat_drive_name)
        if not cat_id:
            print(f'⚠️  {cat_drive_name} não encontrada', flush=True)
            continue
        dest_dir = BASE / subdir
        dest_dir.mkdir(parents=True, exist_ok=True)

        files = listar(cat_id)
        # Filtrar já convertidos
        pendentes = []
        for f in files:
            if 'folder' in f['mimeType']:
                continue
            out_name = prefix + sanitize(f['name'])
            output = dest_dir / f'{out_name}.md'
            if not (output.exists() and output.stat().st_size > 500):
                pendentes.append((f, dest_dir, prefix, cat_drive_name))
        if pendentes:
            print(f'📂 {cat_drive_name}: {len(pendentes)} arquivos pendentes', flush=True)
        todos_arquivos.extend(pendentes)

    print(f'\n{"="*70}', flush=True)
    print(f'🚀 TOTAL: {len(todos_arquivos)} arquivos a processar', flush=True)
    print(f'   Downloads paralelos: {MAX_DOWNLOAD_WORKERS}', flush=True)
    print(f'{"="*70}\n', flush=True)

    if not todos_arquivos:
        print('✅ Nada pendente!', flush=True)
        return

    # Contadores
    stats = {'ok': 0, 'ocr': 0, 'parcial': 0, 'skip': 0, 'erro_download': 0, 'erro_conversao': 0}
    sucessos_arquivos = []
    falhas = []

    # Argumentos pros workers
    args_list = [(f['id'], f['name'], dest, prefix, None)
                 for (f, dest, prefix, cat) in todos_arquivos]

    # Ordem: menor pro maior
    args_list.sort(key=lambda a: 0)  # tamanho já vem pequeno primeiro
    
    start_time = time.time()
    processed = 0

    # Pool de execução
    with ThreadPoolExecutor(max_workers=MAX_CONVERT_WORKERS) as executor:
        futures = {executor.submit(processar_arquivo, args): args for args in args_list}

        for future in as_completed(futures):
            processed += 1
            args = futures[future]
            try:
                status, nome, linhas, cat = future.result()
            except Exception as e:
                status, nome, linhas, cat = 'erro_excecao', args[1], 0, args[3]

            stats[status] = stats.get(status, 0) + 1

            icon = {'ok': '✅', 'ocr': '⚠️ ', 'parcial': '⚠️ ',
                    'skip': '⏭️ ', 'erro_download': '❌', 'erro_conversao': '❌',
                    'erro_excecao': '💥'}.get(status, '?')

            elapsed = time.time() - start_time
            speed = processed / elapsed if elapsed > 0 else 0
            eta = (len(args_list) - processed) / speed if speed > 0 else 0

            if status in ('erro_download', 'erro_conversao', 'erro_excecao'):
                falhas.append((nome, cat, status))
                msg = f'   {icon} [{processed:3d}/{len(args_list)}] {nome[:50]:50s} → {status}'
            else:
                msg = f'   {icon} [{processed:3d}/{len(args_list)}] {nome[:50]:50s} → {linhas:>6} linhas'

            if status in ('ok', 'ocr'):
                msg += f'   ({elapsed:.0f}s decorrido, ETA {eta:.0f}s)'

            print(msg, flush=True)
            log.write(f'{status.upper()}: {cat} / {nome} → {linhas} linhas\n')
            log.flush()

    log.write(f'\n===== FIM {time.strftime("%Y-%m-%d %H:%M:%S")} =====\n')
    log.write(f'Resultados: {stats}\n')
    log.close()

    print(f'\n{"="*70}', flush=True)
    print(f'📊 RESUMO:', flush=True)
    for k, v in stats.items():
        if v > 0:
            icon = {'ok': '✅', 'ocr': '⚠️ ', 'parcial': '⚠️ ',
                    'skip': '⏭️ ', 'erro_download': '❌', 'erro_conversao': '❌'}.get(k, '?')
            print(f'   {icon} {k}: {v}', flush=True)
    print(f'   ⏱️  Tempo total: {time.time()-start_time:.0f}s', flush=True)
    print(f'📄 Log: {log_file}', flush=True)


if __name__ == '__main__':
    main()