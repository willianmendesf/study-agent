import os, re, glob

DIRS = [
    'data/biblioteca/literatura-brasileira',
    'data/biblioteca/literatura-mundial-classica',
    'data/biblioteca/literatura',
]

KEYS = {
    'romance': r'(^|\n)#{1,4}\s*(CAP[ÍI]TULO|Cap[íi]tulo|Part[e]?\s+\w+\s+[-–—]|Chapter)',
    'parte': r'(^|\n)#{1,4}\s*(PARTE|Parte|LIVRO|Livro|Parte\s+[IVX0-9])',
    'conteudo': r'^\s*[A-ZÁÉÍÓÚÂÊÔÃÕÇ][^\n]{40,200}\.',
}

rows = []
for d in DIRS:
    for p in sorted(glob.glob(os.path.join(d, '*.md'))):
        raw = open(p, encoding='utf-8', errors='replace').read()
        kb = len(raw.encode('utf-8'))
        caps = len(re.findall(KEYS['romance'], raw))
        partes = len(re.findall(KEYS['parte'], raw))
        # densidade de prosa: linhas com mais de 80 chars e que terminam em pontuação
        prosa = sum(1 for L in raw.split('\n') if len(L) > 120 and L.rstrip().endswith(('.', '!', '?', '"', '”')))
        rows.append((kb, prosa, caps, partes, os.path.basename(p), d.split('/')[-1]))

rows.sort()
print(f"{'KB':>7} {'prosa':>6} {'caps':>5} {'part':>5}  arquivo")
for kb, prosa, caps, partes, nome, pasta in rows:
    flag = ''
    if prosa < 40:
        flag = '  <-- TEXTO INCOMPLETO/VAZIO'
    print(f"{kb:>7} {prosa:>6} {caps:>5} {partes:>5}  {nome}{flag}")
