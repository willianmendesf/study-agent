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
    return [t for t in norm(s).split() if len(t) > 2]


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
def melhor_candidato(books, titulo_pt, autor_pt, titulo_en="", titulos_alt=None):
    """Escolhe o melhor candidato. Retorna (cand, score)."""
    if not books:
        return None, 0.0
    alvo_pt = norm(titulo_pt)
    alvo_en = norm(titulo_en)
    alvos_alt = [norm(a) for a in (titulos_alt or [])]
    aut_alvo = norm(autor_pt)
    melhor, score = None, -1.0

    for b in books:
        tit = norm(b.get("title"))
        aut = norm(b.get("author"))
        s = 0.0

        # P1 (2026-11-08): GATE DURO DE TITULO, antes de qualquer pontuacao.
        # Sem ele, "Sangue Bom" casava com "Sangue Sabio" (= A Wise Blood)
        # por 1 token em comum — e o pipeline baixava a OUTRA obra.
        if not titulo_confere(b.get("title") or "",
                              [titulo_pt, titulo_en] + list(titulos_alt or [])):
            continue

        # cobertura do titulo (max entre PT / EN / aliases)
        cov = 0.0
        for alvo in [alvo_pt, alvo_en] + alvos_alt:
            if not alvo:
                continue
            tp = toks(alvo)
            if not tp:
                continue
            hit = sum(1 for t in tp if t in tit)
            c = hit / len(tp)
            cov = max(cov, c)
        s += cov * 1.60

        # titulo literal contido
        for alvo in [alvo_pt, alvo_en] + alvos_alt:
            if alvo and len(alvo) > 6 and alvo in tit:
                s += 0.30
                break

        # autor
        if aut_alvo and aut:
            at = toks(aut_alvo)
            ah = sum(1 for t in at if t in aut)
            s += (ah / len(at)) * 0.35 if at else 0.0

        # formato e idioma
        ext = (b.get("extension") or "").lower()
        if ext in ("epub", "mobi", "azw3"):
            s += 0.12
        elif ext == "pdf":
            s += 0.04
        lang = (b.get("lang") or "").lower()
        if lang.startswith("portuguese"):
            s += 0.22
        elif lang.startswith("spanish"):
            s += 0.06
        elif lang.startswith("english"):
            s += 0.10

        # penalidade: colecao / box / obras completas (multi-volume)
        t_raw = (b.get("title") or "").lower()
        if any(k in t_raw for k in ("box", "coleção", "colecao", "grandes obras",
                                    "compendio", "boxset", "colección")):
            s -= 0.55

        if s > score:
            melhor, score = b, s
    return melhor, round(score, 2)


# ---------------------------------------------------------------------------
# conversao + catalogacao (mesma politica do pipeline principal)
# ---------------------------------------------------------------------------
def conteudo_confere(texto, titulo):
    t = norm(titulo)
    corpo = norm(texto)
    if t and t in corpo:
        return True
    partes = [p for p in t.split() if len(p) > 3 and p not in ("de", "da", "do", "e")]
    if partes and all(p in corpo for p in partes[:3]):
        return True
    return False


def converte(ebook, titulo, autor, tags, ano, subpasta):
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
        if not conteudo_confere(txt, titulo):
            return None, "conteudo-divergente: titulo '%s' nao aparece no texto" % titulo
        # P2 (2026-11-08): GATE DE IDIOMA no TEXTO. A rampa e' PT-BR; um
        # exemplar em espanhol/ingles NAO substitui o PT-BR. Foi exatamente
        # o que aconteceu com "Alves & C.a": a 2a via trouxe a edicao
        # ESPANOLA e ela foi gravada em .../portugues/.
        if _diag_idioma is not None:
            diag = _diag_idioma(txt)
            if not diag.startswith("pt"):
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
            continue

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
                if books:
                    break
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
                             "motivo": "download falhou: %s" % info}
                salvar_estado(estado)
                print("[DOWNLOAD-FALHOU] %s: %s" % (it["titulo"], info))
                log("download_falhou_biblio", titulo=it["titulo"], erro=info)
                falhas += 1
                continue
        if fonte == "zlib":
            cota = max(0, cota - 1)

        # ---- conversao ----
        destino, msg = converte(ebook, it["titulo"], it["autor"], it["tags"],
                                it["ano"], it["subpasta"])
        if not destino:
            estado[s] = {"status": "falhou", "tentado": time.strftime("%Y-%m-%d"),
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
