#!/usr/bin/env python3
"""study-lint — barreira determinística (não depende do modelo) contra os gaps que IAs menores deixam.

Uso:  python3 .claude/scripts/study-lint.py [--root DIR] [--strict] [--update-baseline]
Saída: exit 1 se houver ERRO novo (fora do baseline). Só stdlib + PyYAML vendorizado.
Baseline: data/perfil/bibliotecario/lint-baseline.txt  (problemas conhecidos, um por linha).
"""
import argparse, glob, os, re, subprocess, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'vendor'))
import yaml

ap = argparse.ArgumentParser()
ap.add_argument('--root', default=os.getcwd())
ap.add_argument('--strict', action='store_true', help='ignora o baseline')
ap.add_argument('--update-baseline', action='store_true')
a = ap.parse_args()
ROOT = os.path.abspath(a.root)
D = os.path.join(ROOT, 'data')
BASE = os.path.join(D, 'perfil', 'bibliotecario', 'lint-baseline.txt')
issues = []  # (nivel, chave, mensagem)

def err(k, m): issues.append(('ERRO', k, m))
def warn(k, m): issues.append(('AVISO', k, m))
def rel(p): return os.path.relpath(p, ROOT)

def load(p):
    try:
        return list(yaml.safe_load_all(open(p, encoding='utf8')))
    except Exception as e:
        m = getattr(e, 'problem_mark', None)
        err('yaml:' + rel(p), f'YAML inválido{" (linha %d)" % (m.line + 1) if m else ""}: {str(getattr(e, "problem", e))[:70]}')
        return None

# ---------- skills ----------
skills_dir = os.path.join(ROOT, '.claude', 'skills')
skills = set(d for d in os.listdir(skills_dir) if os.path.isdir(os.path.join(skills_dir, d))) if os.path.isdir(skills_dir) else set()
for s in sorted(skills):
    p = os.path.join(skills_dir, s, 'SKILL.md')
    if not os.path.exists(p): err('skill:' + s, 'skill sem SKILL.md'); continue
    t = open(p, encoding='utf8', errors='replace').read()
    m = re.match(r'^---\n(.*?)\n---', t, re.S)
    try: fm = yaml.safe_load(m.group(1)) if m else None
    except Exception: fm = None
    if not isinstance(fm, dict): err('skill:' + s, 'SKILL.md sem frontmatter YAML válido'); continue
    if not fm.get('description'): err('skill:' + s, 'SKILL.md sem description')
    if fm.get('name') != s: warn('skill:' + s, f'name do frontmatter ({fm.get("name")}) != pasta')

def ghost_skills(txt):
    return sorted(r for r in set(re.findall(r'\b((?:study|estudo-fluxo)-[a-z0-9]+(?:-[a-z0-9]+)*)', txt))
                  if r not in skills and not r.startswith(('study-agent', 'study-lint')) and not r.endswith('-'))

# ---------- biblioteca (KBs) ----------
def resolve(p):
    p = p.strip().strip('"\'')
    if not p: return None
    for pre in ('/dados/study-agent/', '/home/study-agent/'):
        if p.startswith(pre): return os.path.join(ROOT, p[len(pre):])
    if p.startswith('data/'): return os.path.join(ROOT, p)
    if p.startswith('/estudos/') or p.startswith('estudos/'): return os.path.join(D, p.lstrip('/'))
    return p if os.path.isabs(p) else os.path.join(D, p)

pool = set()
kbtags = set()
kbs = sorted(glob.glob(os.path.join(D, 'biblioteca', '**', '*.yaml'), recursive=True))
for p in kbs:
    docs = load(p)
    if docs is None: continue
    tags, dis = None, False
    for d in docs:
        if isinstance(d, dict):
            tags = d.get('tags', tags); dis = d.get('disabled', dis)
    if not tags: err('kb-tags:' + rel(p), 'KB sem `tags` (ou tags vazia) — invisível para especialistas'); 
    elif not dis: pool.update(str(x) for x in tags); kbtags.update(str(x) for x in tags)
    def walk(o):
        if isinstance(o, dict):
            if 'caminho_md' in o and isinstance(o['caminho_md'], str):
                tp = resolve(o['caminho_md'])
                st = str(o.get('status', ''))
                if tp and not os.path.exists(tp) and not re.search(r'ocr_pendente|pendente|ausente|removid|duplicata', st):
                    err('caminho:' + rel(p) + '::' + o['caminho_md'][:110], 'caminho_md não existe')
            for v in o.values(): walk(v)
        elif isinstance(o, list):
            for v in o: walk(v)
    for d in docs: walk(d)
    titles = []
    def collect(o):
        if isinstance(o, dict):
            if 'caminho_md' in o and o.get('titulo'): titles.append(str(o['caminho_md']).strip().lower())
            for v in o.values(): collect(v)
        elif isinstance(o, list):
            for v in o: collect(v)
    for d in docs: collect(d)
    for t in sorted(set(x for x in titles if titles.count(x) > 1)):
        err('duplicata:' + rel(p) + '::' + t[:80], 'mesmo caminho_md listado duas vezes na mesma KB')

# ---------- especialistas ----------
sp = {}
for p in sorted(glob.glob(os.path.join(D, 'perfil', 'especialistas', '*.yaml'))):
    n = os.path.basename(p)[:-5]
    docs = load(p)
    if not docs: continue
    e = docs[0].get('especialista') if isinstance(docs[0], dict) else None
    if not isinstance(e, dict): err('esp:' + n, 'falta o bloco raiz `especialista:`'); continue
    sp[n] = e
    for f in ('nome', 'titulo', 'dominio', 'quando_ativar'):
        if not e.get(f): err(f'esp:{n}:{f}', f'especialista sem campo `{f}`')
    if e.get('nome') and e['nome'] != n: err(f'esp:{n}:nome', f'nome ({e["nome"]}) != arquivo')
    tipo = e.get('tipo', 'sistema' if n == 'kairos' else 'conteudo')
    tg = e.get('tags_do_dominio') or []
    if n not in ('bibliotecario',) and tipo != 'sistema' and not tg: err(f'esp:{n}:tags', 'especialista de conteúdo sem tags_do_dominio')
    miss = [t for t in tg if str(t) not in pool]
    if miss and pool: warn(f'esp:{n}:tags-sem-kb', f'tags sem nenhuma KB no pool: {miss}')
    txt_sp = open(p, encoding='utf8').read()
    for cp in sorted(set(re.findall(r'data/[A-Za-z0-9_\-./]+\.(?:yaml|md|json|sh)', txt_sp))):
        if '<' in cp or '*' in cp: continue
        if not os.path.exists(os.path.join(ROOT, cp)): err(f'esp:{n}:path:{cp}', 'especialista cita arquivo inexistente')
    g = ghost_skills(txt_sp)
    if g: err(f'esp:{n}:skills', f'referencia skills inexistentes: {g}')

pm = os.path.join(D, 'perfil', 'perfis.md')
if os.path.exists(pm):
    t = open(pm, encoding='utf8').read()
    rows = set(re.findall(r'^\| \d+ \| \*\*(\w+)\*\*', t, re.M))
    for n in sorted(set(sp) - rows): err('perfis:' + n, 'especialista sem linha em data/perfil/perfis.md (Regra 8)')
    for n in sorted(rows - set(sp)): err('perfis:' + n, 'perfis.md lista especialista sem .yaml')
    m = re.search(r'^total_especialistas:\s*(\d+)', t, re.M)
    if m and int(m.group(1)) != len(sp) and sp: err('perfis:total', f'total_especialistas={m.group(1)} mas há {len(sp)} .yaml')
rp = os.path.join(D, 'perfil', 'relacionamentos.yaml')
if os.path.exists(rp):
    docs = load(rp)
    if docs and isinstance(docs[0], dict):
        rel_ = docs[0].get('relacionamentos') or {}
        for k, v in rel_.items():
            if sp and k not in sp: err('rel:' + k, 'relacionamentos.yaml cita especialista inexistente')
            for t2 in (v.get('interage_com') or {}) if isinstance(v, dict) else []:
                if sp and t2 not in sp: err(f'rel:{k}->{t2}', 'interage_com aponta para especialista inexistente')

for n, e in sp.items():
    tipo = e.get('tipo', 'sistema' if n == 'kairos' else 'conteudo')
    tg = set(str(x) for x in (e.get('tags_do_dominio') or []))
    if tipo != 'sistema' and n != 'bibliotecario' and tg and not (tg & kbtags):
        err(f'esp:{n}:sem-kb', 'especialista não enxerga NENHUMA KB (nenhuma tag cruza) — falta material ou tag')

# ---------- framework ----------
for f in ('CLAUDE.md', 'ORQUESTRADOR.md', 'README.md', 'AGENTS.md'):
    p = os.path.join(ROOT, f)
    if os.path.exists(p):
        g = [x for x in ghost_skills(open(p, encoding='utf8').read()) if x not in ('estudo-fluxo-01-06', 'study-agent-pull', 'study-agent-last-pull')]
        if g: err('doc:' + f, f'cita skills inexistentes: {g}')
cfgp = os.path.join(ROOT, '.claude', 'config.yaml')
if os.path.exists(cfgp): load(cfgp)

# ---------- segredos rastreados ----------
try:
    tracked = subprocess.run(['git', '-C', D, 'ls-files'], capture_output=True, text=True).stdout.split('\n')
    for f in tracked:
        if re.search(r'(^|/)(\.env|zlib-credentials\.yaml|.*credentials.*\.(json|yaml|yml)|.*\.pem|id_rsa)$', f):
            err('segredo:' + f, 'arquivo de credencial rastreado pelo git')
except Exception: pass

# ---------- baseline ----------
keys = sorted(set(k for lv, k, m in issues if lv == 'ERRO'))
if a.update_baseline:
    os.makedirs(os.path.dirname(BASE), exist_ok=True)
    open(BASE, 'w', encoding='utf8').write('# study-lint baseline — problemas CONHECIDOS (não bloqueiam). Não adicione novos aqui: corrija-os.\n' + '\n'.join(keys) + '\n')
    print(f'baseline gravado: {len(keys)} entradas'); sys.exit(0)
known = set()
if os.path.exists(BASE) and not a.strict:
    known = set(l.strip() for l in open(BASE, encoding='utf8') if l.strip() and not l.startswith('#'))
new = [(lv, k, m) for lv, k, m in issues if lv == 'ERRO' and k not in known]
old = [(lv, k, m) for lv, k, m in issues if lv == 'ERRO' and k in known]
for lv, k, m in new: print(f'ERRO   {k}\n       {m}')
for lv, k, m in issues:
    if lv == 'AVISO': print(f'AVISO  {k}: {m}')
print(f'\nstudy-lint: {len(new)} erro(s) novo(s), {len(old)} conhecido(s) no baseline, {sum(1 for i in issues if i[0]=="AVISO")} aviso(s)')
sys.exit(1 if new else 0)
