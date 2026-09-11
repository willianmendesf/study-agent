#!/usr/bin/env python3
"""Processa PDFs/EPUBs do Drive sequencialmente com auto-refresh de token.
Resumível: pula arquivos já convertidos.
Uso: python3 /tmp/processa-drive.py <parent_drive_id> <dest_dir> <prefixo_nome>
"""
import sys, os, json, time, subprocess, hashlib
from pathlib import Path
import urllib.request, urllib.parse

CRED = '/home/willianmendesf/.config/gdrive-mcp/gdrive-credentials.json'

def get_token():
    """Auto-refresh se token expirado."""
    with open(CRED) as f:
        creds = json.load(f)
    if time.time() * 1000 < creds['expiry_date'] - 60000:
        return creds['access_token']
    # Refresh
    with open('/home/willianmendesf/.config/gdrive-mcp/gcp-oauth.keys.json') as f:
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
    print('  [token refreshed]', flush=True)
    return creds['access_token']

def listar(pasta_id):
    """Lista arquivos de uma pasta do Drive."""
    token = get_token()
    qs = urllib.parse.urlencode({
        'q': f"'{pasta_id}' in parents and trashed=false",
        'fields': 'files(id,name,mimeType,size)',
        'pageSize': 200,
    }, quote_via=urllib.parse.quote)
    req = urllib.request.Request(f'https://www.googleapis.com/drive/v3/files?{qs}',
                                  headers={'Authorization': f'Bearer {token}'})
    with urllib.request.urlopen(req) as r:
        return json.load(r).get('files', [])

def baixar(file_id, dest):
    """Baixa arquivo do Drive."""
    token = get_token()
    req = urllib.request.Request(
        f'https://www.googleapis.com/drive/v3/files/{file_id}?alt=media',
        headers={'Authorization': f'Bearer {token}'}
    )
    with urllib.request.urlopen(req, timeout=300) as r:
        with open(dest, 'wb') as f:
            f.write(r.read())

def converter(input_path, output_path, max_minutes=10):
    """Converte arquivo pra .md via markitdown."""
    try:
        result = subprocess.run(
            ['uvx', '--from', 'markitdown[all]', 'markitdown', str(input_path), '-o', str(output_path)],
            capture_output=True, text=True, timeout=max_minutes*60
        )
        return result.returncode == 0
    except subprocess.TimeoutExpired:
        print(f'  ⏱️ TIMEOUT ({max_minutes} min) — pulando', flush=True)
        return False

def md5(path):
    h = hashlib.md5()
    with open(path, 'rb') as f:
        h.update(f.read())
    return h.hexdigest()

# MAIN
parent_id = sys.argv[1]  # ID da pasta do Drive
dest_dir = Path(sys.argv[2])  # Pasta destino
prefixo = sys.argv[3] if len(sys.argv) > 3 else ''  # Prefixo opcional p/ nome do arquivo

dest_dir.mkdir(parents=True, exist_ok=True)
log_file = dest_dir / '_processamento.log'

print(f'📂 Processando pasta {parent_id}', flush=True)
print(f'📁 Destino: {dest_dir}', flush=True)

# Listar arquivos
files = listar(parent_id)
files = [f for f in files if 'folder' not in f['mimeType']]
print(f'📋 {len(files)} arquivos encontrados', flush=True)

# Ordenar por tamanho (menor primeiro)
files.sort(key=lambda x: int(x.get('size', 0)))

with open(log_file, 'w') as log:
    log.write(f'Início: {time.strftime("%Y-%m-%d %H:%M:%S")}\n')
    log.flush()

    sucessos = 0
    falhas = []
    pulos = 0

    for f in files:
        fid = f['id']
        nome = f['name']
        size = int(f.get('size', 0))

        # Nome do .md: remover extensão e adicionar prefixo
        nome_base = nome.rsplit('.', 1)[0]
        # Sanitizar
        nome_md = prefixo + nome_base
        nome_md = ''.join(c if c.isalnum() or c in '-_' else '-' for c in nome_md)
        while '--' in nome_md:
            nome_md = nome_md.replace('--', '-')
        nome_md = nome_md.strip('-')

        output = dest_dir / f'{nome_md}.md'

        # Pular se já existe com conteúdo
        if output.exists() and output.stat().st_size > 500:
            print(f'  ⏭️  {nome_md}.md já existe ({output.stat().st_size//1024} KB)', flush=True)
            pulos += 1
            continue

        # Baixar
        tmp = Path(f'/tmp/dl-{fid}')
        print(f'\n📥 Baixando {nome} ({size//1024//1024} MB)...', flush=True)
        try:
            baixar(fid, tmp)
        except Exception as e:
            print(f'  ❌ Erro no download: {e}', flush=True)
            falhas.append((nome, str(e)))
            log.write(f'FALHA download: {nome}: {e}\n')
            log.flush()
            continue

        # Converter
        print(f'  🔄 Convertendo pra .md...', flush=True)
        if converter(tmp, output, max_minutes=15):
            linhas = sum(1 for _ in open(output))
            size_md = output.stat().st_size // 1024
            print(f'  ✅ {nome_md}.md ({linhas} linhas, {size_md} KB)', flush=True)
            log.write(f'OK: {nome} → {nome_md}.md ({linhas} linhas)\n')
            sucessos += 1
        else:
            print(f'  ❌ Falha na conversão', flush=True)
            log.write(f'FALHA conversão: {nome}\n')
            falhas.append((nome, 'conversão falhou'))

        tmp.unlink(missing_ok=True)
        log.flush()

    log.write(f'\nFim: {time.strftime("%Y-%m-%d %H:%M:%S")}\n')
    log.write(f'Sucessos: {sucessos} | Falhas: {len(falhas)} | Pulos: {pulos}\n')

print(f'\n{"="*60}', flush=True)
print(f'✅ Sucessos: {sucessos}', flush=True)
print(f'❌ Falhas: {len(falhas)}', flush=True)
print(f'⏭️  Pulos (já existiam): {pulos}', flush=True)
if falhas:
    print(f'\nFalhas:', flush=True)
    for nome, err in falhas:
        print(f'  - {nome}: {err}', flush=True)
print(f'📄 Log: {log_file}', flush=True)