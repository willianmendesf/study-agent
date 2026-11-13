#!/usr/bin/env python3
"""pipeline-biblio.py — 2a via de aquisicao SEM COTA (Libgen + Sci-Hub via biblio-mcp).

POR QUE ESTE SCRIPT EXISTE (pedido do William, 2026-11-05):
  "adicione esse no seu fluxo de aquisicoes: https://github.com/yashimosh/biblio-mcp"

O `pipeline-aquisicao.py` usa o z-library, que tem COTA (40 downloads/dia,
reseta 00:00 UTC) e devolveu's vezes"sem resultado". O biblio-mcp abre o
LIBGEN (15M+ livros) e o SCI-HUB (85M+ artigos), que NAO tem cota nenhuma.

A REGRIA DE OURO DESTE SCRIPT:
  O z-library e' a fonte PRIMARIA (tem os formatos em PT-BR, que o acervo
  precisa). O biblio-mcp e' a FALLBACK — entra quando o z-library:
    (a) esta com a cota esgotada, ou
    (b) NAO achou o livro (busca vazia / sem candidato acima do limiar).
  NUNCA o biblio-mcp substitui um resultado bom do z-library: ele baixa
  primeiro o que o z-library tem.

O QUE ESTE SCRIPT FAZ (por obra do catalogo):
  1. Le o catalogo YAML (`--catalogo`).
  2. Pula o que ja esta adquirido (mesmo `pipeline-estado.json`).
  3. Busca no z-library (via `zlib-api.py`) — 1a via.
  4. Se nao achou OU cota esgotada: busca no Libgen via biblio-mcp.
  5. Seleciona o melhor candidato (mesma heuristica do pipeline principal).
  6. Baixa, converte pra .md, cataloga na KB, sobe no BookOrbit.
  7. Registra tudo no `pipeline-estado.json`.

IMPORTANTE — Onde o ebook vive:
  O ebook original vai para `data/biblioteca/_incoming/` e e' APAGADO depois
  que o upload ao BookOrbit for confirmado. O `.md` (versao extraida) e' que
  fica versionado. NUNCA versiona ebook.

Uso:
  pipeline-biblio.py --catalogo data/perfil/bibliotecario/catalogo-ficcao.yaml --max 5
  pipeline-biblio.py --titulo "A Utopia" --autor "Thomas More" --dry
  pipeline-biblio.py --status
"""
import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
ZLIB_API = SCRIPTS / "zlib-api.py"
BIBLIO_API = SCRIPTS / "biblio-api.py"
ESTADO = ROOT / "data" / "perfil" / "bibliotecario" / "pipeline-estado.json"
LOGL = ROOT / "data" / "perfil" / "bibliotecario" / "rodada-log.jsonl"
INCOMING = ROOT / "data" / "biblioteca" / "_incoming"
BIB = ROOT / "data" / "biblioteca"
KB = BIB / "global" / "kb-literatura-mundial-classica.yaml"
EPUB2MD = ROOT / "data" / "perfil" / "bibliotecario" / "biblioteca-orbit" / "epub2md.py"

# ---------------------------------------------------------------------------
# P1/P2 — GATES DUROS (2026-11-08). O lint nao ve conteudo: estes dois
# gates sao o que impede o acervo de mentir.
# ---------------------------------------------------------------------------
try:
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from detectar_idioma import diagnostico as _diag_idioma
except Exception:                                   # sem detector: nao quebra
    _diag_idioma = None


def similar(a, b):
    """Similaridade de duas strings normalizadas (0..1)."""
    import difflib
    return difflib.SequenceMatcher(None, norm(a), norm(b)).ratio()


def titulo_confere(titulo_cand, variantes):
    """O candidato e' a MESMA obra que procuramos?

    BUG (2026-11-08): "Sangue Bom" (Good Country People) casou com "Sangue
    Sabio" (que e' A Wise Blood) — 1 token em comum num titulo de 2, e o
    score passou. Cobertura por token SO nao prova identidade de obra.

    Gate DURO: igualdade, substring, contencao de TODOS os tokens
    significativos, ou similaridade >= 0.85.
    """
    c = norm(titulo_cand)
    if not c:
        return False
    for v in variantes or []:
        if not v or len(str(v).strip()) <= 2:
            continue
        n = norm(v)
        if not n:
            continue
        if c == n:
            return True
        if len(n) > 4 and n in c:
            return True
        tv = [t for t in n.split() if len(t) > 2]
        tc = set(c.split())
        if tv and all(t in tc for t in tv):
            return True
        if similar(n, c) >= 0.85:
            return True
    return False


MIN_BYTES = 20000
MIN_LINHAS = 120
# BUG (2026-11-11): ate 2 tentativas por obra por dia.
MAX_TENTATIVAS_DIA = 2
# BUG (2026-11-11): quantos candidatos tries por obra numa rodada.
MAX_CANDIDATOS = 3

# Formatos aceitos + penalidades de edicao. Mesma politica do pipeline
# principal (scripts/pipeline-aquisicao.py). BUG (2026-11-11): estas
# constantes NAO existiam aqui — a `melhor_candidato` recem-copiada quebrava
# com NameError e a 2a via (sem cota) MORREVA no primeiro item.
EXT_OK = {"epub", "pdf", "mobi", "azw3", "azw", "prc", "fb2"}

# titulos/colecoes que sao COLECAO de varias obras: o acervo deve comprar
# cada obra SEPARADA, nao a antologia.
RUIM = re.compile(
    r"(box|cole[cç][aã]o|obras completas|antologia|c[oó]pia|enciclop|"
    r"cl[aá]ssicos? de ouro|grandes obras|volumes? \d|mundo inteiro|"
    r"acervo|livros? de|sumo|reunidos)", re.I)

# edicoes que NAO sao a obra: adaptacao, resumo, bolso.
DEGRADE = re.compile(
    r"(abreviat|resum[oa]\b|adapta|bolso|cl[aá]ssicos? de ouro|"
    r"vers[aã]o (simplificada|adaptada|abreviada)|"
    r"como ler|em 15 minutos|leitura f[aá]cil)", re.I)

# edicoes aceitaveis mas nao ideais: comentada, bilingue, ilustrada.
MEDIO = re.compile(
    r"(coment[aá]d|comentar|bilingue|ilustrad|anota[cç][aã]o|"
    r"cl[aá]ssicos?world|cl[aá]ssicos? de ouro|ed[ií]c[aã]o)", re.I)

# INTEGRIDADE DO EBOOK (bug real de 2026-11-05):
# O z-library devolveu um .epub de 1,1 MB cujo HEADER era 100 bytes de \x00
# (sem o magic "PK\x03\x04"). O `epub2md.py` conseguiu extrair o texto mesmo
# assim (o .md saiu íntegro, 6132 linhas), mas o BookOrbit REJEITOU o upload
# com "File contents do not match the .epub format" (UPLOAD_CONTENT_INVALID).
# Ou seja: um ebook corrompido no _incoming/ fica orphaned para sempre e faz
# o cron de 15 min falhar com ele a cada rodada.
# Por isso: valida o magic ANTES de declarar o download ok.
MAGIC = {
    ".epub": (b"PK\x03\x04",),
    ".zip": (b"PK\x03\x04",),
    ".mobi": (b"BOOKMOBI",),
    ".azw3": (b"TPZ3",),
    ".pdf": (b"%PDF",),
    ".cbz": (b"PK\x03\x04",),
}


def ebook_integridade(path: Path):
    """Retorna (ok, motivo). Confere o magic do formato + o tamanho minimo."""
    if not path.exists():
        return False, "arquivo nao existe"
    size = path.stat().st_size
    if size < MIN_BYTES:
        return False, "arquivo pequeno demais (%d bytes)" % size
    ext = path.suffix.lower()
    esperados = MAGIC.get(ext)
    if not esperados:
        return True, "formato nao verificado (%s)" % ext
    head = path.read_bytes()[:4096]
    if not any(head.startswith(m) or m in head[:2048] for m in esperados):
        return False, ("conteudo nao corresponde a %s (magic ausente — "
                       "download corrompido?)" % ext)
    return True, "ok"

PESO = {"alta": 0, "media": 1, "baixa": 2}


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------
def log(ev, **kw):
    try:
        LOGL.parent.mkdir(parents=True, exist_ok=True)
        with LOGL.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps({"ts": time.strftime("%Y-%m-%dT%H:%M:%S"),
                                  "evento": ev, **kw}, ensure_ascii=False) + "\n")
    except OSError:
        pass


def sem_acento(s):
    import unicodedata
    # P4 (2026-11-08): NFKD (como o pipeline principal). Antes era NFD, que
    # mantem o 'ª' -> "Alves-Cª-Eca-de-Queiroz" (2a via) contra
    # "Alves-Ca-Eca-de-Queiroz" (1a via): DUAS chaves para a MESMA obra no
    # mesmo estado, e dois arquivos no acervo.
    return "".join(c for c in unicodedata.normalize("NFKD", s or "")
                   if not unicodedata.combining(c))


def norm(s):
    s = sem_acento(s or "").lower()
    s = re.sub(r"[^a-z0-9]+", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def toks(s):
    """Tokens como CONJUNTO (2026-11-13).

    BUG: esta copia devolvia LISTA, mas o score faz `alv_a & a`
    (intersecao de conjuntos, herdada do pipeline-aquisicao.py, onde
    `toks` devolve `set`). Resultado: TypeError
    "unsupported operand type(s) for &: 'list' and 'list'" em TODA
    chamada de `candidatos_ordenados` -> a 2a via (libgen, SEM COTA)
    morria antes de avaliar o 1o candidato desde 2026-11-11.
    """
    return {t for t in norm(s).split() if len(t) > 2}


def slug(titulo, autor):
    """Slug CANONICO — identico ao de pipeline-aquisicao.py.

    BUG (2026-11-07): este script usava um formato PROPRIO
    ("tokens truncados, minusculos"), enquanto o pipeline principal usava
    "Titulo-Autor" com maiusculas. Os DOIS gravam no mesmo
    `pipeline-estado.json` — entao uma obra ja ADQUIRIDA pelo z-library
    aparecia como "pendente" para a 2a via (biblio/libgen) e era re-baixada,
    gastando cota e criando duplicata. Alem disso, cada "falhou" do
    pipeline-biblio poluia o estado com chaves que o pipeline principal
    nunca lia.
    REGRA: quem grava no estado tem de usar a MESMA chave. Alterou o
    formato do slug? Migre o estado (scripts/migrar-estado-pipeline.py).
    """
    s = sem_acento(f"{titulo} - {autor}")
    s = s.replace("—", "-").replace("–", "-")
    s = re.sub(r"[^\w\s-]", "", s)
    s = re.sub(r"[\s_]+", "-", s)
    s = re.sub(r"-{2,}", "-", s).strip("-")
    return s[:70].strip("-")


def carregar_estado():
    if ESTADO.exists():
        try:
            return json.loads(ESTADO.read_text(encoding="utf-8"))
        except ValueError:
            return {}
    return {}


def salvar_estado(est):
    ESTADO.parent.mkdir(parents=True, exist_ok=True)
    ESTADO.write_text(json.dumps(est, ensure_ascii=False, indent=1), encoding="utf-8")


def run_json(cmd, timeout=180):
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    out = (r.stdout or "").strip()
    if not out:
        return None, (r.stderr or "")[-300:]
    try:
        return json.loads(out), None
    except ValueError:
        # as vezes o stdout tem logs antes do json: pega o ultimo bloco
        i = out.find("[")
        j = out.rfind("]")
        if i >= 0 and j > i:
            try:
                return json.loads(out[i:j + 1]), None
            except ValueError:
                pass
        i = out.find("{")
        j = out.rfind("}")
        if i >= 0 and j > i:
            try:
                return json.loads(out[i:j + 1]), None
            except ValueError:
                pass
    return None, out[-300:]


# ---------------------------------------------------------------------------
# catalogo
# ---------------------------------------------------------------------------
def carrega_catalogo(path):
    import yaml
    data = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    if isinstance(data, dict):
        for k in ("obras", "itens", "livros", "catalogo"):
            if k in data and isinstance(data[k], list):
                return data[k]
        return []
    return data if isinstance(data, list) else []


def normaliza_item(x):
    if not isinstance(x, dict):
        return None
    titulo = (x.get("titulo") or x.get("title") or "").strip()
    if not titulo:
        return None
    return {
        "titulo": titulo,
        "autor": (x.get("autor") or x.get("author") or "").strip(),
        "prioridade": (x.get("prioridade") or "media").lower(),
        "tags": [t for t in (x.get("tags") or []) if t],
        "ano": str(x.get("ano") or ""),
        "subpasta": (x.get("subpasta") or "outros"),
        "titulo_en": (x.get("titulo_en") or "").strip(),
        "titulos_alt": [t for t in (x.get("titulos_alt") or []) if t],
    }


# ---------------------------------------------------------------------------
# FONTE 1 — z-library (primaria, tem cota)
# ---------------------------------------------------------------------------
def busca_zlib(query, limit=25):
    d, err = run_json([sys.executable, str(ZLIB_API), "search", query, "--limit", str(limit)])
    if not isinstance(d, list):
        return []
    out = []
    for b in d:
        out.append({
            "id": b.get("id"), "hash": b.get("hash"),
            "title": b.get("title"), "author": b.get("author"),
            "extension": (b.get("extension") or "").lower(),
            "lang": b.get("lang"), "year": b.get("year"),
            "size": b.get("size"), "publisher": b.get("publisher"),
            "fonte": "zlib",
        })
    return out


def cota_zlib():
    """O `zlib-api.py limits` imprime TEXTO (nao JSON). Parse por regex.

    Formato real medido (2026-11-05):
      "  zlib2: today=0 limit=10 remaining=10 err="

    BUG (2026-11-09): quando o z-library caia, o `zlib-api.py limits` ficava
    sondando 18 dominios e o `subprocess.run(..., timeout=120)` estourava
    `TimeoutExpired` — que NAO era tratado. A 2a via SEM COTA (libgen), que
    existe JUSTAMENTE para quando o z-library falha, MORREU com traceback
    justo no dia em que era necessaria. Agora o timeout e' tratado e a cota
    vira 0 com aviso — a via alternativa SEGUE funcionando.
    """
    try:
        r = subprocess.run([sys.executable, str(ZLIB_API), "limits"],
                           capture_output=True, text=True, timeout=120)
        stdout = r.stdout or ""
    except subprocess.TimeoutExpired:
        print("[biblio] zlib-api limits estourou o timeout (z-library "
              "provavelmente fora do ar) — seguindo sem cota", flush=True)
        return 0, "z-library inacessivel (timeout)"
    except Exception as e:
        print("[biblio] zlib-api limits falhou: %s" % e, flush=True)
        return 0, "z-library inacessivel (%s)" % e
    total = 0
    linhas = []
    for m in re.finditer(r"(\S+):\s*today=(\d+)\s+limit=(\d+)\s+remaining=(\d+)",
                         stdout):
        alias, _today, _limit, rem = m.groups()
        total += int(rem)
        linhas.append("%s=%s" % (alias, rem))
    return total, ", ".join(linhas)


# ---------------------------------------------------------------------------
# FONTE 2 — biblio-mcp (Libgen + Anna's + Sci-Hub) — SEM COTA
# ---------------------------------------------------------------------------
def busca_biblio(query, limit=25):
    d, err = run_json([sys.executable, str(BIBLIO_API), "search", query, "--limit", str(limit)])
    if not isinstance(d, list):
        return []
    out = []
    for b in d:
        out.append({
            "id": None, "hash": None, "md5": b.get("md5"),
            "title": b.get("title"), "author": b.get("author"),
            "extension": (b.get("format") or "").lower(),
            "lang": b.get("language"), "year": b.get("year"),
            "size": b.get("size"), "publisher": b.get("publisher"),
            "fonte": "biblio",
        })
    return out


def baixa_biblio(cand, destino):
    """Baixa via biblio-mcp. Retorna (caminho, info) ou (None, erro)."""
    d, err = run_json([sys.executable, str(BIBLIO_API), "download", cand["md5"],
                        "--dest", str(destino.parent)], timeout=320)
    if not isinstance(d, dict) or not d.get("ok"):
        return None, (d.get("erro") if isinstance(d, dict) else None) or "download falhou"
    p = Path(d["path"])
    if not p.exists() or p.stat().st_size < MIN_BYTES:
        return None, "arquivo vazio/pequeno demais"
    ok, motivo = ebook_integridade(p)
    if not ok:
        # NAO deixa o arquivo corrompido no _incoming/ (o cron de 15 min
        # tentaria subir esse lixo a cada rodada e falharia sempre).
        try:
            p.unlink()
        except OSError:
            pass
        return None, "integridade falhou: %s" % motivo
    # renomeia com o nome do livro (o MCP devolve <md5>.<ext>)
    ext = p.suffix.lower() or ".epub"
    final = destino.parent / (destino.stem + ext)
    if final != p:
        shutil.move(str(p), str(final))
    return final, "%d KB %s" % (final.stat().st_size // 1024, ext)


# ---------------------------------------------------------------------------
# selecao (mesma heuristica do pipeline principal)
# ---------------------------------------------------------------------------

def _toks_fuzzy(a, b):
    """Dois tokens sao o mesmo com variacao morfologica minima?
    'kroger' ~ 'kroeger', 'dubliners' ~ 'dublineses'. Regra conservadora:
    prefixo comum >= 4 chars, diferenca de tamanho <= 2, ambos >= 5 chars."""
    if a == b:
        return True
    if len(a) < 5 or len(b) < 5 or abs(len(a) - len(b)) > 2:
        return False
    p = 0
    for x, y in zip(a, b):
        if x != y:
            break
        p += 1
    return p >= 4



def candidatos_ordenados(books, titulo_pt, autor_pt, titulo_en="", titulos_alt=None,
                         minimo=0.55):
    """Todos os candidatos ACEITAVEIS, do melhor para o pior.

    BUG (2026-11-11): o pipeline escolhia UM candidato; se a conversao
    falhasse (idioma errado, exemplar corrompido), a obra ficava pendente e
    a PROXIMA rodada gastava cota de novo no MESMO exemplar defeituoso.
    Agora o pipeline tem uma lista e tenta o proximo quando a conversao falha."""
    variantes = [v for v in ([titulo_pt, titulo_en] + list(titulos_alt or []))
                 if v and len(str(v).strip()) > 2]
    norm_pt = norm(titulo_pt)
    norm_locais = {norm_pt} | {norm(v) for v in (titulos_alt or [])}
    norm_todas = norm_locais | ({norm(titulo_en)} if titulo_en else set())
    alv_a = toks(autor_pt)
    scored = []
    for b in books:
        raw = b.get("title", "") or ""
        aut_raw = b.get("author", "") or ""
        if not titulo_confere(raw, variantes):
            continue
        ext = (b.get("extension") or "").lower()
        lang = (b.get("lang") or "").lower()
        if ext not in EXT_OK:
            continue
        if lang and "portugu" not in lang and "english" not in lang:
            continue
        pen = 0.0
        if RUIM.search(raw):
            pen += 0.30
        if DEGRADE.search(raw):
            pen += 0.55
        elif MEDIO.search(raw):
            pen += 0.20
        t = toks(raw)
        a = toks(aut_raw)
        cov = 0.0
        contido = False
        for var in variantes:
            tv = toks(var)
            if tv:
                c = 0.0
                for tv1 in tv:
                    if tv1 in t or any(_toks_fuzzy(tv1, t2) for t2 in t):
                        c += 1
                cov = max(cov, c / len(tv))
            nv = norm(var)
            if len(nv) > 6 and nv in norm(raw):
                contido = True
        nraw = norm(raw)
        exacto = nraw in norm_todas
        exacto_local = nraw in norm_locais
        cov_a = len(alv_a & a) / max(1, len(alv_a))
        s = cov * 0.62 + cov_a * 0.28 - pen
        if exacto:
            s += 0.30 if exacto_local else 0.12
        elif contido:
            s += 0.22
        s += {"epub": 0.10, "pdf": 0.04, "azw3": 0.03, "mobi": 0.02}.get(ext, 0.0)
        if "portugu" in lang:
            s += 0.20
        else:
            s -= 0.10
        if len(t) < 2 and not exacto:
            s -= 0.35
        raw_norm = "".join(
            c for c in unicodedata.normalize("NFD", raw)
            if unicodedata.category(c) != "Mn").lower()
        sufixo_outra_obra = re.search(
            r"\(\s*(manga|hq|graphic|ilustr\w*|adapt\w*|resum\w*|guia|inicia\w*|"
            r"coment\w*|ilustrado|colorido|adaptado|vers[aã]o|para o teatro)\s*\)",
            raw_norm, re.I)
        if sufixo_outra_obra:
            s -= 0.75 if cov_a < 0.5 else 0.50
        if cov_a == 0.0 and len(alv_a) > 0:
            s -= 0.40
        scored.append((s, b))
    scored.sort(key=lambda x: -x[0])
    return [(b, round(s, 3)) for s, b in scored if s >= minimo]


def melhor_candidato(books, titulo_pt, autor_pt, titulo_en="", titulos_alt=None):
    """Melhor candidato (o 1o da lista ordenada)."""
    lst = candidatos_ordenados(books, titulo_pt, autor_pt, titulo_en, titulos_alt)
    if lst:
        return lst[0]
    # devolve o melhor MESMO abaixo do limiar, para o log mostrar o score
    todos = candidatos_ordenados(books, titulo_pt, autor_pt, titulo_en, titulos_alt,
                                 minimo=-99)
    if todos:
        return None, todos[0][1]
    return None, -99


def _sobrenomes(autor):
    """Tokens do autor que provam autoria no texto. Ignora prenomes
    curtos/common e as particulas (de, da, do)."""
    stop = {"o", "a", "os", "as", "de", "do", "da", "dos", "das", "e",
            "j", "w", "sir", "lady", "lord", "jean", "von", "van", "der"}
    out = set()
    for t in re.findall(r"[a-z0-9]+", sem_acento(autor or "").lower()):
        if len(t) >= 4 and t not in stop:
            out.add(t)
    return out


def _primeiras_linhas(texto, n=25):
    linhas = [l.strip() for l in (texto or "").split("\n") if l.strip()]
    return "\n".join(linhas[:n])


def _tem_token(bloco, tokens):
    b = sem_acento(bloco or "").lower()
    return any(re.search(r"\b" + re.escape(sem_acento(t)) + r"\b", b) for t in tokens)


def _titulo_dentro(corpo_norm, variante):
    """O titulo aparece no texto — por igualdade, ou pelos tokens (com
    tolerancia de transliteracao: 'Kroeger' vs 'Kröger').

    BUG (2026-11-11): a busca por string exata ("tonio kroeger") falhava
    quando o texto escreve "Tonio Kröger" -> "kroger". O texto esta CORRETO
    (e' a obra do Thomas Mann), mas o gate dizia "conteudo divergente"."""
    if not variante:
        return False
    v = norm(variante)
    if v and v in corpo_norm:
        return True
    vt = [x for x in re.findall(r"[a-z0-9]+", sem_acento(variante).lower()) if len(x) >= 3]
    ct = set(re.findall(r"[a-z0-9]+", corpo_norm))

    def vt_norm(t):
        return t.replace("oe", "o").replace("ae", "a").replace("ue", "u")

    if not vt:
        return False
    for t in vt:
        if not any(x == t or vt_norm(x) == vt_norm(t)
                   or (len(x) >= 4 and len(t) >= 4 and x[0] == t[0]
                       and x[-1] == t[-1] and x.replace("oe", "") == t.replace("oe", ""))
                   for x in ct):
            return False
    return True


def _titulo_exato(bloco, variante):
    """O titulo pedido aparece como TITULO (linha propria ou cabecalho),
    e nao como substring de outro titulo.

    BUG GRAVE (2026-11-11): "A Perdição" casou com a linha "MINHA PERDIÇÃO
    faz parte de uma serie de mafia..." — a palavra "perdição" esta dentro de
    um titulo DIFERENTE. Por isso a comparacao e' por tokens + forma, e nao
    por substring.

    TOLERANCIA DE TRANSLITERACAO: "Kroeger" (catalogo) vs "Kröger" (no texto)
    — o mesmo nome em grafias diferentes. Compara por tokens com matching
    tolerante a 'oe'/'ö' e ao troca de vogais simples."""
    if not variante:
        return False
    tv = [x for x in re.findall(r"[a-z0-9]+", sem_acento(variante).lower()) if len(x) >= 3]
    if not tv:
        return False

    def variante_token(t):
        return t.replace("oe", "o").replace("ae", "a").replace("ue", "u")

    def casa(a, b):
        if a == b:
            return True
        if variante_token(a) == variante_token(b):
            return True
        # kroeger vs kroger: remove a vogal intermediaria e compara
        if len(a) >= 4 and len(b) >= 4 and a[0] == b[0] and a[-1] == b[-1]:
            if a.replace("oe", "") == b.replace("oe", ""):
                return True
        return False

    for ln in [l.strip() for l in (bloco or "").split("\n")][:30]:
        lt = [x for x in re.findall(r"[a-z0-9]+", sem_acento(ln).lower()) if len(x) >= 3]
        if not lt:
            continue
        # casa cada token do titulo com um token da linha (sem repetir)
        usados = set()
        ok = True
        for t in tv:
            achou = None
            for i, x in enumerate(lt):
                if i not in usados and casa(t, x):
                    achou = i
                    break
            if achou is None:
                ok = False
                break
            usados.add(achou)
        if not ok:
            continue
        # a linha tem TODOS os tokens do titulo, e nao tem nenhum token
        # a mais que "qualifica" outro titulo (ex.: "minha" antes de "perdição").
        extras = [x for x in lt if x not in tv and
                  not any(casa(x, t) for t in tv)]
        # tolera qualificadores COMUNS de linha editorial
        tolerados = {"minha", "meu", "um", "uma", "the", "a", "o", "de",
                     "obra", "livro", "edicao", "volume", "parte", "colecao"}
        if not [x for x in extras if x not in tolerados]:
            return True
    return False


def autor_confere(texto, autor, variantes=None):
    """O texto prova que e' do AUTOR pedido?

    BUG GRAVE (2026-11-11): "A Perdição" (Eça de Queiroz) foi gravada com o
    texto de "Minha perdição" — um romance de outra autora (Sara Ester, Liam e
    Aurora). O gate checava SO o titulo, e "perdição" aparece DENTRO do texto
    errado.

    REGRA (medida nas 11 obras da rodada):
      1. o sobrenome do autor aparece no texto -> aceito;
      2. nao aparece, mas ALGUM token do autor aparece (ex.: o prenome) ->
         aceito (algumas edicoes so trazem o prenome);
      3. NENHUM token do autor -> so aceito se o TITULO aparece na ficha
         catalografica como titulo PROPRIO (nao como substring de outro).
         Medido:
           - "Tonio Kroeger" (Thomas Mann): o autor nao aparece no corpo, mas
             a 1a linha do arquivo e' o titulo -> e' a obra certa;
           - "A Perdição" trocada: a linha e' "MINHA PERDIÇÃO faz parte de uma
             serie de mafia" -> o titulo pedido aparece como PARTE de outro
             titulo -> rejeita.
    """
    sob = _sobrenomes(autor)
    if not sob:
        return True          # autor sem sobrenome utilizavel: nao bloqueia
    corpo = sem_acento(texto or "").lower()
    if any(re.search(r"\b" + re.escape(t) + r"\b", corpo) for t in sob):
        return True
    todos = {t for t in re.findall(r"[a-z0-9]+", sem_acento(autor or "").lower())
             if len(t) >= 3}
    if any(re.search(r"\b" + re.escape(t) + r"\b", corpo) for t in todos):
        return True
    # ultimo recurso: o titulo na ficha catalografica, como titulo PROPRIO
    for v in (variantes or []):
        if _titulo_exato(_primeiras_linhas(texto), v):
            return True
    return False


def conteudo_confere(texto, titulo, variantes=None, autor=None):
    """Confere que o texto e' do livro certo. Busca no texto INTEIRO (bug de
    2026-11-05: EPUBs sem folha de rosto so citam o titulo no fim).

    BUG (2026-11-11): aceitava SO o titulo PT literal. A obra pode estar no
    acervo brasileiro com OUTRO titulo (alias) — "Retratos" (Joyce) e' "Dublineses",
    "Uma História de Duas Cidades" e' "Um Conto de Duas Cidades". Agora aceita
    qualquer variante (PT, EN, aliases).

    BUG GRAVE (2026-11-11): o titulo sozinho nao prova a obra. "A Perdição" do
    Eça casou com "Minha perdição" (outra autora). Agora checa o AUTOR tambem."""
    corpo = norm(texto)
    alvos = [titulo] + list(variantes or [])
    achou = False
    for t in alvos:
        if _titulo_dentro(corpo, t):
            achou = True
            break
    if not achou:
        for t in alvos:
            n = norm(t)
            partes = [p for p in n.split() if len(p) > 3 and p not in ("de", "da", "do", "e")]
            if partes and all(p in corpo for p in partes[:3]):
                achou = True
                break
    if not achou:
        return False
    if autor and not autor_confere(texto, autor, alvos):
        return False
    return True


def converte(ebook, titulo, autor, tags, ano, subpasta, variantes=None,
             permitir_en=False):
    tmp = Path(tempfile.mkdtemp(prefix="biblio-conv-"))
    try:
        r = subprocess.run([sys.executable, str(EPUB2MD), "--dest", str(tmp), str(ebook)],
                           capture_output=True, text=True, timeout=2400)
        mds = list(tmp.glob("*.md"))
        if not mds:
            return None, "conversao-sem-md"
        gerado = max(mds, key=lambda p: p.stat().st_size)
        txt = gerado.read_text(encoding="utf-8", errors="ignore")
        linhas = txt.count("\n")
        if gerado.stat().st_size < MIN_BYTES or linhas < MIN_LINHAS:
            return None, ("texto-curto (%d KB, %d lin) — extracao provavelmente falhou"
                          % (gerado.stat().st_size // 1024, linhas))
        if not conteudo_confere(txt, titulo, variantes, autor):
            return None, "conteudo-divergente: titulo '%s' nao aparece no texto" % titulo
        # P2 (2026-11-08): GATE DE IDIOMA no TEXTO. A rampa e' PT-BR; um
        # exemplar em espanhol/ingles NAO substitui o PT-BR. Foi exatamente
        # o que aconteceu com "Alves & C.a": a 2a via trouxe a edicao
        # ESPANOLA e ela foi gravada em .../portugues/.
        if _diag_idioma is not None:
            diag = _diag_idioma(txt)
            # BUG (2026-11-11): para as obras marcadas "gap-idioma" (PT-BR
            # inexistente no z-library), o exemplar em ingles E' aceitavel —
            # e a KB registra o idioma REAL, entao o acervo nao mente. Sem
            # isso, "A Utopia" gastava cota downloading a edicao inglesa e
            # depois rejeitava o proprio download.
            # REGRA (2026-11-11): so PT e EN. O ESPANHOL nunca entra
            # (a rampa e' PT-BR) — e o gate de ES era contornado
            # quando o METADADO do z-library dizia "Portuguese" para
            # uma traducao espanhola (medido em "Dublineses", Joyce).
            _ok = diag.startswith("pt") or (permitir_en and diag.startswith("en"))
            if not _ok:
                return None, "idioma-nao-pt (%s) — a rampa e' PT-BR" % diag
        dest_dir = BIB / "literatura-mundial-classica" / subpasta
        dest_dir.mkdir(parents=True, exist_ok=True)
        destino = dest_dir / ("%s.md" % slug(titulo, autor))
        shutil.move(str(gerado), str(destino), copy_function=os.replace)
        return destino, "ok"
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def cataloga(destino, titulo, autor, tags, ano, fonte, idioma="Portuguese"):
    """P3 (2026-11-08): o `idioma` na KB era fixo em 'Portuguese' — a KB
    MENTIA sobre o acervo (edicao espanhola gravada como portuguesa)."""
    rel = ("./data/biblioteca/literatura-mundial-classica/"
           + str(destino.relative_to(BIB / "literatura-mundial-classica")))
    if not KB.exists():
        return "KB-ausente"
    txt = KB.read_text(encoding="utf-8")
    if rel in txt:
        return "ja-catalogado"
    tags_yaml = ", ".join(tags) if tags else "ficcao"
    linha = ("  - titulo: LT %s - %s\n"
             "    caminho_md: %s\n"
             "    tamanho_md: %d KB\n"
             "    linhas_md: %d\n"
             "    idioma: %s\n"
             "    tags: [%s]\n"
             "    ano: %s\n"
             "    status: indexado_auto\n"
             "    origem: pipeline-biblio-mcp\n"
             "    fonte_aquisicao: %s\n"
             % (titulo, autor, rel, destino.stat().st_size // 1024,
                destino.read_text(encoding="utf-8", errors="ignore").count("\n"),
                idioma, tags_yaml, ano, fonte))
    # BUG (2026-11-05): o regex procurava a chave "knowledge_base_literatura",
    # mas a KB real se chama "knowledge_base_literatura_mundial_classica" ->
    # o cataloga() retornava "falha-bloco-kb" e a obra NUNCA entrava na KB
    # (o .md existia, mas a KB nao — o acervo ficava invisivel pros
    # especialistas). Agora o regex casa QUALQUER bloco "knowledge_base_*"
    # que tenha "materiais:", e o cataloga() insere no bloco certo.
    m = re.search(r"^knowledge_base_[a-z_]*:\n(?:.*\n)*?^\s*materiais:\s*\n", txt, re.M)
    if not m:
        return "falha-bloco-kb"
    KB.write_text(txt[:m.end()] + linha + txt[m.end():], encoding="utf-8")
    return "catalogado"


def frontmatter(titulo, autor, tags, ano, idioma="Portuguese"):
    """Frontmatter do .md.

    BUG (2026-11-07): o `idioma` era fixo em "Portuguese", mas a 2a via
    (libgen) pode trazer a obra em INGLES (a traducao PT nao existia). O
    frontmatter dizia "Portuguese" sobre um texto em ingles — o acervo
    mentia sobre o proprio idioma. Agora o idioma vem do CANDIDATO real.
    """
    t = ", ".join('"%s"' % x for x in (tags or ["ficcao"]))
    return ("---\n"
            "titulo: \"%s\"\n"
            "autor: \"%s\"\n"
            "idioma: %s\n"
            "tipo: livro\n"
            "tags: [%s]\n"
            "ano: \"%s\"\n"
            "origem: pipeline-biblio-mcp\n"
            "---\n\n" % (titulo, autor, idioma, t, ano))


def subir_orbit(ebook, autor=""):
    """Sobe o ebook ao BookOrbit (1 login, sessão única) e apaga o local.

    BUG (2026-11-05): a 1a versão chamava `orbit-upload.py <arquivo>` POSICIONAL.
    O script usa `--file` (e nao aceita posicional) → argparse reclamava
    "unrecognized arguments" e o upload NUNCA acontecia (o ebook ficava
    no _incoming/ para sempre). Agora usa a forma correta.
    """
    up = ROOT / "scripts" / "orbit-upload.py"
    if not up.exists():
        return False, "orbit-upload.py ausente"
    cmd = [sys.executable, str(up), "--file", str(ebook)]
    if autor:
        cmd += ["--autor", autor]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
    except subprocess.TimeoutExpired:
        return False, "timeout no upload"
    out = (r.stdout or "") + (r.stderr or "")
    low = out.lower()
    # 409 UPLOAD_DESTINATION_CONFLICT = o livro JA esta no acervo (o
    # BookOrbit nomeia pelo TITULO extraido do metadata do epub, nao pelo
    # filename). Nao e falha: e o estado desejado. O arquivo local e' apagado
    # (o .md ja esta versionado; o ebook e' redundante).
    ja_esta = ("destination_conflict" in low or "already exists" in low
               or '"statuscode": 409' in low or '"statuscode":409' in low)
    ok = r.returncode == 0 and ("ok" in low or "enviado" in low
                                or "upload" in low or "sucesso" in low)
    if ok or ja_esta:
        try:
            ebook.unlink()
        except OSError:
            pass
    if ja_esta:
        return True, "JA ESTA NO ACERVO (409 destino) — local preservado: nao"
    return ok, out[-220:]


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--catalogo")
    ap.add_argument("--titulo", help="processa so este titulo (ad-hoc)")
    ap.add_argument("--autor", default="")
    ap.add_argument("--prioridade", default="media")
    ap.add_argument("--tags", default="")
    ap.add_argument("--max", type=int, default=5)
    ap.add_argument("--dry", action="store_true")
    ap.add_argument("--status", action="store_true")
    ap.add_argument("--sem-orbit", action="store_true")
    ap.add_argument("--so-biblio", action="store_true",
                    help="ignora o z-library e usa SO o biblio-mcp (teste do fallback)")
    args = ap.parse_args()

    estado = carregar_estado()

    if args.status:
        print("=== pipeline-biblio (2a via, sem cota) ===")
        print("estado:", ESTADO.relative_to(ROOT))
        c, lin = cota_zlib()
        print("cota z-library restante:", c, "(%s)" % lin)
        print("fonte alternativa: biblio-mcp (Libgen + Anna's Archive + Sci-Hub)")
        return 0

    if args.titulo:
        itens = [{"titulo": args.titulo, "autor": args.autor,
                  "prioridade": args.prioridade,
                  "tags": [t.strip() for t in args.tags.split(",") if t.strip()],
                  "ano": "", "subpasta": "outros", "titulo_en": "",
                  "titulos_alt": []}]
    elif args.catalogo:
        itens = [normaliza_item(x) for x in carrega_catalogo(args.catalogo)]
        itens = [x for x in itens if x]
    else:
        print("ERRO: --catalogo ou --titulo", file=sys.stderr)
        return 2

    def ordem(it):
        st = estado.get(slug(it["titulo"], it["autor"]), {})
        tentado = 1 if st.get("tentado") else 0
        return (PESO.get(it["prioridade"], 1), tentado, it["titulo"])
    itens.sort(key=ordem)

    INCOMING.mkdir(parents=True, exist_ok=True)
    cota, lin_cota = cota_zlib()
    print("cota z-library: %d (%s)" % (cota, lin_cota))
    print("fonte alternativa sem cota: biblio-mcp (libgen.li)")

    baixados = falhas = 0
    for it in itens:
        if baixados >= args.max:
            break
        s = slug(it["titulo"], it["autor"])
        st = estado.get(s, {})
        if st.get("status") == "adquirido":
            continue
        if st.get("tentado") and st.get("status") == "falhou" and not args.titulo:
            # ja falhou uma vez: nao repete no mesmo dia (cota e precious)
            #
            # BUG (2026-11-10): este bloco foi corrigido no pipeline PRINCIPAL
            # em 2026-11-09, mas a correcao NUNCA foi replicada aqui. O
            # `continue` sem comparar a DATA travava a obra PARA SEMPRE:
            # as 46 falhas do catalogo estavam bloqueadas desde 2026-11-06 e
            # nenhuma voltaria a ser tentada — nem pela 2a via (libgen), que
            # nao gasta cota. Por isso a rodada de 2026-11-10 rodou e
            # processou ZERO itens, apesar de 41 obras do catalogo estarem
            # sem estado (nunca tentadas).
            # Agora so' bloqueia se a tentativa for do MESMO DIA e nao for
            # uma falha de REDE (rede nao e' culpa da obra).
            hoje = time.strftime("%Y-%m-%d")
            tentativa = st.get("tentado")
            motivo = (st.get("motivo") or "")
            falha_de_rede = ("download falhou: download falhou" in motivo
                             or "z-library inacessivel" in motivo
                             or "sem resposta" in motivo
                             or "nenhum link direto baixou" in motivo)
            # BUG (2026-11-11): o bloqueio era "1 tentativa por dia, sem
            # excecao". As 13 pendentes ja tinham falhado as 00:17 UTC e a
            # rodada das 07:15 nao podia nem tentar de novo — sobrando 64 de
            # cota. Agora: ate MAX_TENTATIVAS_DIA tentativas por obra por dia
            # (a 1a falha pode ser de BUG, nao da obra) e falha de REDE nunca
            # bloqueia.
            if tentativa == hoje and not falha_de_rede:
                if (st.get("n_tentativas") or 0) >= MAX_TENTATIVAS_DIA:
                    continue
            # se a tentativa e' de hoje mas foi FALHA DE REDE, nao bloqueia:
            # a obra nao e' responsavel e o dia ainda comeca.

        queries = ["%s %s" % (it["titulo"], it["autor"])]
        if it["titulo_en"]:
            queries.append("%s %s" % (it["titulo_en"], it["autor"]))
        for alt in it["titulos_alt"]:
            queries.append("%s %s" % (alt, it["autor"]))

        # ---- FONTE 1: z-library (primaria) ----
        books = []
        if (cota > 0 or args.dry) and not args.so_biblio:
            for q in queries:
                books += busca_zlib(q)
                # nao interrompe no primeiro resultado: as queries seguintes
                # podem trazer o exemplar EN (que o filtro PT esconde)
            if books:
                print("[zlib] %d resultado(s) p/ %s" % (len(books), it["titulo"]))
            if books:
                print("[zlib] %d resultado(s) p/ %s" % (len(books), it["titulo"]))

        cand = None
        score = 0.0
        fonte = "zlib"
        if books:
            cand, score = melhor_candidato(books, it["titulo"], it["autor"],
                                           it["titulo_en"], it["titulos_alt"])

        # ---- FONTE 2: biblio-mcp (fallback, SEM COTA) ----
        if (not cand or score < 0.85 or args.so_biblio) and args.dry is False:
            print("[biblio] z-library nao serviu p/ %s (score %s) — tentando libgen"
                  % (it["titulo"], score))
            b2 = []
            for q in queries:
                b2 += busca_biblio(q)
                if b2:
                    break
            if b2:
                cand2, score2 = melhor_candidato(b2, it["titulo"], it["autor"],
                                                  it["titulo_en"], it["titulos_alt"])
                if cand2 and score2 > score:
                    cand, score, fonte = cand2, score2, "biblio"
                    print("[biblio] %d resultado(s) — melhor score %s"
                          % (len(b2), score2))

        if not cand:
            estado[s] = {"status": "falhou", "tentado": time.strftime("%Y-%m-%d"),
                         "n_tentativas": (st.get("n_tentativas") or 0) + 1,
                         "motivo": "sem candidato em zlib nem biblio"}
            salvar_estado(estado)
            print("[SEM-CANDIDATO] %s — %s" % (it["titulo"], it["autor"]))
            log("sem_candidato_biblio", titulo=it["titulo"], autor=it["autor"])
            falhas += 1
            continue

        print("[CANDIDATO] %s <- %s (%s, %s, score %s, fonte %s)"
              % (it["titulo"], (cand.get("title") or "")[:60],
                 cand.get("extension"), cand.get("lang"), score, fonte))

        if args.dry:
            continue

        # ---- download ----
        if fonte == "biblio":
            ebook, info = baixa_biblio(cand, INCOMING / s)
        else:
            ebook, info = baixa_zlib(cand, INCOMING / s)
        if not ebook:
            # BUG (2026-11-07): quando o z-library tem COTA mas o DOWNLOAD
            # falha (cota real esgotada na conta, downloadLink expirado,
            # link quebrado), a 2a via NAO caia para o libgen — que e' justamente
            # a fonte SEM COTA. A obra era marcada "falhou" e a cota do dia
            # se perdia. Agora: se o download do z-library falhar, tenta o
            # libgen ANTES de desistir.
            if fonte == "zlib" and not args.dry:
                print("[zlib] download falhou p/ %s (%s) — tentando libgen "
                      "(fonte sem cota)" % (it["titulo"], info))
                b3 = []
                for q in queries:
                    b3 += busca_biblio(q)
                    if b3:
                        break
                if b3:
                    cand3, score3 = melhor_candidato(
                        b3, it["titulo"], it["autor"],
                        it["titulo_en"], it.get("titulos_alt"))
                    if cand3 and score3 >= 0.55:
                        ebook3, info3 = baixa_biblio(cand3, INCOMING / s)
                        if ebook3:
                            ebook, info, fonte = ebook3, info3, "biblio"
                            cand = cand3
                            print("[biblio] recuperado via libgen: %s (%s)"
                                  % (it["titulo"], info3))
            if not ebook:
                estado[s] = {"status": "falhou", "tentado": time.strftime("%Y-%m-%d"),
                         "n_tentativas": (st.get("n_tentativas") or 0) + 1,
                             "motivo": "download falhou: %s" % info}
                salvar_estado(estado)
                print("[DOWNLOAD-FALHOU] %s: %s" % (it["titulo"], info))
                log("download_falhou_biblio", titulo=it["titulo"], erro=info)
                falhas += 1
                continue
        if fonte == "zlib":
            cota = max(0, cota - 1)

        # ---- conversao ----
        _vars = [v for v in ([it["titulo"], it.get("titulo_en")]
                              + list(it.get("titulos_alt") or [])) if v]
        _gap_en = any("gap-idioma" in (t or "").lower()
                      for t in (it.get("tags") or []))
        destino, msg = converte(ebook, it["titulo"], it["autor"], it["tags"],
                                it["ano"], it["subpasta"], _vars, _gap_en)
        if not destino:
            estado[s] = {"status": "falhou", "tentado": time.strftime("%Y-%m-%d"),
                         "n_tentativas": (st.get("n_tentativas") or 0) + 1,
                         "motivo": "conversao: %s" % msg}
            salvar_estado(estado)
            print("[CONVERSAO-FALHOU] %s: %s" % (it["titulo"], msg))
            log("conversao_falhou_biblio", titulo=it["titulo"], erro=msg)
            falhas += 1
            continue

        # ---- catalogacao + frontmatter ----
        _idioma_txt = "Portuguese"
        try:
            _d = _diag_idioma(destino.read_text(encoding="utf-8", errors="ignore")) \
                if _diag_idioma else "pt"
            _idioma_txt = ("Portuguese" if _d.startswith("pt") else
                           "English" if _d.startswith("en") else
                           "Spanish" if _d.startswith("es") else
                           "French" if _d.startswith("fr") else
                           "Italian" if _d.startswith("it") else "Portuguese")
        except Exception:
            pass
        st_cat = cataloga(destino, it["titulo"], it["autor"], it["tags"], it["ano"], fonte, _idioma_txt)
        # idioma REAL do candidato (a 2a via pode trazer a obra em ingles)
        cand_lang = str((cand.get("lang") or cand.get("language") or "")).lower()
        idioma = "Portuguese" if ("portugu" in cand_lang or not cand_lang) else (
            "English" if "english" in cand_lang else cand_lang.title())
        destino.write_text(frontmatter(it["titulo"], it["autor"], it["tags"], it["ano"], idioma)
                           + destino.read_text(encoding="utf-8"), encoding="utf-8")

        # ---- orbit ----
        if not args.sem_orbit:
            ok, msg = subir_orbit(ebook, it["autor"])
            print("[ORBIT] %s — %s" % ("enviado" if ok else "falhou", msg))
        else:
            print("[ORBIT] pulado (--sem-orbit); ebook em %s" % ebook.name)

        estado[s] = {"status": "adquirido", "titulo": it["titulo"],
                     "autor": it["autor"], "fonte": fonte, "md5": cand.get("md5"),
                     "caminho_md": str(destino.relative_to(ROOT)),
                     "quando": time.strftime("%Y-%m-%d %H:%M")}
        salvar_estado(estado)
        print("[OK] %s -> %s" % (it["titulo"], destino.relative_to(ROOT)))
        log("adquirido_biblio", titulo=it["titulo"], autor=it["autor"], fonte=fonte)
        baixados += 1

    print("\nbaixados: %d · falhas: %d" % (baixados, falhas))
    return 0 if baixados else 1


def baixa_zlib(cand, destino):
    """Baixa no z-library. Retorna (caminho, info) ou (None, erro)."""
    d, err = run_json([sys.executable, str(ZLIB_API), "download",
                        str(cand.get("id")), str(cand.get("hash")),
                        "--dest", str(destino.parent)], timeout=320)
    if not isinstance(d, dict) or not d.get("ok"):
        return None, (d.get("erro") if isinstance(d, dict) else None) or "download falhou"
    p = Path(d["path"])
    if not p.exists() or p.stat().st_size < MIN_BYTES:
        return None, "arquivo vazio/pequeno demais"
    ok, motivo = ebook_integridade(p)
    if not ok:
        try:
            p.unlink()
        except OSError:
            pass
        return None, "integridade falhou: %s" % motivo
    return p, "%d KB %s" % (p.stat().st_size // 1024, p.suffix.lstrip("."))


if __name__ == "__main__":
    sys.exit(main())
