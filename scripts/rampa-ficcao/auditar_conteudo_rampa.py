#!/usr/bin/env python3
"""Auditoria de CONTEUDO dos .md da rampa: confere que o texto e do livro certo.

Para cada obra, usa marcadores distintivos (em portugues, incluindo as
transliteracoes que as traducoes PT-BR usam) e reporta a taxa de acerto.
Se o texto for de OUTRO livro, os marcadores nao batem.

Uso: python3 scripts/rampa-ficcao/auditar_conteudo_rampa.py
"""
import re
import sys
import unicodedata
from pathlib import Path

ROOT = Path("/home/willian/study-agent")
DEST = ROOT / "data/biblioteca/literatura-mundial-classica"

OBRAS = {
    "dostoievski/Crime-e-Castigo-Fiodor-Dostoievski.md":
        ["crime e castigo", "raskolnikov", "sonya", "raskolnikov", "katerina", "petr"],
    "dostoievski/Os-Irmaos-Karamazov-Fiodor-Dostoievski.md":
        ["karamazov", "alyosha", "dmitri", "grushenka", "ivan", "fiodor"],
    # traducao PT-BR (Paulo Bezerra): "O Principe Myshkin", "Nastasya Filippovna"
    "dostoievski/O-Idiota-Fiodor-Dostoievski.md":
        ["o idiota", "myshkin", "nastasya", "príncipe", "prince", "ganya"],
    "dostoievski/Os-Demonios-Fiodor-Dostoievski.md":
        ["os demonios", "stavrogin", "shatov", "darya", "ivan", "tikhon"],
    "dostoievski/O-Jogador-Fiodor-Dostoievski.md":
        ["o jogador", "alexei", "polina", "rulette", "roulette", "marinka"],
    "tolstoi/Guerra-e-Paz-Lev-Tolstoi.md":
        ["guerra e paz", "pierre", "andrei", "natasha", "natália", "bolkonsky", "kutuzov"],
    "tolstoi/Anna-Karenina-Lev-Tolstoi.md":
        ["anna karenina", "anna karênina", "levin", "kitty", "vronsky", "vronski", "alexei karinin"],
    "tolstoi/Ressurreicao-Lev-Tolstoi.md":
        ["ressurreição", "ressurreicao", "nekrasov", "maslova", "anna", "iudash"],
    "austen/Orgulho-e-Preconceito-Jane-Austen.md":
        ["orgulho e破産", "orgulho e prejudice", "elizabeth", "elizabeth bennet", "darcy", "bennet"],
    "austen/Emma-Jane-Austen.md":
        ["emma", "woodhouse", "knightley", "harriet", "frank churchill"],
    "bronte/Jane-Eyre-Charlotte-Bronte.md":
        ["jane eyre", "rochester", "bertha", "alice", "thornfield", "heathcliff"],
    "anglo-saxoes/Middlemarch-George-Eliot.md":
        ["middlemarch", "dorothea", "caspar", "will", "brooke", "tertius", "featherstone"],
    "anglo-saxoes/Moby-Dick-Herman-Melville.md":
        ["moby", "ishmael", "whale", "whaling", "pequod", "captain ahab", "queequeg"],
    "anglo-saxoes/Frankenstein-Mary-Shelley.md":
        ["frankenstein", "victor", "monster", "elizabeth", "walton", "clay"],
    "anglo-saxoes/Mrs-Dalloway-Virginia-Woolf.md":
        ["dalloway", "clarissa", "septimus", "hugh walpole", "bradshaw", "london"],
    "anglo-saxoes/As-Aventuras-de-Tom-Sawyer-Mark-Twain.md":
        ["tom sawyer", "huckleberry", "becky", "injun joe", "aunt polly", "huck finn"],
    "anglo-saxoes/As-Aventuras-de-Huckleberry-Finn-Mark-Twain.md":
        ["huckleberry finn", "huck finn", "jim", "mississippi", "king james", "tom sawyer"],
    "anglo-saxoes/1984-George-Orwell.md":
        ["winston", "novafala", "grande irmao", "partido", "telescreens", "doublethink", "julia"],
    "anglo-saxoes/A-Revolucao-dos-Animais-George-Orwell.md":
        ["fazenda dos animais", "napoleao", "bola de neve", "guinchento", "boxer",
         "sete mandamentos", "animalismo", "moinho de vento", "whymper"],
    "dickens/Grandes-Esperancas-Charles-Dickens.md":
        ["pip", "estella", "jo", "great expectations", "wemmick", "magwitch", "con miss abel"],
    "dickens/Casa-de-Cassandra-Charles-Dickens.md":
        ["casa de cassandra", "cassandra", "noble", "tuck", "alice", "clara"],
    "dickens/David-Copperfield-Charles-Dickens.md":
        ["david copperfield", "david", "agnes", "dora", "uriah", "murdstone", "peggottty"],
    "agostinho/A-Cidade-de-Deus-Santo-Agostinho.md":
        ["cidade de deus", "augustino", "sanctus", "roma", "cesar", "pompeia", "portao"],
    "agostinho/Confissoes-Santo-Agostinho.md":
        ["confissoes", "confessiones", "augustino", "deus", "tempo", "memorias", "gameiro"],
    "dante/A-Divina-Comedia-Dante-Alighieri.md":
        ["divina comedia", "dante", "v Virgil", "v�r", "inferno", "purgatorio", "paradiso", "inferno"],
    "antigos/A-Odisseia-Homero.md":
        ["odisseia", "odysseus", "ulisses", "telemo", "penelope", "nestor", "poseidon"],
    "antigos/A-Eneida-Virgilio.md":
        ["eneida", "eneida de virgilio", "eneas", "eneas", "dido", "aquiles", "caronte"],
    "antigos/Fausto-Johann-Wolfgang-von-Goethe.md":
        ["fausto", "faust", "mefistofeles", "mephistopheles", "marguerite", "werther"],
    "proust/Em-Busca-do-Tempo-Perdido-I-Marcel-Proust.md":
        ["proust", "swann", "combray", "marcel", "madeleine", "verona"],
    "frances/Madame-Bovary-Gustave-Flaubert.md":
        ["madame bovary", "emma", "charles bovary", "leon dupuis", "homais", "rouen"],
}


def sem_acento(s):
    return "".join(c for c in unicodedata.normalize("NFKD", s or "")
                   if not unicodedata.combining(c))


def norm(s):
    return re.sub(r"[^a-z0-9]+", " ", sem_acento(s or "").lower()).strip()


problemas = []
print(f"{'obra':52s} {'acerto':>10s}  status")
print("-" * 80)
for rel, marcadores in OBRAS.items():
    p = DEST / rel
    if not p.exists():
        print(f"{rel[:52]:52s} {'AUSENTE':>10s}  !!")
        problemas.append(f"{rel}: arquivo ausente")
        continue
    txt = p.read_text(encoding="utf-8", errors="ignore")
    corpo = norm(txt)
    acertos = [m for m in marcadores if norm(m) in corpo]
    pct = len(acertos) / len(marcadores)
    status = "OK" if pct >= 0.4 else ("suspeito" if pct > 0 else "!! ERRADO")
    print(f"{rel[:52]:52s} {len(acertos):2d}/{len(marcadores):<3d} {pct*100:3.0f}%  {status}")
    if pct < 0.4:
        problemas.append(f"{rel}: so {len(acertos)}/{len(marcadores)} marcadores "
                        f"-> {acertos}")

if problemas:
    print(f"\n!! {len(problemas)} problema(s):")
    for x in problemas:
        print("  -", x)
    sys.exit(1)
print("\nOK: todos os .md da rampa tem o conteudo do livro certo.")
