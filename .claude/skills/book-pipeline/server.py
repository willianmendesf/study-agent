#!/usr/bin/env python3
"""
Servidor HTTP que processa 1 livro do Drive por clique.
Com botão "Trazer Todos" — processa sequencialmente em background.
"""
import json, urllib.request, urllib.parse, time, os, subprocess, signal, sys, traceback, threading, logging
from pathlib import Path
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from datetime import datetime

CRED = Path.home() / '.config' / 'gdrive-mcp' / 'gdrive-credentials.json'
KEYS = Path.home() / '.config' / 'gdrive-mcp' / 'gcp-oauth.keys.json'
DATA = Path('/dados/study-agent/data')
LIVROS = DATA / 'estudos' / 'livros'
STATE = Path('/tmp/server-livros-state.json')
LOG_FILE = Path('/tmp/server-livros.log')
TMP = Path('/tmp/drive-one')
PORT = int(os.environ.get('PORT', '8765'))

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[logging.FileHandler(LOG_FILE), logging.StreamHandler(sys.stdout)]
)
log = logging.getLogger('livros')

MAPEAMENTO = {
    'Bibliologia': ('bibliologia', 'BL-'),
    'Cronologia e Contextos Históricos': ('cronologia-contextos-historicos', 'CC-'),
    'Bases da fé': ('bases-da-fe', 'BF-'),
    'Sexual': ('sexual', 'SX-'),
    'Feminilidade Cristã': ('familia-crista', 'FM-'),
    'Familia Cristã': ('familia-crista', 'FC-'),
    'Messias': ('messias', 'MS-'),
    'Pastoral': ('pastoral', 'PS-'),
    'Cultura dos Textos Biblicos': ('cultura-textos-biblicos', 'CT-'),
    'Arqueologia Biblica': ('arqueologia-biblica', 'AQ-'),
    'Hermeneutica e Exegese': ('exegese-hermeneutica', 'HE-'),
    'Simbologias Biblicas': ('referencias-biblicas', 'SB-'),
    'Personagens Bíblicos': ('referencias-biblicas', 'PB-'),
    'Teologia Bíblica': ('teologia-biblica', 'TB-'),
    'Manuais Bíblicos': ('manuais-biblicos', 'MB-'),
    'Dicionário Teológico e Exegético': ('dicionario-teologico', 'DT-'),
    'Línguas Originais': ('linguas-originais', 'LO-'),
    'Igreja': ('igreja-discipulado', 'IG-'),
    'Outros': ('outros', 'OU-'),
    'Teologia': ('teologia', 'TG-'),
    'Teologia Sistemática': ('teologia-sistematica', 'TS-'),
    'História da Igreja': ('historia-igreja', 'HI2-'),
    'Atlas & Mapas Bíblicos': ('atlas-mapas', 'AM-'),
    'Comentários Biblicos': ('comentarios-biblicos', 'CB-'),
    'Dicionários, Enciclopédias e Concordâncias Biblicas': ('dicionarios-concordancias', 'DC-'),
    'Filosofia Cristã': ('filosofia-crista', 'FC2-'),
    'Masculinidade Cristã': ('masculinidade-crista', 'MC-'),
    'Temperamentos': ('temperamentos', 'TP-'),
    'Literatura': ('literatura', 'LT-'),
    'Historia': ('historia', 'HI-'),
}

# Mapeamento por NOME de arquivo (pra subpastas IPB com prefixos numéricos)
MAPEAMENTO_POR_NOME = {
    # IPB subpastas (todos vão pra ipb-documentos com prefixo diferente)
    '2_-_Fides_27-1-2022_-_As_Tres_Dimensoes_do_Ministerio_da_Palavra_-_Valdeci_Santos.pdf': ('ipb-documentos', 'IP-'),
    '4_C_DPowlison_Afimacoes e negacoes.pdf': ('ipb-documentos', 'IP-'),
    '2_N_JBabler_Uma critica do DSM-IV - 2023.pdf': ('ipb-documentos', 'IP-'),
}

def get_destino(item):
    """Decide destino do arquivo. Prioridade: MAPEAMENTO_POR_NOME > regex IPB > MAPEAMENTO."""
    nome = item['name']
    if nome in MAPEAMENTO_POR_NOME:
        return MAPEAMENTO_POR_NOME[nome]
    cat = item['categoria_drive']
    # Subpastas IPB com prefixo (2_Fides, 4_C_D, 6.ATIVIDADES, 09. Romanos, 1- COMENTÁRIO, etc)
    if cat == 'Igreja':
        # Padrão: começa com dígito + separador (_-./espaço)
        if len(nome) > 2 and nome[0].isdigit() and nome[1] in '_-./ ':
            return ('ipb-documentos', 'IP-')
        # Outros arquivos da IPB
        return ('ipb-documentos', 'IP-')
    # Comentários Biblicos: arquivos do Calvino/Hendriksen/etc vão pra comentários
    if cat == 'Comentários Biblicos':
        # Já tem MAPEAMENTO, mas alguns sub-arquivos com prefixo
        return MAPEAMENTO.get(cat, ('comentarios-biblicos', 'CB-'))
    if cat in MAPEAMENTO:
        return MAPEAMENTO[cat]
    # Fallback: _to_organize
    return ('_to_organize', 'XX-')

ROOT_FIDES = '1CsWI_bYHZ8qk6nt1v52HfWcMl0az0BQr'
state_lock = threading.Lock()
worker_lock = threading.Lock()  # Só 1 worker "Trazer Todos" por vez

def get_token():
    with open(CRED) as f:
        creds = json.load(f)
    if time.time() * 1000 < creds['expiry_date'] - 60000:
        return creds['access_token']
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

def listar_recursivo(fid, depth=0, max_depth=5, skip_categories=None):
    if depth > max_depth:
        return []
    if skip_categories is None:
        skip_categories = set()
    try:
        d = api('files', {
            'q': f"'{fid}' in parents and trashed=false",
            'fields': 'files(id,name,mimeType,size)',
            'pageSize': 200,
        })
    except Exception as e:
        log.error(f'Erro listando {fid[:20]}: {e}')
        return []
    items = []
    for f in d.get('files', []):
        # Pular imagens (markitdown não processa)
        if 'image/' in f.get('mimeType', ''):
            continue
        # Pular DOCX antigos que não funcionam
        # if 'officedocument' in f.get('mimeType', '') and int(f.get('size', 0)) == 0:
        #     continue
        items.append({
            'id': f['id'],
            'name': f['name'],
            'mime': f['mimeType'],
            'size': int(f.get('size', 0)),
            'depth': depth,
        })
        if 'folder' in f['mimeType']:
            items.extend(listar_recursivo(f['id'], depth + 1, max_depth, skip_categories))
    return items

def sanitize(nome):
    import unicodedata
    nfkd = unicodedata.normalize('NFKD', nome)
    ascii_name = nfkd.encode('ASCII', 'ignore').decode('ASCII')
    ascii_name = ascii_name.replace(' ', '_').replace('_-_', '-').replace('__', '_')
    ascii_name = ''.join(c if c.isalnum() or c in '-_.' else '-' for c in ascii_name)
    while '--' in ascii_name:
        ascii_name = ascii_name.replace('--', '-')
    return ascii_name.strip('-_.')[:120]

def load_state():
    if STATE.exists():
        try:
            return json.load(open(STATE))
        except:
            pass
    return {'done': [], 'failed': [], 'worker': {'running': False, 'processed': 0, 'errors': 0, 'current': '', 'started': None}}

def save_state(state):
    with state_lock:
        tmp = STATE.with_suffix('.tmp')
        with open(tmp, 'w') as f:
            json.dump(state, f, indent=2)
        tmp.rename(STATE)

def get_inventario():
    cats = api('files', {
        'q': f"'{ROOT_FIDES}' in parents and trashed=false and mimeType='application/vnd.google-apps.folder'",
        'fields': 'files(id,name)',
        'pageSize': 100,
    }).get('files', [])
    inventário = []
    for c in cats:
        if c['name'] == 'MK Reforma Protestante':
            continue
        items = listar_recursivo(c['id'], 0, 5, skip_categories={c['name']})
        for it in items:
            it['categoria_drive'] = c['name']
            it['categoria_id'] = c['id']
            inventário.append(it)
    return inventário

def filter_pending(inventario, state):
    done_set = set(state.get('done', []))
    return [i for i in inventario if i['id'] not in done_set and i['size'] > 0]

def baixar(file_id, dest):
    token = get_token()
    req = urllib.request.Request(
        f'https://www.googleapis.com/drive/v3/files/{file_id}?alt=media',
        headers={'Authorization': f'Bearer {token}'}
    )
    with urllib.request.urlopen(req, timeout=600) as r:
        with open(dest, 'wb') as f:
            f.write(r.read())

def converter(input_path, output_path, timeout_min=10):
    """Pipeline: markitdown → mobi lib (se MOBI) → OCR (se escaneado) → none."""
    # 1) markitdown (PDF/EPUB/DOCX)
    try:
        r = subprocess.run(
            ['uvx', '--from', 'markitdown[all]', 'markitdown', str(input_path), '-o', str(output_path)],
            capture_output=True, text=True, timeout=timeout_min*60
        )
        if r.returncode == 0 and os.path.exists(output_path):
            linhas = sum(1 for _ in open(output_path))
            if linhas > 50:
                return True
            log.info(f'   markitdown deu só {linhas} linhas, tentando OCR')
    except subprocess.TimeoutExpired:
        log.warning(f'   markitdown timeout')
    except Exception as e:
        log.warning(f'   markitdown erro: {e}')

    # 2) MOBI fallback (se for .mobi)
    if input_path.suffix.lower() == '.mobi':
        try:
            r = subprocess.run(
                ['uvx', '--from', 'mobi', 'python', '-c',
                 f"from mobi import extract; r=extract('{input_path}'); print(r[1])"],
                capture_output=True, text=True, timeout=timeout_min*60
            )
            html = None
            for line in r.stdout.split('\n'):
                if 'book.html' in line:
                    import re
                    m = re.search(r"(/tmp/[^']+book\.html)", line)
                    if m:
                        html = m.group(1)
            if html and os.path.exists(html):
                subprocess.run(
                    ['uvx', '--from', 'html2text', 'html2text', html],
                    stdout=open(output_path, 'w'), timeout=timeout_min*60
                )
                # Cleanup
                import shutil
                shutil.rmtree(os.path.dirname(html), ignore_errors=True)
                if os.path.exists(output_path):
                    linhas = sum(1 for _ in open(output_path))
                    if linhas > 10:
                        log.info(f'   mobi→html2text OK ({linhas} linhas)')
                        return True
        except Exception as e:
            log.warning(f'   mobi erro: {e}')

    # 3) OCR via EasyOCR (só para PDFs)
    if input_path.suffix.lower() == '.pdf':
        log.info(f'   Iniciando OCR (EasyOCR, pode demorar 10-30 min para PDFs grandes)...')
        try:
            r = subprocess.run(
                ['python3', '/tmp/ocr-pdf.py', str(input_path), str(output_path)],
                capture_output=True, text=True, timeout=60*60  # 1h max
            )
            if r.returncode == 0 and os.path.exists(output_path):
                linhas = sum(1 for _ in open(output_path))
                if linhas > 10:
                    log.info(f'   OCR OK ({linhas} linhas)')
                    return True
        except subprocess.TimeoutExpired:
            log.warning(f'   OCR timeout (>1h)')
        except Exception as e:
            log.warning(f'   OCR erro: {e}')

    return False

def processar_um(item, state):
    if item['id'] in state.get('done', []):
        return {'status': 'ja_feito'}

    cat = item['categoria_drive']
    mapeamento = get_destino(item)
    if mapeamento is None:
        return {'status': 'sem_mapeamento', 'categoria': cat}

    subdir, prefix = mapeamento
    dest_dir = LIVROS / subdir
    dest_dir.mkdir(parents=True, exist_ok=True)

    out_name = prefix + sanitize(item['name'])
    output = dest_dir / f'{out_name}.md'

    if output.exists() and output.stat().st_size > 500:
        state['done'].append(item['id'])
        save_state(state)
        return {'status': 'pulado'}

    ext = item['name'].rsplit('.', 1)[-1].lower() if '.' in item['name'] else ''
    tmp = TMP / item['id']
    tmp.parent.mkdir(exist_ok=True, parents=True)

    try:
        try:
            baixar(item['id'], tmp)
        except Exception as e:
            return {'status': 'erro_download', 'erro': str(e)}

        if converter(tmp, output):
            try:
                linhas = sum(1 for _ in open(output))
            except:
                linhas = 0
            state['done'].append(item['id'])
            save_state(state)
            return {'status': 'ok', 'linhas': linhas, 'pasta': subdir}
        else:
            # Última tentativa: copiar PDF como referência (se PDF)
            if ext == 'pdf' and tmp.exists():
                try:
                    log.warning(f'   Todas as tentativas falharam, copiando PDF como referência')
                    ref_path = dest_dir / f'{out_name}.pdf.REFERENCE.pdf'
                    import shutil
                    shutil.copy(tmp, ref_path)
                    state['done'].append(item['id'])
                    save_state(state)
                    return {'status': 'copiado_pdf_referencia', 'caminho': str(ref_path)}
                except:
                    pass
            return {'status': 'erro_conversao'}
    finally:
        try:
            if tmp.exists():
                tmp.unlink()
        except:
            pass

# ========== Worker "Trazer Todos" ==========
worker_thread = None

def worker_trazer_todos():
    """Thread que processa todos pendentes em sequência."""
    state = load_state()
    if state.get('worker', {}).get('running'):
        log.warning('Worker já está rodando, ignorando nova chamada')
        return

    with worker_lock:
        state['worker'] = {
            'running': True,
            'processed': 0,
            'errors': 0,
            'current': '',
            'started': datetime.now().isoformat(),
            'last_update': datetime.now().isoformat(),
        }
        save_state(state)

        try:
            inv = state.get('inventario', [])
            pendentes = filter_pending(inv, state)
            pendentes.sort(key=lambda x: x['size'])  # Menor pro maior
            log.info(f'Worker iniciou: {len(pendentes)} livros pendentes')

            for i, item in enumerate(pendentes):
                state['worker']['current'] = item['name']
                state['worker']['last_update'] = datetime.now().isoformat()
                save_state(state)

                log.info(f'[{i+1}/{len(pendentes)}] {item["name"]} ({item["size"]//1024} KB)')
                result = processar_um(item, state)

                if result['status'] == 'ok':
                    state['worker']['processed'] += 1
                    log.info(f'   ✅ {result.get("linhas", 0)} linhas → {result.get("pasta", "?")}')
                elif result['status'] == 'pulado':
                    log.info('   ⏭️  já existe')
                else:
                    state['worker']['errors'] += 1
                    log.warning(f'   ⚠️ {result.get("status")}: {result.get("erro", "")}')

                state['worker']['current'] = ''
                save_state(state)
        except Exception as e:
            log.error(f'Erro no worker: {e}')
            traceback.print_exc()
        finally:
            state['worker']['running'] = False
            state['worker']['ended'] = datetime.now().isoformat()
            save_state(state)
            log.info(f'Worker finalizado: {state["worker"]["processed"]} processados, {state["worker"]["errors"]} erros')

# ========== HTTP ==========
class Handler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        log.debug(f'{self.client_address[0]} - {format % args}')

    def _send(self, code, ctype, body):
        self.send_response(code)
        self.send_header('Content-Type', ctype + '; charset=utf-8')
        self.send_header('Content-Length', str(len(body.encode('utf-8'))))
        self.end_headers()
        self.wfile.write(body.encode('utf-8'))

    def do_GET(self):
        try:
            if self.path == '/':
                self._send(200, 'text/html', self.html_lista())
            elif self.path == '/health':
                state = load_state()
                w = state.get('worker', {})
                self._send(200, 'application/json', json.dumps({
                    'status': 'ok', 'port': PORT,
                    'worker_running': w.get('running', False),
                    'worker_processed': w.get('processed', 0),
                    'worker_errors': w.get('errors', 0),
                }))
            elif self.path == '/worker-status':
                state = load_state()
                self._send(200, 'application/json', json.dumps(state.get('worker', {}), indent=2))
            elif self.path == '/atualizar':
                inv = get_inventario()
                state = load_state()
                state['inventario'] = inv
                state['inventario_atualizado_em'] = datetime.now().isoformat()
                save_state(state)
                self._send(200, 'text/html', f'✅ {len(inv)} arquivos catalogados<br><a href="/">Voltar</a>')
            else:
                self._send(404, 'text/plain', 'not found')
        except Exception as e:
            log.error(f'GET error: {e}')
            traceback.print_exc()
            self._send(500, 'text/plain', f'error: {e}')

    def do_POST(self):
        try:
            if self.path.startswith('/processar/'):
                file_id = self.path[len('/processar/'):].strip()
                self.processar(file_id)
            elif self.path == '/trazer-todos':
                self.trazer_todos()
            else:
                self._send(404, 'text/plain', 'not found')
        except Exception as e:
            log.error(f'POST error: {e}')
            traceback.print_exc()
            try:
                self._send(500, 'text/html', f'<p>Erro: {e}</p>')
            except:
                pass

    def html_lista(self):
        state = load_state()
        inv = state.get('inventario', [])
        pendentes = filter_pending(inv, state)
        pendentes.sort(key=lambda x: x['size'])
        w = state.get('worker', {})

        from collections import defaultdict
        grupos = defaultdict(list)
        for it in pendentes:
            grupos[it['categoria_drive']].append(it)

        total = sum(it['size'] for it in pendentes)
        done_count = len(state.get('done', []))
        updated = state.get('inventario_atualizado_em', 'nunca')
        worker_running = w.get('running', False)
        worker_processed = w.get('processed', 0)
        worker_errors = w.get('errors', 0)
        worker_current = w.get('current', '')

        worker_panel = ''
        if worker_running:
            worker_panel = f'''<div style="background:#fef5e7;padding:12px;margin:12px 0;border-radius:6px;border:1px solid #f6ad55">
<b>🔄 Worker "Trazer Todos" RODANDO</b><br>
Processados: <b>{worker_processed}</b> | Erros: <b>{worker_errors}</b><br>
Atual: <code>{worker_current[:80]}</code>
</div>'''
        elif worker_processed > 0:
            worker_panel = f'''<div style="background:#f0fff4;padding:10px;margin:12px 0;border-radius:6px;border:1px solid #48bb78">
✅ <b>Última execução do worker:</b> {worker_processed} processados, {worker_errors} erros<br>
<a href="/">🔄 Atualizar página</a> | <a href="/worker-status">Ver status completo (JSON)</a>
</div>'''

        html = f'''<!DOCTYPE html>
<html><head><meta charset="utf-8"><meta http-equiv="refresh" content="5">
<title>Drive → Base Study-Agent</title>
<style>
body{{font-family:sans-serif;max-width:1100px;margin:20px auto;padding:0 20px;background:#fafafa;color:#222}}
h1{{color:#333}}.cat{{background:#fff;padding:12px 16px;margin:10px 0;border-radius:8px;box-shadow:0 1px 3px rgba(0,0,0,0.1)}}
.cat h2{{margin:0 0 8px 0;color:#2c5282;font-size:1.05em}}
.item{{display:flex;align-items:center;padding:8px 4px;border-bottom:1px solid #f0f0f0;gap:10px}}
.item:last-child{{border:none}}.info{{flex:1;font-size:0.9em}}.size{{color:#666;font-size:0.85em;width:90px;text-align:right}}
button{{background:#3182ce;color:#fff;border:none;padding:6px 14px;border-radius:4px;cursor:pointer;font-size:0.85em}}
button:hover{{background:#2c5282}}button:disabled{{background:#a0aec0;cursor:not-allowed}}
.btn-all{{background:#38a169;font-size:1em;padding:10px 20px}}
.btn-all:hover{{background:#2f855a}}
.stats{{background:#ebf8ff;padding:14px;border-radius:8px;margin-bottom:16px;display:flex;gap:24px;align-items:center;flex-wrap:wrap}}
</style></head><body>
<h1>📚 Drive 1. Fides → Base Study-Agent</h1>
{worker_panel}
<div class="stats">
<div><b>{len(pendentes)}</b> pendentes</div>
<div><b>{done_count}</b> já processados</div>
<div><b>{total//1024//1024} MB</b> restantes</div>
<div style="font-size:0.85em;color:#666">inv: {updated[:19]}</div>
<form method="GET" action="/atualizar" style="margin-left:auto">
<button type="submit">🔄 Atualizar inventário</button>
</form>
<form method="GET" action="/health" style="margin:0">
<button type="submit" style="background:#48bb78">💚 Health</button>
</form>
</div>
<form method="POST" action="/trazer-todos" style="margin:16px 0;text-align:center">
<button type="submit" class="btn-all" {'disabled' if worker_running else ''}>🚀 TRAZER TODOS (background, sequencial, do menor pro maior)</button>
</form>
'''
        if not pendentes:
            html += '<p style="text-align:center;padding:40px;color:#48bb78;font-size:1.2em">✅ Tudo processado!</p>'

        for cat in sorted(grupos.keys()):
            items = grupos[cat]
            cat_total = sum(it['size'] for it in items)
            html += f'<div class="cat"><h2>📂 {cat} ({len(items)}, {cat_total//1024//1024} MB)</h2>'
            for it in items:
                size_mb = it['size'] / (1024*1024)
                size_color = '#c53030' if size_mb > 100 else '#666'
                html += f'''<div class="item">
<div class="info"><b>{it['name']}</b><br><small>depth={it['depth']} | {it['id'][:18]}...</small></div>
<div class="size" style="color:{size_color}">{size_mb:.1f} MB</div>
<form method="POST" action="/processar/{it['id']}" target="r_{it['id'][-6:]}" style="display:inline">
<button type="submit">▶ Trazer</button>
</form>
<iframe name="r_{it['id'][-6:]}" style="display:none;width:100%;height:60px;border:1px solid #eee;margin-top:4px"></iframe>
</div>'''
            html += '</div>'
        html += '</body></html>'
        return html

    def processar(self, file_id):
        state = load_state()
        inv = state.get('inventario', [])
        item = next((i for i in inv if i['id'] == file_id), None)
        if not item:
            self._send(404, 'text/html', f'<p>ID {file_id} não está no inventário. Clique em "Atualizar inventário".</p>')
            return

        log.info(f'Processando: {item["name"]} ({item["size"]//1024} KB)')
        try:
            result = processar_um(item, state)
            log.info(f'Resultado: {result.get("status")} | {item["name"]}')
        except Exception as e:
            log.error(f'Erro processando {item["name"]}: {e}')
            traceback.print_exc()
            result = {'status': 'erro_excecao', 'erro': str(e)}

        status = result['status']
        if status == 'ok':
            body = f'<p style="color:green;font-size:0.9em">✅ <b>{result["nome"]}</b> → {result["linhas"]} linhas em <code>{result["pasta"]}/</code></p>' if 'nome' in result else f'<p style="color:green;font-size:0.9em">✅ {result.get("linhas", 0)} linhas em <code>{result["pasta"]}/</code></p>'
        elif status == 'pulado':
            body = '<p style="color:orange;font-size:0.9em">⏭️ Já existe</p>'
        elif status == 'sem_mapeamento':
            body = f'<p style="color:red;font-size:0.9em">❌ Categoria {result.get("categoria", "?")} sem mapeamento</p>'
        elif status == 'erro_download':
            body = f'<p style="color:red;font-size:0.9em">❌ Download: {result.get("erro", "")[:80]}</p>'
        elif status == 'erro_conversao':
            body = '<p style="color:red;font-size:0.9em">❌ Conversão falhou (escaneado?)</p>'
        else:
            body = f'<pre style="font-size:0.8em">{json.dumps(result, indent=2)[:300]}</pre>'

        full = f'''<!DOCTYPE html><html><head><meta charset="utf-8">
<style>body{{font-family:sans-serif;padding:8px;margin:0}}.result{{animation:highlight 1s}}
@keyframes highlight{{0%{{background:#fff5a3}}100%{{background:transparent}}}}</style>
</head><body><div class="result">{body}</div>
<script>setTimeout(()=>{{try{{parent.location.reload()}}catch(e){{}}}}, 800);</script>
</body></html>'''
        self._send(200, 'text/html', full)

    def trazer_todos(self):
        """Inicia worker em background que processa TUDO."""
        state = load_state()
        if state.get('worker', {}).get('running'):
            self._send(200, 'text/html', '''<h2>⚠️ Worker já está rodando</h2>
<p>Volte à página principal para acompanhar o progresso.</p>
<a href="/">← Voltar</a>''')
            return

        # Inicia thread
        t = threading.Thread(target=worker_trazer_todos, daemon=True)
        t.start()

        self._send(200, 'text/html', '''<h2>🚀 Worker iniciado!</h2>
<p><b>Processando todos os livros pendentes em background.</b></p>
<p>Vai processar 1 por 1, do menor pro maior. A página recarrega sozinha (5s).</p>
<p>Para acompanhar ao vivo: <code>tail -f /tmp/server-livros.log</code></p>
<a href="/">← Voltar para lista (atualiza sozinha)</a>''')

# ========== Sinais ==========
shutdown_requested = False

def handle_signal(signum, frame):
    global shutdown_requested
    log.info(f'Sinal {signum} recebido, encerrando...')
    shutdown_requested = True

signal.signal(signal.SIGTERM, handle_signal)
signal.signal(signal.SIGINT, handle_signal)

# ========== Main ==========
if __name__ == '__main__':
    TMP.mkdir(parents=True, exist_ok=True)
    log.info(f'🚀 Servidor iniciando na porta {PORT}')
    log.info(f'   Pasta: {LIVROS}')

    state = load_state()
    if not state.get('inventario'):
        log.info('📂 Carregando inventário inicial...')
        try:
            inv = get_inventario()
            state['inventario'] = inv
            state['inventario_atualizado_em'] = datetime.now().isoformat()
            save_state(state)
            log.info(f'   ✅ {len(inv)} arquivos catalogados')
        except Exception as e:
            log.error(f'   ⚠️ Erro inventário: {e}')

    server = ThreadingHTTPServer(('0.0.0.0', PORT), Handler)
    log.info(f'✅ Servidor pronto em http://localhost:{PORT}')
    try:
        while not shutdown_requested:
            server.handle_request()
    except KeyboardInterrupt:
        log.info('🛑 KeyboardInterrupt')
    finally:
        server.server_close()
        log.info('👋 Servidor encerrado')