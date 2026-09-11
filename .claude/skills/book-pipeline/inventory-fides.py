#!/usr/bin/env python3
"""Inventário recursivo de Drive / 1. Fides / <categoria>.
Uso: drive-inventory.py <parent_id>
Salva resultado em /tmp/drive-inventory.json
"""
import sys, json, urllib.request, urllib.parse

CRED_FILE = '/home/willianmendesf/.config/gdrive-mcp/gdrive-credentials.json'
API = 'https://www.googleapis.com/drive/v3/files'

with open(CRED_FILE) as f:
    token = json.load(f)['access_token']

def api(path, params):
    qs = urllib.parse.urlencode(params, quote_via=urllib.parse.quote)
    url = f'{API}/{path}?{qs}'
    req = urllib.request.Request(url, headers={'Authorization': f'Bearer {token}'})
    with urllib.request.urlopen(req) as r:
        return json.load(r)

def listar_recursivo(folder_id, depth=0, max_depth=4):
    if depth > max_depth:
        return []
    d = api('files', {
        'q': f"'{folder_id}' in parents and trashed=false",
        'fields': 'files(id,name,mimeType,size,parents)',
        'pageSize': 200,
    })
    items = []
    for f in d.get('files', []):
        if 'folder' in f['mimeType']:
            items.extend(listar_recursivo(f['id'], depth+1, max_depth))
        else:
            items.append(f)
    return items

parent = sys.argv[1] if len(sys.argv) > 1 else '1CsWI_bYHZ8qk6nt1v52HfWcMl0az0BQr'
items = listar_recursivo(parent)
print(f'Total: {len(items)} arquivos', file=sys.stderr)
print(json.dumps(items, indent=2, ensure_ascii=False))