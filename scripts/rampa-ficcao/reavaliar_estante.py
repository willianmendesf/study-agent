#!/usr/bin/env python3
"""Reavalia os 58 livros da estante do William contra o acervo ATUAL (pos-lote PT-BR).

Para cada titulo, procura no acervo um .md cujo frontmatter/basename case com
autor + palavras-chave do titulo. Atualiza o campo no_acervo_study_agent no YAML.

Uso: python3 scripts/rampa-ficcao/reavaliar_estante.py
"""
import re
import unicodedata
from pathlib import Path

ROOT = Path("/home/willian/study-agent")
BIB = ROOT / "data/biblioteca"
YML = ROOT / "data/perfil/bibliotecario/estante-william.yaml"

IGNORE_DIRS = {"_incoming"}


def sem_acento(s):
    return "".join(c for c in unicodedata.normalize("NFKD", s or "")
                   if not unicodedata.combining(c))


def norm(s):
    return re.sub(r"[^a-z0-9]+", " ", sem_acento(s or "").lower()).strip()


# --- indice do acervo: (autor_norm, titulo_norm) -> caminho relativo ---
indice = []
for md in BIB.rglob("*.md"):
    rel = md.relative_to(BIB)
    if rel.parts[0] in IGNORE_DIRS:
        continue
    nome = norm(md.stem)
    fm = ""
    try:
        head = md.read_text(encoding="utf-8", errors="ignore")[:1500]
        if head.lstrip().startswith("---"):
            fm = head.split("---", 2)[1]
    except Exception:
        pass
    ma = re.search(r'autor: "?([^"\n]+)"?', fm)
    mt = re.search(r'titulo: "?([^"\n]+)"?', fm)
    autor = norm(ma.group(1)) if ma else ""
    titulo = norm(mt.group(1)) if mt else ""
    # nome do arquivo costuma ter "Autor-Obra"
    indice.append((autor, titulo, nome, str(md.relative_to(ROOT))))

# Casos que o casamento automatico erra: decididos a mao.
OVERRIDES = {
    10: ["data/biblioteca/literatura-mundial-classica/antigos/A-Odisseia-Homero.md"],
    38: [],   # "O Processo" = o romance de Kafka; no acervo so ha o manual da IPB
    41: [],   # "Novelas Exemplares" = obra distinta do "Dom Quixote" (que ele tem)
    14: ["data/biblioteca/literatura-mundial-classica/Cervantes-Dom-Quixote.md"],
}

# stopwords para casar titulos
STOP = {"a", "o", "as", "os", "de", "do", "da", "e", "um", "uma", "no", "na",
        "para", "com", "ou", "por", "se", "ao", "dos", "das", "que", "the",
        "volume", "vol", "obras", "coletanea"}

# sinonimos: como o titulo na estante pode nao bater com o do acervo
SINON = {
    "no caminho de swann": ["em busca do tempo perdido", "proust"],
    "odisseia": ["odisseia", "odisseia", "homero"],
    "fausto werther": ["fausto", "goethe"],
    "madame bovary": ["madame bovary", "flaubert"],
    "novelas exemplares": ["dom quixote", "cervantes"],
    "contos": ["contos", "voltaire"],
}


def casa(entrada):
    """(autor, titulo) da estante -> lista de caminhos do acervo."""
    id_, tit, aut = entrada
    t, a = norm(tit), norm(aut)
    chaves_t = [w for w in t.split() if w not in STOP and len(w) > 2]
    chaves_a = [w for w in a.split() if w not in STOP and len(w) > 2]

    if id_ in OVERRIDES:
        return OVERRIDES[id_]
    alvos = SINON.get(t, [t])
    achados = []
    for autor, titulo, nome, caminho in indice:
        if autor:
            if not all(w in autor or w in nome for w in chaves_a[:2]):
                continue
        for alvo in alvos:
            alvo_n = norm(alvo)
            alvo_chaves = [w for w in alvo_n.split() if w not in STOP and len(w) > 2]
            if not alvo_chaves:
                continue
            # o nome do arquivo ou o frontmatter tem que conter as palavras do titulo
            pool = nome + " " + titulo
            if all(w in pool for w in alvo_chaves[:3]):
                achados.append(caminho)
                break
    return sorted(set(achados))


# --- parse do YAML ---
txt = YML.read_text(encoding="utf-8")
entradas = []
for m in re.finditer(
        r"  - id: (\d+)\n    titulo: '((?:[^']|'')*)'\n    autor: '((?:[^']|'')*)'",
        txt):
    entradas.append((int(m.group(1)), m.group(2).replace("''", "'"),
                      m.group(3).replace("''", "'")))

print(f"{len(entradas)} entradas no YAML\n")
relatorio = []
for e in entradas:
    achados = casa(e)
    relatorio.append((e[0], e[1], e[2], achados))
    marca = "SIM" if achados else "nao"
    print(f"#{e[0]:>2} {marca:4s} {e[1][:44]:46s} -> {len(achados)} arquivo(s)")
    for a in achados:
        print(f"        {a}")

n_sim = sum(1 for r in relatorio if r[3])
print(f"\n{n_sim}/{len(relatorio)} da estante agora tem(no) acervo do agente")

# --- atualiza o YAML (idempotente: limpa os registros de acervo anteriores) ---
txt = re.sub(r"^    acervo: .+\n", "", txt, flags=re.M)
for id_, tit, aut, achados in relatorio:
    novo = "    no_acervo_study_agent: " + ("sim" if achados else "nao") + "\n"
    # substitui o campo existente
    pat = re.compile(r"(  - id: %d\n(?:.*\n)*?)    no_acervo_study_agent: \w+\n" % id_)
    m = pat.search(txt)
    if m:
        txt = txt[:m.start(1)] + m.group(1) + novo + txt[m.end():]
    # registra os caminhos encontrados
    if achados:
        pat = re.compile(r"(  - id: %d\n(?:.*\n)*?    no_acervo_study_agent: sim\n)" % id_)
        m = pat.search(txt)
        if m:
            bloco = "".join(f"    acervo: {a}\n" for a in achados)
            txt = txt[:m.end(1)] + bloco + txt[m.end(1):]

YML.write_text(txt, encoding="utf-8")
print(f"\nYAML atualizado: {YML.relative_to(ROOT)}")
