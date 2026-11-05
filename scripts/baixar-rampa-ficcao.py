#!/usr/bin/env python3
"""Lote de aquisicao para a rampa de ficcao — traducoes PT-BR + lacunas.

search -> seleciona obra unica em EPUB/PT -> /file -> downloadLink -> _incoming/
Rotaciona entre as 4 contas do z-library (10 downloads cada = 40/dia).
Log JSONL em data/perfil/bibliotecario/logs/rampa-ficcao-downloads.jsonl
"""
import json
import re
import subprocess
import time
import types
import unicodedata
from pathlib import Path

SRC = Path("/home/willian/study-agent/scripts/tmp_baixar_rampa.py")
V2 = Path("/home/willian/study-agent/scripts/tmp_selecionar_v2.py")

src = SRC.read_text(encoding="utf-8").split('print(f"ALVOS:')[0]
mod = types.ModuleType("dl")
exec(compile(src, "dl", "exec"), mod.__dict__)

v2src = V2.read_text(encoding="utf-8").split("TESTES = [")[0]
mod2 = types.ModuleType("dl2")
exec(compile(v2src, "dl2", "exec"), mod2.__dict__)

LOG = mod.LOG
DOM = mod.DOM
UA = mod.UA
INCOMING = mod.INCOMING


def log(ev, **kw):
    rec = {"ts": time.strftime("%Y-%m-%dT%H:%M:%S"), "event": ev, **kw}
    with LOG.open("a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")


def cota(acct):
    out = mod.curl([f"https://{DOM}/eapi/user/profile", "-H", f"User-Agent: {UA}",
                    "-b", mod.cookie(acct)], timeout=30)
    try:
        u = json.loads(out).get("user", {})
        return u.get("downloads_today", 0), u.get("downloads_limit", 10)
    except Exception:
        return 0, 10


ALVOS = [
    # -- Dostoievski: zero na estante do William --
    ("Dostoievski-Crime-e-Castigo", "Crime e Castigo Dostoiévski", "Crime e Castigo", "Dostoiévski", "Crime and Punishment"),
    ("Dostoievski-Irmãos-Karamázov", "Os Irmãos Karamázov Dostoiévski", "Os Irmãos Karamázov", "Dostoiévski", "Brothers Karamazov"),
    ("Dostoievski-O-Idiota", "O Idiota Dostoiévski", "O Idiota", "Dostoiévski", "The Idiot"),
    ("Dostoievski-Os-Demônios", "Os Demônios Dostoiévski", "Os Demônios", "Dostoiévski", "Demons"),
    ("Dostoievski-O-Jogador", "O Jogador Dostoiévski", "O Jogador", "Dostoiévski", "The Gambler"),
    # -- Tolstoi: zero na estante do William --
    ("Tolstoi-Guerra-e-Paz", "Guerra e Paz Tolstói", "Guerra e Paz", "Tolstói", "War and Peace"),
    ("Tolstoi-Anna-Karênina", "Anna Karênina Tolstói", "Anna Karênina", "Tolstói", "Anna Karenina"),
    ("Tolstoi-Ressurreição", "Ressurreição Tolstói", "Ressurreição", "Tolstói", "Resurrection"),
    # -- Austen: ausente, e eixo da prova de Literatura da IPB --
    ("Austen-Orgulho-e-Preconceito", "Orgulho e Preconceito Jane Austen", "Orgulho e Preconceito", "Austen", "Pride and Prejudice"),
    ("Brontë-Jane-Eyre", "Jane Eyre Charlotte Brontë", "Jane Eyre", "Brontë", "Jane Eyre"),
    ("Austen-Emma", "Emma Jane Austen", "Emma", "Austen", "Emma"),
    # -- Dickens: no acervo so em ingles --
    ("Dickens-Grandes-Esperanças", "Grandes Esperanças Charles Dickens", "Grandes Esperanças", "Dickens", "Great Expectations"),
    ("Dickens-Casa-Cassandra", "Casa de Cassandra Dickens", "Casa de Cassandra", "Dickens", "Bleak House"),
    ("Dickens-David-Copperfield", "David Copperfield Dickens", "David Copperfield", "Dickens", "David Copperfield"),
    # -- Agostinho e Dante: os classicos do acervo estao em ingles --
    ("Agostinho-Cidade-de-Deus", "A Cidade de Deus Agostinho", "A Cidade de Deus", "Agostinho", "City of God"),
    ("Agostinho-Confissoes", "Confissões de Santo Agostinho", "Confissões", "Agostinho", "Confessions"),
    ("Dante-Divina-Comédia", "A Divina Comédia Dante", "A Divina Comédia", "Dante", "Divine Comedy"),
    # -- PT-BR que faltam no acervo --
    ("Flaubert-Madame-Bovary", "Madame Bovary Gustave Flaubert", "Madame Bovary", "Flaubert", "Madame Bovary"),
    ("Proust-Em-Busca-do-Tempo-Perdido-1", "Em Busca do Tempo Perdido Proust", "Em Busca do Tempo Perdido", "Proust", "Swann's Way"),
    ("Homero-A-Odissia", "A Odisséia Homero", "A Odisséia", "Homero", "Odyssey"),
    ("Virgilio-A-Eneida", "A Eneida Virgílio", "A Eneida", "Virgílio", "Aeneid"),
    ("Goethe-Fausto", "Fausto Goethe", "Fausto", "Goethe", "Faust"),
    ("Hugo-Les-Miserables", "Les Misérables Victor Hugo", "Les Misérables", "Hugo", "Les Misérables"),
    # -- anglo-saxoes --
    ("Melville-Moby-Dick", "Moby Dick Herman Melville", "Moby Dick", "Melville", "Moby Dick"),
    ("Eliot-George-Middlemarch", "Middlemarch George Eliot", "Middlemarch", "Eliot", "Middlemarch"),
    ("Shelley-Frankenstein", "Frankenstein Mary Shelley", "Frankenstein", "Shelley", "Frankenstein"),
    ("Twain-As-Aventuras-de-Tom-Sawyer", "As Aventuras de Tom Sawyer Mark Twain", "As Aventuras de Tom Sawyer", "Twain", "Tom Sawyer"),
    ("Twain-Huckleberry-Finn", "As Aventuras de Huckleberry Finn Twain", "Huckleberry Finn", "Twain", "Huckleberry Finn"),
    ("Orwell-1984", "1984 George Orwell", "1984", "Orwell", "Nineteen Eighty-Four"),
    ("Orwell-A-Revolucao-dos-Animais", "A Revolução dos Animais Orwell", "A Revolução dos Animais", "Orwell", "Animal Farm"),
    ("Joyce-Retratos", "Retratos James Joyce", "Retratos", "Joyce", "Dubliners"),
    ("Woolf-A-Mrs-Dalloway", "A Mrs Dalloway Virginia Woolf", "Mrs Dalloway", "Woolf", "Mrs Dalloway"),
    ("Maupassant-Contos", "Contos Guy de Maupassant", "Contos", "Maupassant", "Contos"),
    ("Kipling-Kim", "Kim Rudyard Kipling", "Kim", "Kipling", "Kim"),
    # -- trilha cristiana: gap de intencao, zero na estante --
    ("Chesterton-Ortodoxia", "Ortodoxia Chesterton", "Ortodoxia", "Chesterton", "Orthodoxy"),
    ("Chesterton-O-Homem-que-foi-Quinta-feira", "O Homem que foi Quinta-feira Chesterton", "O Homem que foi Quinta-feira", "Chesterton", "The Man Who Was Thursday"),
    ("Lewis-O-Problema-da-Dor", "O Problema da Dor C S Lewis", "O Problema da Dor", "Lewis", "The Problem of Pain"),
    ("Bunyan-O-Peregrino", "O Peregrino John Bunyan", "O Peregrino", "Bunyan", "Pilgrim's Progress"),
    ("Greene-O-Poder-e-a-Gloria", "O Poder e a Glória Graham Greene", "O Poder e a Glória", "Greene", "The Power and the Glory"),
    ("OConnor-A-Wise-Blood", "A Wise Blood Flannery O'Connor", "A Wise Blood", "O'Connor", "Wise Blood"),
]

CONTAS = mod.CONTAS
print(f"ALVOS={len(ALVOS)} contas={CONTAS} dominio={DOM}")
print(f"destino={INCOMING}\n")
log("inicio-lote", alvos=len(ALVOS), contas=CONTAS, dominio=DOM)

_cache = {}
baixados, falhas = 0, 0
acct_idx = 0
acct = CONTAS[0]
t0 = time.time()
LIMITE_TEMPO = 3000

for slug, query, tit, aut, alt in ALVOS:
    if time.time() - t0 > LIMITE_TEMPO:
        print("!! limite de tempo atingido")
        log("limite-tempo")
        break
    h, l = cota(acct)
    if h >= l:
        # procura proxima conta com cota
        achou = False
        for i in range(len(CONTAS)):
            cand_acct = CONTAS[(acct_idx + 1 + i) % len(CONTAS)]
            ch, cl = cota(cand_acct)
            if ch < cl:
                acct = cand_acct
                acct_idx = (acct_idx + 1 + i) % len(CONTAS)
                print(f"   >> cota de {CONTAS[acct_idx]} esgotada -> {acct} ({ch}/{cl})")
                achou = True
                break
        if not achou:
            print("!! todas as contas sem cota")
            log("cota-esgotada")
            break
    if query not in _cache:
        _cache[query] = mod.busca(query, acct)
        time.sleep(1.0)
    books = _cache[query]
    cand, score = mod2.melhor2(books, tit, aut, alt)
    if not cand:
        print(f"[SEM-CAND] {slug:42s} n={len(books)} score={score}")
        log("sem-candidato", slug=slug, query=query, n=len(books), score=score)
        falhas += 1
        continue
    dest, info = mod.baixa(cand, acct, slug)
    if dest is None:
        print(f"[FALHA-DL] {slug:42s} {info}")
        log("falha-download", slug=slug, erro=info, titulo=cand.get("title"))
        falhas += 1
        continue
    baixados += 1
    print(f"[OK {baixados:02d}] {slug:42s} {info:12s} <- {cand.get('title')[:52]} | {cand.get('author')[:26]}")
    log("baixado", slug=slug, arquivo=dest.name, info=info,
        zlib_title=cand.get("title"), zlib_author=cand.get("author"),
        zlib_id=cand.get("id"), zlib_hash=cand.get("hash"), conta=acct)

print(f"\n=== FIM: baixados={baixados} falhas={falhas} ===")
log("fim-lote", baixados=baixados, falhas=falhas)
