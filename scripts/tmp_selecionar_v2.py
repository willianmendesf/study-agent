#!/usr/bin/env python3
"""Melhora a selecao de candidatos: obra unica, titulo exato, EPUB preferido,
idioma portugues, e evita 'Box'/'Colecao'/'Grandes Obras' multi-volume.
"""
import re
import types
from pathlib import Path

src = Path("/home/willian/study-agent/scripts/tmp_baixar_rampa.py").read_text(encoding="utf-8")
cut = src.split('print(f"ALVOS:')[0]
mod = types.ModuleType("dl")
exec(compile(cut, "dl", "exec"), mod.__dict__)

RUIM = re.compile(r"\b(box|cole[cç][aã]o|grandes obras|obras completas|completo|"
                   r"antologia|volumes?|parte\s*\d|tom[o]?\s*\d|antologia)\b", re.I)
PREFER_EXT = {"epub": 3, "mobi": 2, "azw3": 1, "pdf": 0, "fb2": 0}


def melhor2(books, titulo_pt, autor_pt, titulo_en=""):
    alvo = toks_local(titulo_pt) | toks_local(titulo_en)
    alv_a = toks_local(autor_pt)
    best, best_s = None, -1
    for b in books:
        raw = b.get("title", "")
        autor_raw = b.get("author", "")
        ext = (b.get("extension") or "").lower()
        lang = (b.get("language") or "").lower()
        # 1. idioma: so portugues (ou vazio, que costuma ser PT na busca filtrada)
        if lang and "portugu" not in lang:
            continue
        # 2. penaliza colecao/multi-volume
        pen = 0.25 if RUIM.search(raw) else 0.0
        # 3. cobertura de tokens
        t = toks_local(raw)
        a = toks_local(autor_raw)
        cov = len(alvo & t) / max(1, len(alvo))
        cov_a = len(alv_a & a) / max(1, len(alv_a))
        s = cov * 0.62 + cov_a * 0.28 - pen
        # 4. bonus: titulo PT literal contido (normalizado)
        tpl = sem_local(titulo_pt)
        if len(tpl) > 6 and tpl in sem_local(raw):
            s += 0.22
        # 5. bonus: autor literal contido
        if len(sem_local(autor_pt)) > 3 and sem_local(autor_pt).split()[0] in sem_local(autor_raw):
            s += 0.10
        # 6. bonus de formato
        s += 0.06 * PREFER_EXT.get(ext, 0) / 3
        # 7. penaliza traducao de bolso / edicoes abreviadas
        if re.search(r"abreviat|resum|adapt|bolso|cl[aá]ssicos? de ouro", raw, re.I):
            s -= 0.15
        if s > best_s:
            best, best_s = b, s
    return (best, round(best_s, 3)) if best and best_s >= 0.52 else (None, round(best_s, 3))


def toks_local(s):
    STOP = {"o", "a", "os", "as", "de", "do", "da", "dos", "das", "e", "em", "no", "na",
            "um", "uma", "para", "com", "que", "se", "por", "ao", "a", "the", "of", "and"}
    return {t for t in re.findall(r"[a-z0-9]+", sem_local(s)) if t not in STOP and len(t) > 2}


def sem_local(s):
    import unicodedata
    return "".join(c for c in unicodedata.normalize("NFKD", s or "")
                   if not unicodedata.combining(c)).lower()


TESTES = [
    ("Dostoyevsky-Crime-e-Castigo", "Crime e Castigo Dostoiévski", "Crime e Castigo", "Dostoiévski", "Crime and Punishment"),
    ("Dostoyevsky-Irmãos-Karamázov", "Os Irmãos Karamázov Dostoiévski", "Os Irmãos Karamázov", "Dostoiévski", "Brothers Karamazov"),
    ("Tolstoi-Guerra-e-Paz", "Guerra e Paz Tolstói", "Guerra e Paz", "Tolstói", "War and Peace"),
    ("Austen-Orgulho-e-Preconceito", "Orgulho e Preconceito Jane Austen", "Orgulho e Preconceito", "Austen", "Pride and Prejudice"),
    ("Dante-Divina-Comedia", "A Divina Comédia Dante", "A Divina Comédia", "Dante", "Divine Comedy"),
    ("Agostinho-Cidade-de-Deus", "A Cidade de Deus Agostinho", "A Cidade de Deus", "Agostinho", "City of God"),
    ("Chesterton-Ortodoxia", "Ortodoxia Chesterton", "Ortodoxia", "Chesterton", "Orthodoxy"),
    ("Twain-Tom-Sawyer", "As Aventuras de Tom Sawyer Mark Twain", "As Aventuras de Tom Sawyer", "Twain", "Tom Sawyer"),
]
for slug, q, tit, aut, alt in TESTES:
    books = mod.busca(q, "zlib")
    cand, sc = melhor2(books, tit, aut, alt)
    print(f"{slug:36s} score={sc} -> {cand.get('title') if cand else 'NENHUM'} "
          f"| {cand.get('author') if cand else ''} | {cand.get('extension') if cand else ''} "
          f"| {cand.get('filesizeString') if cand else ''}")
