#!/usr/bin/env python3
"""Download em lote das traducoes PT-BR / lacunas para a rampa de ficcao.

Fluxo z-library eAPI: search -> (id, hash) -> /file -> downloadLink -> baixa em
data/biblioteca/_incoming/. Salva um JSONL de log para o bibliotecario processar.
"""
import json
import re
import subprocess
import sys
import time
import unicodedata
from pathlib import Path

ROOT = Path("/home/willian/study-agent")
INCOMING = ROOT / "data" / "biblioteca" / "_incoming"
LOG = ROOT / "data" / "perfil" / "bibliotecario" / "logs" / "rampa-ficcao-downloads.jsonl"
INCOMING.mkdir(parents=True, exist_ok=True)
LOG.parent.mkdir(parents=True, exist_ok=True)

DOM = "z-lib.gd"
UA = "Mozilla/5.0 (Android 12; Mobile)"
CREDS = json.load(open(Path.home() / ".zlib-mcp" / ".account-env-cache.json"))

# importa a conta principal do yaml do perfil
import re as _re
_txt = (ROOT / "data/perfil/bibliotecario/zlib-credentials.yaml").read_text(encoding="utf-8")
_blocks = _txt.split("- alias:")
for _i, _b in enumerate(_blocks[1:]):
    _rid = _re.search(r"remix_id:\s*'?([0-9]+)'?", _b)
    _rkey = _re.search(r"remix_key:\s*'?([A-Za-z0-9]+)'?", _b)
    if _rid and _rkey:
        nm = ["zlib", "zlib2", "zlib3", "zlib4"][_i] if _i < 4 else None
        if nm:
            CREDS.setdefault(nm, {}).update(ZLIB_REMIX_ID=_rid.group(1),
                                           ZLIB_REMIX_KEY=_rkey.group(1))

CONTAS = [c for c in ["zlib", "zlib2", "zlib3", "zlib4"] if c in CREDS]


def cookie(acct):
    e = CREDS[acct]
    return f"remix_userid={e['ZLIB_REMIX_ID']}; remix_userkey={e['ZLIB_REMIX_KEY']}"


def curl(args, timeout=60):
    r = subprocess.run(["curl", "-sS", "-m", str(timeout), *args],
                       capture_output=True, text=True)
    return r.stdout


def sem(s):
    return "".join(c for c in unicodedata.normalize("NFKD", s or "")
                   if not unicodedata.combining(c)).lower()


STOP = {"o", "a", "os", "as", "de", "do", "da", "dos", "das", "e", "em", "no", "na",
        "um", "uma", "para", "com", "que", "se", "por", "ao", "a", "the", "of", "and"}


def toks(s):
    return {t for t in re.findall(r"[a-z0-9]+", sem(s)) if t not in STOP and len(t) > 2}


def log(ev, **kw):
    rec = {"ts": time.strftime("%Y-%m-%dT%H:%M:%S"), "event": ev, **kw}
    with LOG.open("a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")


def usa_conta(acct):
    """Consome 1 slot de cota da conta; devolve False se estourou."""
    out = curl([f"https://{DOM}/eapi/user/profile", "-H", f"User-Agent: {UA}",
                "-b", cookie(acct)], timeout=30)
    try:
        u = json.loads(out).get("user", {})
    except Exception:
        return True
    return u.get("downloads_today", 0) < u.get("downloads_limit", 10)


def busca(query, acct, languages="portuguese", limit=25):
    args = [f"https://{DOM}/eapi/book/search", "-H", f"User-Agent: {UA}",
            "-b", cookie(acct), "-d", f"message={query}&limit={limit}"]
    if languages:
        args += ["-d", f"languages[]={languages}"]
    out = curl(args, timeout=45)
    try:
        d = json.loads(out)
    except Exception:
        return []
    if not d.get("success"):
        return []
    return d.get("books", [])


def melhor(books, titulo_pt, autor_pt, titulo_en=""):
    """Escolhe o melhor candidato por sobreposicao de tokens do titulo/autor."""
    alvo = toks(titulo_pt) | toks(titulo_en)
    alv_a = toks(autor_pt)
    best, best_s = None, -1
    for b in books:
        t = toks(b.get("title", ""))
        a = toks(b.get("author", ""))
        cov = len(alvo & t) / max(1, len(alvo))
        cov_a = len(alv_a & a) / max(1, len(alv_a))
        s = cov * 0.7 + cov_a * 0.3
        # bonus se o titulo contem o titulo_pt literal
        if sem(titulo_pt)[:18] in sem(b.get("title", "")):
            s += 0.25
        if s > best_s:
            best, best_s = b, s
    return (best, round(best_s, 3)) if best and best_s >= 0.45 else (None, round(best_s, 3))


def baixa(book, acct, slug):
    bid, bh = book.get("id"), book.get("hash")
    out = curl([f"https://{DOM}/eapi/book/{bid}/{bh}/file", "-H", f"User-Agent: {UA}",
                "-b", cookie(acct)], timeout=45)
    try:
        d = json.loads(out)
    except Exception:
        return None, "resposta-file nao-JSON"
    if not d.get("success"):
        return None, d.get("error", "erro desconhecido")
    link = d.get("file", {}).get("downloadLink")
    if not link:
        return None, "sem downloadLink"
    ext = d.get("file", {}).get("extension", "epub")
    dest = INCOMING / f"{slug}.{ext}"
    r = subprocess.run(["curl", "-sSL", "-m", "300", "-o", str(dest),
                        "-H", f"User-Agent: {UA}", link], capture_output=True, text=True)
    if not dest.exists() or dest.stat().st_size < 20000:
        return None, "arquivo vazio/pequeno demais"
    return dest, f"{dest.stat().st_size//1024}KB {ext}"


# (slug, query, titulo_pt, autor_pt, titulo_alternativo_en)
ALVOS = [
    # -- Dostoievski (buraco zero na estante do William) --
    ("Dostoievski-Crime-e-Castigo", "Crime e Castigo Dostoiévski", "Crime e Castigo", "Dostoiévski", "Crime and Punishment"),
    ("Dostoievski-Irmãos-Karamázov", "Os Irmãos Karamázov Dostoiévski", "Os Irmãos Karamázov", "Dostoiévski", "Brothers Karamazov"),
    ("Dostoievski-O-Idiota", "O Idiota Dostoiévski", "O Idiota", "Dostoiévski", "The Idiot"),
    ("Dostoievski-Os-Demônios", "Os Demônios Dostoiévski", "Os Demônios", "Dostoiévski", "Demons"),
    ("Dostoievski-O-Jogador", "O Jogador Dostoiévski", "O Jogador", "Dostoiévski", "The Gambler"),
    # -- Tolstoi --
    ("Tolstoi-Guerra-e-Paz", "Guerra e Paz Tolstói", "Guerra e Paz", "Tolstói", "War and Peace"),
    ("Tolstoi-Anna-Karênina", "Anna Karênina Tolstói", "Anna Karênina", "Tolstói", "Anna Karenina"),
    ("Tolstoi-Ressurreição", "Ressurreição Tolstói", "Ressurreição", "Tolstói", "Resurrection"),
    # -- Austen (a prova de Literatura da IPB e em PT) --
    ("Austen-Orgulho-e-Preconceito", "Orgulho e Preconceito Jane Austen", "Orgulho e Preconceito", "Austen", "Pride and Prejudice"),
    ("Austen-Jane-Eyre", "Jane Eyre Charlotte Brontë", "Jane Eyre", "Brontë", "Jane Eyre"),
    ("Austen-Emma", "Emma Jane Austen", "Emma", "Austen", "Emma"),
    ("Austen-Sanditon", "Sanditon Jane Austen", "Sanditon", "Austen", "Sanditon"),
    # -- Dickens --
    ("Dickens-Grandes-Esperanças", "Grandes Esperanças Charles Dickens", "Grandes Esperanças", "Dickens", "Great Expectations"),
    ("Dickens-Casa-Cassandra", "Casa de Cassandra Dickens", "Casa de Cassandra", "Dickens", "Bleak House"),
    ("Dickens-David-Copperfield", "David Copperfield Dickens", "David Copperfield", "Dickens", "David Copperfield"),
    ("Dickens-Nicholas-Nickleby", "Nicholas Nickleby Dickens", "Nicholas Nickleby", "Dickens", "Nicholas Nickleby"),
    # -- Agostinho / Dante (6 classicos do acervo estao em ingles) --
    ("Agostinho-Cidade-de-Deus", "A Cidade de Deus Agostinho", "A Cidade de Deus", "Agostinho", "City of God"),
    ("Agostinho-Confissoes", "Confissões de Santo Agostinho", "Confissões", "Agostinho", "Confessions"),
    ("Dante-Divina-Comedia", "A Divina Comédia Dante", "A Divina Comédia", "Dante", "Divine Comedy"),
    # -- Flaubert / Proust / classicos PT que faltam no acervo --
    ("Flaubert-Madame-Bovary", "Madame Bovary Gustave Flaubert", "Madame Bovary", "Flaubert", "Madame Bovary"),
    ("Proust-Em-Busca-do-Tempo-Perdido-1", "Em Busca do Tempo Perdido Proust", "Em Busca do Tempo Perdido", "Proust", "Swann's Way"),
    # -- Anglo-saxoes --
    ("Melville-Moby-Dick", "Moby Dick Herman Melville", "Moby Dick", "Melville", "Moby Dick"),
    ("Eliot-George-Middlemarch", "Middlemarch George Eliot", "Middlemarch", "Eliot", "Middlemarch"),
    ("Shelley-Frankenstein", "Frankenstein Mary Shelley", "Frankenstein", "Shelley", "Frankenstein"),
    ("Twain-Tom-Sawyer", "As Aventuras de Tom Sawyer Mark Twain", "As Aventuras de Tom Sawyer", "Twain", "Tom Sawyer"),
    ("Twain-Huckleberry-Finn", "As Aventuras de Huckleberry Finn Twain", "Huckleberry Finn", "Twain", "Huckleberry Finn"),
    ("Orwell-1984", "1984 George Orwell", "1984", "Orwell", "Nineteen Eighty-Four"),
    ("Orwell-A-Revolucao-dos-Animais", "A Revolução dos Animais Orwell", "A Revolução dos Animais", "Orwell", "Animal Farm"),
    ("Joyce-Retratos", "Retratos James Joyce", "Retratos", "Joyce", "Dubliners"),
    ("Woolf-A-Mrs-Dalloway", "A Mrs Dalloway Virginia Woolf", "Mrs Dalloway", "Woolf", "Mrs Dalloway"),
    ("Maupassant-Contos", "Contos Guy de Maupassant", "Contos", "Maupassant", "Contos"),
    # --等部门: classicos PT que faltam --
    ("Homero-Odissia", "A Odisséia Homero", "A Odisséia", "Homero", "Odyssey"),
    ("Virgilio-Eneida", "A Eneida Virgílio", "A Eneida", "Virgílio", "Aeneid"),
    ("Goethe-Fausto", "Fausto Goethe", "Fausto", "Goethe", "Faust"),
    ("Hugo-Les-Miserables", "Les Misérables Victor Hugo", "Les Misérables", "Hugo", "Les Misérables"),
    ("Kipling-Kim", "Kim Rudyard Kipling", "Kim", "Kipling", "Kim"),
    # -- trilha cristã (gap de intencao: zero ficcao cristiana na estante) --
    ("Chesterton-Ortodoxia", "Ortodoxia Chesterton", "Ortodoxia", "Chesterton", "Orthodoxy"),
    ("Chesterton-O-Homem-que-foi-Quinta-feira", "O Homem que foi Quinta-feira Chesterton", "O Homem que foi Quinta-feira", "Chesterton", "The Man Who Was Thursday"),
    ("Lewis-O-Problema-da-Dor", "O Problema da Dor C S Lewis", "O Problema da Dor", "Lewis", "The Problem of Pain"),
    ("Bunyan-O-Peregrino", "O Peregrino John Bunyan", "O Peregrino", "Bunyan", "Pilgrim's Progress"),
    ("Greene-O-Poder-e-a-Gloria", "O Poder e a Glória Graham Greene", "O Poder e a Glória", "Greene", "The Power and the Glory"),
    ("OConnor-A-Wise-Blood", "A Wise Blood Flannery O'Connor", "A Wise Blood", "O'Connor", "Wise Blood"),
]

print(f"ALVOS: {len(ALVOS)} | contas: {CONTAS}")
print(f"dominio: {DOM} | destino: {INCOMING}\n")

# cache de busca por query para nao repetir requests
_cache = {}
baixados, falhas, sem_cota = 0, 0, 0
conta_idx = 0
acct = CONTAS[conta_idx]
t0 = time.time()

for slug, query, tit, aut, alt in ALVOS:
    if time.time() - t0 > 2400:
        print("!! tempo esgotado, parando")
        break
    # rotaciona conta
    if not usa_conta(acct):
        prox = [c for c in CONTAS if c != acct]
        if not prox:
            print("!! todas as contas sem cota")
            sem_cota = len(ALVOS) - baixados - falhas
            break
        acct = prox[0]
        print(f"   (cota de {acct} esgotada -> {acct})")
    if query not in _cache:
        _cache[query] = busca(query, acct)
        time.sleep(1.2)
    books = _cache[query]
    cand, score = melhor(books, tit, aut, alt)
    if not cand:
        print(f"[FALHA-CAND] {slug}: sem candidato (n={len(books)} melhor={score})")
        log("sem-candidato", slug=slug, query=query, n=len(books), score=score)
        falhas += 1
        continue
    dest, info = baixa(cand, acct, slug)
    if dest is None:
        print(f"[FALHA-DL] {slug}: {info}")
        log("falha-download", slug=slug, erro=info, book=cand.get("title"))
        falhas += 1
        continue
    baixados += 1
    print(f"[OK] {slug:45s} {info:12s} <- {cand.get('title')[:60]} | {cand.get('author')[:30]}")
    log("baixado", slug=slug, arquivo=dest.name, info=info,
        zlib_title=cand.get("title"), zlib_author=cand.get("author"),
        zlib_id=cand.get("id"), zlib_hash=cand.get("hash"), conta=acct)

print(f"\n=== FIM: baixados={baixados} falhas={falhas} sem_cota={sem_cota} ===")
