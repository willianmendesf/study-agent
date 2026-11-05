#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CURADOR DO MEMOS — reestruturação de tags e limpeza
=====================================================
Diagnóstico de 2026-11-05: o Memos tinha 389 memos, 195 tags distintas, 113 delas
usadas 1-2 vezes, e 4 esquemas de tag competindo (`grupo/`, `estudo/`, `aula/`,
tags soltas tipo `resumo`/`plano`). Resultado: nada achável.

Este script faz 4 coisas, controladas por flag:

  --auditar    (default) só RELATA o que faria. NÃO escreve nada.
  --aplicar    re-tag dos memos do Study-Agent na taxonomia nova.
  --dedup      apaga cópias duplicadas (mesmo título), mantendo a mais recente.
  --limpar     apaga lixo técnico (probes, sanity-checks, <120 chars).

COMO AS TAGS FUNCIONAM NO MEMOS (descoberto em 2026-11-05):
  As tags NÃO são um campo editável — o servidor extrai das HASHTAGS no fim do
  `content`. Por isso re-tagar = reescrever o conteúdo com as hashtags novas.
  Armadilha: `PATCH {"content": ...}` preserva as tags já existentes, mas `PATCH
  {"tags": [...]}` é RECUSADO ("invalid update path: tags"). E o uid da API é o
  `name` SEM o prefixo `memos/` e COM o sufixo completo (ex.:
  `memos/3ER2zYRdjebVPMZirzG8G5` → `3ER2zYRdjebVPMZirzG8G5`).

NUNCA apaga material do outro projeto (fisioterapia/medicina): esse material pode
pertencer a outro study-agent do William. Ele é apenas ISOLADO por tag.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path("/home/willian/study-agent")
ENVFILE = ROOT / "data/config-backup/memos/memos.env"

# ------------------------------------------------------------------ config
URL = PAT = ""

# projeto externo (fisioterapia/medicina) — ISOLAR, nunca apagar
EXTERNO = re.compile(
    r"fisioterapia|ortopedia|cardiologia|neurologia|pediatria|"
    r"saude[-_ ]da[-_ ]mulher|unicid|cardio|massagem|goniometr|"
    r"cinesiolog|osteopat|reabilita|enfermagem|farmacia|radiolog|"
    r"neuropediatria|neonat|apgar|ventila[cç]", re.I)

# area -> tag eixo 1
AREAS = [
    ("teologia", re.compile(
        r"exegese|devocional|bíblic|biblic|hermen|teolog|homili|sermão|sermao|"
        r"pregação|pregacao|confissão|confessao|westminster|"
        r"\bjoão\b|\bjoao\b|romanos|efésios|efesios|hebreus|apocalipse|"
        r"filemon|jejum|vocação|vocacao|ministério|ministerio|1joao|1 joão", re.I)),
    ("literatura", re.compile(
        r"literatura|romance|novela|conto|ficção|ficcao|machado|clarice|"
        r"rampa|dom quixote|dostoi|tolstoi|austen|dickens", re.I)),
    ("portugues", re.compile(
        r"portugu[eê]s|gramática|gramatica|ortografia|sintaxe|vogais|alfabeto|"
        r"consoante|redação|redacao|sílaba|silaba|acentua", re.I)),
    ("curriculo", re.compile(
        r"ipb|seminário|seminario|\bebd\b|curriculum|curículo|edital|"
        r"m[óo]dulo|candidatura|roadmap|grade|comitê|comite", re.I)),
    ("producao", re.compile(
        r"t[eé]cnica de estudo|m[eé]todo de estudo|leitura ativa|fichamento|"
        r"memoriza|revis[aã]o espa|resumo|nota de leitura", re.I)),
]

# forma -> tag eixo 2
TIPOS = [
    ("plano", re.compile(r"\bplano\b|roadmap|roteiro|grade|grade curricular|"
                         r"plano de aula|plano de estudo|plano de leitura|"
                         r"cronograma|cronograma", re.I)),
    ("ficha", re.compile(r"\bficha\b|fichamento|index card|8 pastas", re.I)),
    ("resumo", re.compile(r"\bresumo\b|mega-resumo|resumo por aula|"
                          r"resumo explicativo|resumo de", re.I)),
    ("exegese", re.compile(r"exegese|análise sintática|análise textual|"
                           r"introdu[çc][ãa]o contextual", re.I)),
    ("devocional", re.compile(r"devocional", re.I)),
    ("guia", re.compile(r"\bguia\b|guia de bolso|question[áa]rio|banco de perguntas|"
                        r"simula[çc][ãa]o de entrevista|matriz de cobertura|"
                        r"variações de quest", re.I)),
    ("indice", re.compile(r"cat[áa]logo|[íi]ndice|acervo|refer[êe]ncias|"
                          r"grade curricular", re.I)),
    ("mapa", re.compile(r"mapa conceitual|mapa de assuntos|mapa m[0-9]|"
                        r"\bmapa\b", re.I)),
    ("simulado", re.compile(r"simulado|prova\s+\d|simula[çc][ãa]o", re.I)),
    ("transcricao", re.compile(r"transcri[çc][ãa]o|transcri", re.I)),
    ("relatorio", re.compile(r"relat[óo]rio|relatorio", re.I)),
    ("nota", re.compile(r"\bnota\b|revis[ãa]o|diário|diario", re.I)),
]

# fonte -> tag eixo 3 (opcional)
FONTES = [
    ("ipb-candidatura", re.compile(r"ipb.*candidatura|candidatura", re.I)),
    ("seminario-jmc", re.compile(r"semin[áa]rio.*jmc|jmc", re.I)),
    ("ebd-ipbf", re.compile(r"\bebd\b.*ipbf|ebd-ipbf", re.I)),
    ("ebdi", re.compile(r"\bebdi\b|ebdi", re.I)),
    ("hermeneia", re.compile(r"hermeneia|hermen[eê]utica", re.I)),
]

# livro bíblico -> tag eixo 4 (opcional)
LIVROS = ["joao", "1-joao", "2-joao", "3-joao", "romanos", "efesios", "filemon",
          "hebreus", "apocalipse", "joel", "amos", "obadias", "jonas", "miqueias",
          "habacuque", "sofnias", "ageu", "zacarias", "malaquias", "salmos",
          "proverbios", "ecclesiastes", "isaias", "jeremias", "laminas",
          "ezequiel", "daniel", "oseias", "joel", "amos", "obadias", "jonas",
          "miqueias", "naum", "habacuque", "sofnias", "ageu", "zacarias",
          "malaquias", "genesis", "exodo", "levitico", "numeros", "deuteronomio",
          "josue", "juizes", "rut", "1-samuel", "2-samuel", "1-reis", "2-reis",
          "1-cronicas", "2-cronicas", "esdras", "neemias", "ester", "joao",
          "apocalipse", "mateus", "marcos", "lucas", "atos", "romanos",
          "1-corintios", "2-corintios", "galatas", "efesios", "filipenses",
          "colossenses", "1-tessalonicenses", "2-tessalonicenses", "1-timoteo",
          "2-timoteo", "tito", "filemom", "hebreus", "iago", "1-pedro",
          "2-pedro", "1-joao", "2-joao", "3-joao", "judas", "apocalipse"]

# módulo/série
SERIE = re.compile(r"modulo/(m\d[\w-]*)|serie/([\w-]+)", re.I)
PERSONA = re.compile(r"#(hermes|hermeneia|eusebeia|literato|portuga|darshan|"
                     r"kerux|rhetor|homologia|histor|kritikos|zetesis|"
                     r"areopago|antropos|bibliotecario|aporia|dialektikos|"
                     r"bereiano|anglista|kairos)\b")

HASHTAG = re.compile(r"(?:^|\s)#([^\s#]+)")

# vocabulario controlado dos eixos
AREA_VALIDAS = {"teologia", "curriculo", "portugues", "literatura",
                 "producao", "geral"}
TIPOS_VALIDOS = {"plano", "ficha", "resumo", "exegese", "devocional", "guia",
                  "indice", "mapa", "simulado", "transcricao", "relatorio",
                  "nota", "aula", "exercicio", "externo"}


# ------------------------------------------------------------------ helpers
def carregar_env():
    global URL, PAT
    for line in ENVFILE.read_text(encoding="utf-8").splitlines():
        if line.startswith("MEMOS_URL="):
            URL = line.split("=", 1)[1].strip().rstrip("/")
        if line.startswith("MEMOS_PAT="):
            PAT = line.split("=", 1)[1].strip()
    if not URL or not PAT:
        sys.stderr.write("ERRO: MEMOS_URL/MEMOS_PAT ausentes no memos.env\n")
        raise SystemExit(2)


def api(method, path, body=None, timeout=45):
    args = ["curl", "-sS", "--max-time", str(timeout), "-X", method,
            f"{URL}{path}", "-H", f"Authorization: Bearer {PAT}"]
    if body is not None:
        args += ["-H", "Content-Type: application/json",
                 "--data-binary", json.dumps(body, ensure_ascii=False)]
    r = subprocess.run(args, capture_output=True, text=True)
    try:
        return json.loads(r.stdout)
    except Exception:
        return {"_raw": r.stdout, "_err": r.stderr}


def listar():
    todos, token = [], ""
    while True:
        url = f"/api/v1/memos?pageSize=200" + (f"&pageToken={token}" if token else "")
        d = api("GET", url)
        todos.extend(d.get("memos", []))
        token = d.get("nextPageToken", "")
        if not token or len(todos) > 2000:
            break
    return todos


def uid(memo):
    return (memo.get("name") or "").split("/", 1)[-1]


def tags_de(memo):
    ts = memo.get("tags") or []
    if isinstance(ts, str):
        ts = [t.strip() for t in ts.split(",") if t.strip()]
    return ts


# ------------------------------------------------------------------ taxonomia
def _tags_por_eixo(tags):
    """Separa as tags antigas por eixo, para reusar o que já está certo."""
    eixo = {"area": None, "tipo": None, "fonte": None, "livro": None,
            "serie": None, "persona": None}
    for t in tags:
        if t.startswith("grupo/estudo/"):
            cand = t[len("grupo/estudo/"):]
            if cand and "/" not in cand:
                eixo["area"] = cand
        elif t.startswith("estudo/"):
            cand = t[len("estudo/"):]
            if cand and "/" not in cand and cand not in ("teologia", "curriculo",
                                                        "portugues", "literatura",
                                                        "producao", "geral"):
                # so e' area se for uma area conhecida; senao e' persona/especialista
                if cand in AREA_VALIDAS:
                    eixo["area"] = cand
                else:
                    eixo["persona"] = eixo["persona"] or cand
        elif t.startswith("tipo/"):
            cand = t[len("tipo/"):]
            if cand in TIPOS_VALIDOS:
                eixo["tipo"] = cand
        elif t.startswith("fonte/"):
            eixo["fonte"] = t[len("fonte/"):]
        elif t.startswith("livro/"):
            eixo["livro"] = t[len("livro/"):]
        elif t.startswith("modulo/"):
            eixo["serie"] = t[len("modulo/"):]
        elif t.startswith("serie/"):
            eixo["serie"] = t[len("serie/"):]
        elif t.startswith("persona/"):
            eixo["persona"] = t[len("persona/"):]
    return eixo


# area antiga -> area nova
ALIAS_AREA = {"portugues": "portugues", "português": "portugues",
              "teologia": "teologia", "curriculo": "curriculo",
              "literatura": "literatura", "fisioterapia": None}


def classificar(memo):
    """Devolve (tags_novas, area, tipo, eh_externo).

    REGRA DE OURO: a tag antiga e' mais confiavel que o texto. O texto so entra
    como fallback (quando a tag nao existe) — e ai so o TITULO + as primeiras
    linhas contam, para nao classificar por mencao casual a outro livro.
    """
    c = memo.get("content", "") or ""
    tags_old = memo.get("tags") or []
    if isinstance(tags_old, str):
        tags_old = [t.strip() for t in tags_old.split(",") if t.strip()]
    ts = " ".join(tags_old)

    # TRAVA DE DONO (2026-11-05): o Memos e' COMPARTILHADO. Memos de outro
    # creator nao sao do Study-Agent — nunca re-taguear, nunca reescrever.
    # (Bug anterior: 9 memos da Fabiana carregavam tag 'study-agent' e seriam
    #  OverWRITTEN por este curador.)
    creator = (memo.get("creator") or "")
    if creator and creator != "users/willianmendesf":
        return (["externo/projeto-terceiro"], "externo", "externo", True)

    if EXTERNO.search(ts) or EXTERNO.search(c[:800]):
        return (["externo/projeto-terceiro"], "externo", "externo", True)

    eixo = _tags_por_eixo(tags_old)
    linhas = [l for l in c.strip().splitlines() if l.strip()]
    titulo = " ".join(linhas[:3])[:400]

    # --- AREA: tag antiga > regex no titulo > regex no corpo
    area = None
    if eixo["area"]:
        area = ALIAS_AREA.get(eixo["area"], eixo["area"])
    if not area:
        area = next((a for a, rx in AREAS if rx.search(titulo)), None)
    if not area:
        area = next((a for a, rx in AREAS if rx.search(c[:2000])), "geral")

    # --- TIPO: tag antiga > regex no titulo > regex no corpo
    tipo = None
    if eixo["tipo"]:
        tipo = eixo["tipo"]
    if not tipo:
        tipo = next((t for t, rx in TIPOS if rx.search(titulo)), None)
    if not tipo:
        tipo = next((t for t, rx in TIPOS if rx.search(c[:2000])), "nota")

    # --- FONTE: tag antiga > regex
    fonte = eixo["fonte"]
    if not fonte:
        fonte = next((f for f, rx in FONTES if rx.search(titulo)), None)

    # --- LIVRO: so da tag antiga (texto livre erra — "Tito" vira "judas")
    livro = eixo["livro"]
    if not livro and area == "teologia":
        low = titulo.lower()
        for lv in sorted(set(LIVROS), key=len, reverse=True):
            if re.search(rf"\b{re.escape(lv)}\b", low):
                livro = lv
                break

    serie = eixo["serie"]
    persona = eixo["persona"]
    if not persona:
        mp = PERSONA.search(" " + ts)
        if mp:
            persona = mp.group(1)

    novas = [f"estudo/{area}", f"tipo/{tipo}"]
    if fonte:
        novas.append(f"fonte/{fonte}")
    if livro:
        novas.append(f"livro/{livro}")
    if serie:
        novas.append(f"serie/{serie}")
    if persona:
        novas.append(f"persona/{persona}")
    novas.append("study-agent")
    return (novas, area, tipo, False)


def limpar_hashtags(conteudo):
    """Remove a LINHA DE TAGS do corpo (onde o Memos lê as tags).

    BUG FIX 2026-11-05: a versão anterior só popava a ÚLTIMA linha. Vários
    memos tinham a linha de tags antiga NO MEIO do corpo (PATCH anterior
    anexou hashtags sem remover as velhas), e elas continuavam virando tags:
    '#grupo/estudo/teologia tipo/nota study-agent jejum disciplina'.
    Agora remove TODAS as linhas que são só lista de tokens de tag.
    """
    linhas = conteudo.rstrip().splitlines()
    out = []
    for l in linhas:
        s = l.strip()
        if not s:
            out.append(l)
            continue
        toks = s.split()
        # linha de tags = tokens "#x" ou "x" separados por espaço, SEM texto
        # corrido (sem frase, sem pontuação de parágrafo).
        parece_tags = bool(toks) and all(
            t.startswith("#") or re.fullmatch(r"[\wÀ-ÿ][\wÀ-ÿ\-/]*", t)
            for t in toks)
        tem_hash = any(t.startswith("#") for t in toks)
        tem_palavra_real = any(
            re.fullmatch(r"[a-zA-ZÀ-ÿ]{3,}", t) and not t.startswith("#")
            and t.lower() not in (
                "study-agent", "tipo", "estudo", "grupo", "fonte", "livro",
                "serie", "persona", "modulo", "aula", "resumo", "plano",
                "nota", "guia", "mapa", "ficha", "indice", "teologia",
                "producao", "literatura", "curriculo", "portugues", "geral",
                "exegese", "devocional", "simulado", "relatorio", "transcricao",
                "exercicio", "externo")
            for t in toks)
        if parece_tags and (tem_hash or tem_palavra_real) and len(toks) >= 2:
            continue  # linha de tags antiga -> remove
        out.append(l)
    return "\n".join(out).rstrip()


# ------------------------------------------------------------------ higiene
# PROVA (probe empirico em 2026-11-05): o Memos extrai hashtag de QUALQUER
# linha do corpo, nao so da ultima. Exemplos que viraram tag:
#   "bloco **#182**"   -> tag "182"
#   "(#gama)"          -> tag "gama"
#   "#mu/nu"           -> tags "mu" E "mu/nu"  (cria tag-pai a cada "/")
#   "[#kappa]"         -> tag "kappa"
#   "```#delta```"     -> NAO virou tag (bloco de codigo e ignorado)
#   "https://x/#theta" -> NAO virou tag (URL ignorada)
# Logo: no corpo do memo, "#" so pode aparecer como marca de titulo markdown.
INLINE_HASHTAG = re.compile(r"(?<!^)(?<![\s(#`\[])#(?![!#])"
                            r"(?![0-9]+(?:\.[0-9]+)?\b(?![^\s#]*[a-zA-ZÀ-ÿ]))"
                            r"(?![a-zA-ZÀ-ÿ][^\s#]*::)"
                            r"([0-9]+|[a-zA-ZÀ-ÿ][\wÀ-ÿ/-]*)")


def higienizar_corpo(conteudo):
    """Remove hashtags inline (fora da linha de tags) do corpo do memo.

    Objetivo: o corpo do memo tem que ler como MATERIAL DE ESTUDO, não como
    indexação. As tags ficam so na ultima linha.
    """
    linhas = conteudo.rstrip().splitlines()
    out = []
    for l in linhas:
        # codigo: nao tocar
        if l.strip().startswith("```") or l.strip().startswith("    "):
            out.append(l)
            continue
        # titulo markdown (## Titulo) — nao tocar
        if re.match(r"^\s*#{1,6}\s", l):
            out.append(l)
            continue
        # LINHA INTEIRA de hashtags (a linha de tags antiga pode estar no MEIO
        # do corpo, nao so no fim — bug de 2026-11-05): remove a linha toda.
        if l.count("#") >= 2 and len(HASHTAG.findall(l)) >= 2:
            out.append("")
            continue
        # protege URLs
        partes = re.split(r"(https?://\S+)", l)
        novo = []
        for k, parte in enumerate(partes):
            if k % 2 == 1:      # URL
                novo.append(parte)
                continue
            # "#N" numerico -> "nºN" ; "#palavra" -> "palavra"
            parte = re.sub(r"#(?=[0-9])(\d+)", lambda m: "nº" + m.group(1), parte)
            parte = re.sub(r"(?<![\w`\[])#([a-zA-ZÀ-ÿ][\wÀ-ÿ-]{2,})(?![\wÀ-ÿ/])",
                           lambda m: m.group(1), parte)
            novo.append(parte)
        out.append("".join(novo))
    return "\n".join(out).rstrip()


def reescrever(conteudo, tags):
    """Devolve o conteúdo higienizado + a linha de hashtags nova no fim."""
    base = higienizar_corpo(limpar_hashtags(conteudo))
    linha = " ".join("#" + t for t in tags)
    return f"{base}\n\n{linha}\n"


# ------------------------------------------------------------------ auditoria
def auditar(todos):
    plano = []
    for m in todos:
        c = m.get("content", "") or ""
        ts = m.get("tags") or []
        if isinstance(ts, str):
            ts = [t.strip() for t in ts.split(",") if t.strip()]
        novas, area, tipo, ext = classificar(m)
        mudou = sorted(set(novas)) != sorted(set(ts))
        plano.append({
            "name": m.get("name"), "uid": uid(m),
            "len": len(c), "tags_antigas": ts, "tags_novas": novas,
            "mudou": mudou, "externo": ext, "area": area, "tipo": tipo,
            "titulo": (c.strip().splitlines() or ["(vazio)"])[0][:80],
        })
    return plano


def _titulo_limpo(memo):
    """Titulo = 1a linha, sem a linha de hashtags e sem emoji inicial."""
    c = (memo.get("content", "") or "").strip()
    linhas = [l.strip() for l in c.splitlines() if l.strip()]
    if not linhas:
        return ""
    t = linhas[0]
    if HASHTAG.search(t) and len(HASHTAG.findall(t)) >= 2:
        return ""
    # remove emoji/simbolos iniciais e normaliza
    t = re.sub(r"^[^\wÀ-ÿ#]+", "", t).strip().lower()
    return re.sub(r"\s+", " ", t)


def duplicatas(todos):
    """Memos com o MESMO titulo → devolver o uid a apagar (o mais antigo).

    CUIDADO (achado em 2026-11-05): titulo igual NAO e' sempre duplicata.
    O "Devocional de 7 Dias" aparecia 7x — e cada copia era um DIA DIFERENTE
    (Dia 1 Salmo 51, Dia 2 ..., Dia 7 Salmo 143). Sao 7 capitulos de uma serie,
    nao 7 copias. Por isso: so considerar duplicata quando o CONTEUDO tambem
    coincide (mesmo md5) OU quando o corpo nao tem marcador de serie.
    """
    por_titulo = defaultdict(list)
    for m in todos:
        t = _titulo_limpo(m)
        if len(t) >= 12:
            por_titulo[t].append(m)
    apagar = []
    for titulo, grupo in por_titulo.items():
        if len(grupo) < 2:
            continue
        # conteudo identico? → duplicata real
        # BUG FIX 2026-11-05: comparar o content CRU errava — as linhas de
        # hashtags no fim diferem entre as cópias (uma tem a taxonomia velha,
        # outra a nova), entao duas copias byte-a-byte do corpo nao casavam.
        # Agora compara o corpo SEM a linha de tags.
        por_hash = defaultdict(list)
        for m in grupo:
            c = limpar_hashtags(m.get("content", "") or "")
            por_hash[hashlib.md5(c.strip().encode()).hexdigest()].append(m)
        for h, sub in por_hash.items():
            if len(sub) > 1:
                sub = sorted(sub, key=lambda x: x.get("createTime", ""))
                for m in sub[:-1]:
                    apagar.append((m, titulo, "conteudo identico"))
        # conteudo diferente? → verificar se e' serie (marcador DIA n / PARTE n)
        restantes = [m for m in grupo
                     if m not in [x for x, _, _ in apagar]]
        if len(restantes) > 1:
            marcadores = [bool(re.search(r"(?im)^\s*#{1,4}\s*(dia|parte|bloco|aula)\s*\d+",
                                         m.get("content", "") or ""))
                          for m in restantes]
            if all(marcadores):
                # e' serie: mantem todos
                continue
            # sem marcador de serie →真的 duplicata: mantem o mais recente
            restantes = sorted(restantes, key=lambda x: x.get("createTime", ""))
            for m in restantes[:-1]:
                apagar.append((m, titulo, "mesmo titulo, corpo diferente"))
    return apagar


def lixo(todos):
    """Lixo técnico: probe, sanity-check, conteúdo < 120 chars."""
    rx = re.compile(r"^\s*(probe|sanity[- ]?check|teste de conectividade|ping|"
                    r"ok$|test$)", re.I)
    out = []
    for m in todos:
        c = (m.get("content", "") or "").strip()
        if rx.match(c) or len(c) < 120:
            out.append(m)
    return out


# ------------------------------------------------------------------ main
def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--auditar", action="store_true", help="só relata (padrão)")
    ap.add_argument("--aplicar", action="store_true", help="re-tagueia os memos")
    ap.add_argument("--dedup", action="store_true", help="apaga cópias duplicadas")
    ap.add_argument("--limpar", action="store_true", help="apaga lixo técnico")
    ap.add_argument("--somente-area", help="filtra por área (ex.: teologia)")
    ap.add_argument("--higienizar", action="store_true",
                    help="remove hashtags inline do corpo (mantem as tags atuais)")
    ap.add_argument("--confirmar", action="store_true",
                    help="exigir confirmação por memo (modo seguro)")
    a = ap.parse_args()

    carregar_env()
    todos = listar()
    print(f"Memos na API: {len(todos)}\n")

    plano = auditar(todos)

    # ---------- auditoria
    mudancas = [p for p in plano if p["mudou"]]
    externos = [p for p in plano if p["externo"]]
    meus = [p for p in plano if not p["externo"]]
    print("=== AUDITORIA ===")
    print(f"  memos na API                : {len(todos)}")
    print(f"  memos do Study-Agent        : {len(meus)}")
    print(f"  memos de outro projeto/usuario: {len(externos)} (NAO TOCADOS)")
    print(f"  memos que mudariam de tag   : {len(mudancas)}")
    print(f"  tags atuais distintas       : "
          f"{len({t for p in plano for t in p['tags_antigas']})}")
    print(f"  tags depois da re-tagagem   : "
          f"{len({t for p in plano for t in p['tags_novas']})}")
    print()

    by_area = Counter(p["area"] for p in plano)
    by_tipo = Counter(p["tipo"] for p in plano)
    print("  por área :", dict(by_area))
    print("  por tipo :", dict(by_tipo))
    print()

    dups = duplicatas(todos)
    lixos = lixo(todos)
    # TRAVA DE DONO: dedup/limpeza so valem para memos do Study-Agent.
    def _meu(m):
        return (m.get("creator") or "users/willianmendesf") == "users/willianmendesf"
    dups = [(m, t, mo) for (m, t, mo) in dups if _meu(m)]
    lixos = [m for m in lixos if _meu(m)]
    print(f"  duplicatas (mesmo título) : {len(dups)}")
    print(f"  lixo técnico (<120 chars) : {len(lixos)}")
    print()

    if a.somente_area:
        mudancas = [p for p in mudancas if p["area"] == a.somente_area]

    if a.auditar or not (a.aplicar or a.dedup or a.limpar or a.higienizar):
        print("=== AMOSTRA DO QUE MUDARIA (primeiros 30) ===")
        for p in mudancas[:30]:
            print(f"  {p['uid'][:22]:24s} {p['titulo'][:44]:46s}")
            print(f"      ANTES: {p['tags_antigas']}")
            print(f"      DEPOIS: {p['tags_novas']}")
        print()
        print("(modo auditoria — nada foi escrito)")
        return 0

    # ---------- dedup
    if a.dedup:
        print(f"=== DEDUP: apagando {len(dups)} cópias ===")
        for m, titulo, motivo in dups:
            r = api("DELETE", f"/api/v1/memos/{uid(m)}")
            ok = isinstance(r, dict) and not r.get("code")
            print(f"  {'OK ' if ok else 'ERR'} {uid(m)[:22]:24s} {titulo[:44]:46s} [{motivo}]")
            time.sleep(0.15)

    # ---------- limpeza
    if a.limpar:
        print(f"\n=== LIMPEZA: apagando {len(lixos)} itens de lixo técnico ===")
        for m in lixos:
            c = (m.get("content", "") or "").strip().replace("\n", " ")[:50]
            r = api("DELETE", f"/api/v1/memos/{uid(m)}")
            ok = isinstance(r, dict) and not r.get("code")
            print(f"  {'OK ' if ok else 'ERR'} {uid(m)[:22]:24s} {c}")

    # ---------- higiene do corpo (hashtags inline)
    if a.higienizar:
        print("\n=== HIGIENIZANDO o corpo (hashtags inline) ===")
        n = 0
        for m in todos:
            # TRAVA DE DONO: nunca reescreve memo de outro usuario.
            if (m.get("creator") or "users/willianmendesf") != "users/willianmendesf":
                continue
            c = m.get("content", "") or ""
            if not HASHTAG.search(c):
                continue
            novo = reescrever(c, tags_de(m))
            if novo.strip() == c.strip():
                continue
            r = api("PATCH", f"/api/v1/memos/{uid(m)}", {"content": novo})
            ok = isinstance(r, dict) and not r.get("code")
            if not ok:
                print(f"  ERR {uid(m)[:22]:24s} {str(r)[:100]}")
            n += 1
            if n % 25 == 0:
                print(f"  ... {n}")
            time.sleep(0.2)
        print(f"  higienizados: {n}")
        return 0

    # ---------- retag
    if a.aplicar:
        # TRAVA DE DONO: só re-tagueia memos do William (users/willianmendesf).
        mudancas = [p for p in mudancas if not p["externo"]]
        print(f"\n=== RE-TAGAGEM de {len(mudancas)} memos (só do Study-Agent) ===")
        for i, p in enumerate(mudancas, 1):
            memo = next(m for m in todos if uid(m) == p["uid"])
            novo = reescrever(memo.get("content", "") or "", p["tags_novas"])
            r = api("PATCH", f"/api/v1/memos/{p['uid']}", {"content": novo})
            ok = isinstance(r, dict) and not r.get("code")
            if not ok:
                print(f"  ERR {p['uid'][:22]:24s} {str(r)[:120]}")
            elif i % 25 == 0:
                print(f"  ... {i}/{len(mudancas)}")
            time.sleep(0.2)
        print(f"  re-tagados: {len(mudancas)}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
