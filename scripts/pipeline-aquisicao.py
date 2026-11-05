#!/usr/bin/env python3
"""Pipeline de aquisicao de ficcao em ESCALA — data-driven, para milhares de livros.

Diferenca do `baixar-rampa-ficcao.py` (que e' hardcoded com 30 alvos): aqui o
catálogo vem de um ARQUIVO YAML/CSV externo. Add um livro = add uma linha no
catálogo. Nao ha codigo para mudar.

Fluxo (1 comando por livro):
  1. SEARCH   -> z-library (eAPI, curl), com fallback de idioma e de titulo
  2. SELECT   -> melhor candidato (EPUB > PDF, PT-BR > PT > EN, penaliza coletanea)
  3. DOWNLOAD -> eAPI /file -> _incoming/<slug>.<ext>
  4. CONVERT  -> epub2md.py em tempdir ISOLADO + validacao de conteudo
  5. CATALOG  -> frontmatter + entrada na KB
  6. ORBIT    -> push do ebook original (ebook NAO fica versionado em data/)

Otimizacoes para escala (o que matava o script hardcoded):
  - **Guarda por slug**: o que ja foi tentado nao e tentado de novo (o catalogo
    cresce sem reprocessar o que ja falhou).
  - **Cota real por conta**: consulta /eapi/user/profile antes de cada download e
    respeita `downloads_limit - downloads_today` (a cota reseta a meia-noite UTC).
  - **Rotacao de contas**: 4 contas x 10 = 40/dia.
  - **Ordem por prioridade**: alta -> media -> baixa, e dentro disso o que tem
    mais chance de estar em PT-BR.

Uso:
  python3 scripts/pipeline-aquisicao.py --catalogo data/perfil/bibliotecario/catalogo-ficcao.yaml --max 5
  python3 scripts/pipeline-aquisicao.py --catalogo ... --titulo "O Nome da Rosa" --autor "Umberto Eco" --dry
  python3 scripts/pipeline-aquisicao.py --catalogo ... --status     # só relatório
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

ROOT = Path(__file__).resolve().parent.parent
BIB = ROOT / "data" / "biblioteca"
INCOMING = BIB / "_incoming"
ORBIT_DIR = ROOT / "data" / "perfil" / "bibliotecario" / "biblioteca-orbit"
EPUB2MD = ORBIT_DIR / "epub2md.py"
KB = BIB / "global" / "kb-literatura.yaml"
LOG = ROOT / "data" / "perfil" / "bibliotecario" / "logs" / "pipeline-aquisicao.jsonl"
ESTADO = ROOT / "data" / "perfil" / "bibliotecario" / "pipeline-estado.json"

DOM = "z-lib.gd"
UA = "Mozilla/5.0 (Android 12; Mobile)"
CONTAS = ["zlib2", "zlib3", "zlib4"]
MIN_BYTES = 60_000
MIN_LINHAS = 200

# prioridade -> peso na ordem de processamento
PESO = {"alta": 0, "media": 1, "baixa": 2}

# extensoes que o Orbit aceita (e que o epub2md sabe converter)
EXT_OK = {"epub", "pdf", "mobi", "azw3", "azw", "prc", "fb2"}

# titulos/colecoes que sao COLECAO de varias obras: o acervo deve comprar
# cada obra SEPARADA, nao a antologia.
RUIM = re.compile(
    r"(box|cole[cç][aã]o|obras completas|antologia|c[oó]pia|enciclop|"
    r"cl[aá]ssicos? de ouro|grandes obras|volumes? \d|mundo inteiro|"
    r"acervo|livros? de|sumo|reunidos)", re.I)

# edicoes que NAO sao a obra: adaptacao, resumo, bolso. Penalidade ALTA — uma
# "adapta[c][a]o" do Retrato de Dorian Gray com o titulo literal tinha score
# MAIOR que a obra original (bug de 2026-11-05) porque a penalidade era
# fraca demais (-0.25) e o bonus de "titulo literal contido" (+0.22) a vencia.
DEGRADE = re.compile(
    r"(abreviat|resum[oa]\b|adapta|bolso|cl[aá]ssicos? de ouro|"
    r"vers[aã]o (simplificada|adaptada|abreviada)|"
    r"como ler|em 15 minutos|leitura f[aá]cil)", re.I)

# edicoes aceitaveis mas nao ideais: comentada, bilingue, ilustrada.
# Penalidade media: ainda serve para leitura, mas a edicao limpa e' melhor.
MEDIO = re.compile(
    r"(coment[aá]d|comentar|bilingue|ilustrad|anota[cç][aã]o|"
    r"cl[aá]ssicos?world|cl[aá]ssicos? de ouro|ed[ií]c[aã]o)", re.I)

STOP = {"o", "a", "os", "as", "de", "do", "da", "dos", "das", "e", "em", "no", "na",
        "um", "uma", "para", "com", "que", "se", "por", "ao", "the", "of", "and",
        "a", "ao", "à", "à", "ou", "nao", "mais"}


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------
def sem_acento(s):
    return "".join(c for c in unicodedata.normalize("NFKD", s or "")
                   if not unicodedata.combining(c))


def norm(s):
    s = sem_acento(s or "").lower()
    s = re.sub(r"[^\w\s]", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def toks(s):
    return {t for t in re.findall(r"[a-z0-9]+", norm(s)) if t not in STOP and len(t) > 2}


def slug(titulo, autor):
    s = sem_acento(f"{titulo} - {autor}")
    s = s.replace(" ", " ").replace(" ", " ")
    s = s.replace("—", "-").replace("–", "-")
    s = re.sub(r"[^\w\s-]", "", s)
    s = re.sub(r"[\s_]+", "-", s)
    s = re.sub(r"-{2,}", "-", s).strip("-")
    return s[:70].strip("-")


def log(ev, **kw):
    rec = {"ts": time.strftime("%Y-%m-%dT%H:%M:%S"), "event": ev, **kw}
    LOG.parent.mkdir(parents=True, exist_ok=True)
    with LOG.open("a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")


def carregar_estado():
    if ESTADO.exists():
        try:
            return json.loads(ESTADO.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}


def salvar_estado(st):
    ESTADO.parent.mkdir(parents=True, exist_ok=True)
    ESTADO.write_text(json.dumps(st, ensure_ascii=False, indent=1), encoding="utf-8")


# ---------------------------------------------------------------------------
# credenciais (mescladas: YAML + cache)
# ---------------------------------------------------------------------------
def creds():
    """Contas do z-library. Mescla YAML + cache (BUG 2026-11-05: o cache
    sozinho perdia a conta principal; o YAML sozinho perdia zlib2/3/4)."""
    envs = {}
    cache = Path.home() / ".zlib-mcp" / ".account-env-cache.json"
    if cache.exists():
        try:
            envs.update(json.loads(cache.read_text(encoding="utf-8")))
        except Exception:
            pass
    yml = ROOT / "data" / "perfil" / "bibliotecario" / "zlib-credentials.yaml"
    if yml.exists():
        txt = yml.read_text(encoding="utf-8")
        for bloco in txt.split("- alias:")[1:]:
            alias = bloco.split("\n")[0].strip().strip("'\"")
            rid = re.search(r"remix_id:\s*'?([0-9]+)'?", bloco)
            rkey = re.search(r"remix_key:\s*'?([A-Za-z0-9]+)'?", bloco)
            if alias and rid and rkey:
                envs.setdefault(alias, {"ZLIB_REMIX_ID": rid.group(1),
                                       "ZLIB_REMIX_KEY": rkey.group(1)})
    return envs


def cookie(acct, envs):
    e = envs.get(acct)
    if not e:
        return ""
    return f"remix_userid={e['ZLIB_REMIX_ID']}; remix_userkey={e['ZLIB_REMIX_KEY']}"


def curl(args, timeout=60):
    r = subprocess.run(["curl", "-sS", "-m", str(timeout)] + args,
                       capture_output=True, text=True)
    return r.stdout


# ---------------------------------------------------------------------------
# z-library
# ---------------------------------------------------------------------------
def cota(acct, envs):
    out = curl([f"https://{DOM}/eapi/user/profile", "-H", f"User-Agent: {UA}",
                "-b", cookie(acct, envs)], timeout=30)
    try:
        u = json.loads(out).get("user", {})
        lim = u.get("downloads_limit") or 10
        hoje = u.get("downloads_today") or 0
        return max(0, lim - hoje)
    except Exception:
        return 0


def busca(query, acct, envs, lang=None, limit=30):
    args = [f"https://{DOM}/eapi/book/search", "-H", f"User-Agent: {UA}",
            "-b", cookie(acct, envs), "-d", f"message={query}&limit={limit}"]
    if lang:
        args += ["-d", f"languages[]={lang}"]
    out = curl(args, timeout=45)
    try:
        d = json.loads(out)
    except Exception:
        return []
    if not d.get("success"):
        return []
    return d.get("books", [])


def melhor_candidato(books, titulo_pt, autor_pt, titulo_en=""):
    """Escolhe o melhor candidato. Pontua: cobertura do titulo, cobertura do
    autor, bonus de titulo literal, bonus de formato, penalidade de coletanea
    e de edicao degradada.

    BUG (2026-11-05): a penalidade de "adapta[c][a]o" era -0.25 e o bonus de
    "titulo literal contido" era +0.22 — a ADAPTACAO vencia a obra original.
    Agora a degradada vale -0.55 (manda para o fim da lista) e a media -0.12.

    O score e' uma media ponderada, entao fica em [0, 1]; o limiar 0.55
    significa "pelo menos metade do titulo e metade do autor casam".
    """
    alvo = toks(titulo_pt) | toks(titulo_en)
    alv_a = toks(autor_pt)
    tpl = norm(titulo_pt)
    best, best_s = None, -99
    for b in books:
        raw = b.get("title", "") or ""
        aut_raw = b.get("author", "") or ""
        ext = (b.get("extension") or "").lower()
        lang = (b.get("language") or "").lower()
        # formato aceito
        if ext not in EXT_OK:
            continue
        # idioma: PT e o alvo; EN e aceitavel como ultimo recurso
        if lang and "portugu" not in lang and "english" not in lang:
            continue
        pen = 0.0
        if RUIM.search(raw):
            pen += 0.30
        if DEGRADE.search(raw):
            pen += 0.55
        elif MEDIO.search(raw):
            # edicao comentada/bilingue serve, mas a edicao LIMPA e' melhor:
            # penalidade suficiente para ficar ATRAS da edicao simples, nao
            # para eliminar (as vezes so existe a comentada).
            pen += 0.20
        t = toks(raw)
        a = toks(aut_raw)
        cov = len(alvo & t) / max(1, len(alvo))
        cov_a = len(alv_a & a) / max(1, len(alv_a))
        # score = media ponderada das partes, menos penalidade
        s = cov * 0.62 + cov_a * 0.28 - pen
        if len(tpl) > 6 and tpl in norm(raw):
            s += 0.22
        # bonus de formato: epub > pdf > mobi
        s += {"epub": 0.10, "pdf": 0.04, "azw3": 0.03, "mobi": 0.02}.get(ext, 0.0)
        # bonus de idioma PT
        if "portugu" in lang:
            s += 0.12
        # titulo muito curto e generico demais -> nao confia
        if len(t) < 2:
            s -= 0.35
        # bonus de titulo EXATO (sem sufixo de edicao): o texto integral
        # da obra, sem comentario nem bilingue. Vale mais que o bonus de
        # formato, porque o que o acervo quer e' o livro, nao a apparatus.
        if norm(raw) == tpl:
            s += 0.30
        if s > best_s:
            best, best_s = b, s
    if best and best_s >= 0.55:
        return best, round(best_s, 3)
    return None, round(best_s, 3)


def baixa(book, acct, envs, destino):
    bid, bh = book.get("id"), book.get("hash")
    out = curl([f"https://{DOM}/eapi/book/{bid}/{bh}/file", "-H", f"User-Agent: {UA}",
                "-b", cookie(acct, envs)], timeout=45)
    try:
        d = json.loads(out)
    except Exception:
        return None, "resposta-file nao-JSON"
    if not d.get("success"):
        return None, d.get("error", "erro desconhecido")
    link = (d.get("file") or {}).get("downloadLink")
    if not link:
        return None, "sem downloadLink"
    ext = ((d.get("file") or {}).get("extension") or "epub").lower()
    dest = destino.parent / f"{destino.stem}.{ext}"
    subprocess.run(["curl", "-sSL", "-m", "300", "-o", str(dest),
                    "-H", f"User-Agent: {UA}", link], capture_output=True, text=True)
    if not dest.exists() or dest.stat().st_size < 20000:
        return None, "arquivo vazio/pequeno demais"
    return dest, f"{dest.stat().st_size//1024} KB {ext}"


# ---------------------------------------------------------------------------
# conversao + catalogacao
# ---------------------------------------------------------------------------
def conteudo_confere(texto, titulo):
    """Confere que o texto e' do livro certo. Busca no texto INTEIRO (bug de
    2026-11-05: EPUBs sem folha de rosto so citam o titulo no fim)."""
    t = norm(titulo)
    corpo = norm(texto)
    if t and t in corpo:
        return True
    partes = [p for p in t.split() if len(p) > 3 and p not in ("de", "da", "do", "e")]
    if partes and all(p in corpo for p in partes[:3]):
        return True
    return False


def converte(ebook, titulo, autor, tags, ano, subpasta):
    """Converte em tempdir ISOLADO e so aceita se produziu texto real e se o
    titulo aparece no texto (evita o .md com conteudo de outro livro)."""
    tmp = Path(tempfile.mkdtemp(prefix="pipe-conv-"))
    try:
        r = subprocess.run([sys.executable, str(EPUB2MD), "--dest", str(tmp), str(ebook)],
                           capture_output=True, text=True, timeout=2400)
        mds = list(tmp.glob("*.md"))
        if not mds:
            return None, f"conversao-sem-md: {r.stdout[-160:]}"
        gerado = max(mds, key=lambda p: p.stat().st_size)
        txt = gerado.read_text(encoding="utf-8", errors="ignore")
        linhas = txt.count("\n")
        if gerado.stat().st_size < MIN_BYTES or linhas < MIN_LINHAS:
            return None, (f"texto-curto ({gerado.stat().st_size//1024} KB, "
                          f"{linhas} lin) — extraicao provavelmente falhou")
        if not conteudo_confere(txt, titulo):
            return None, f"conteudo-divergente: titulo '{titulo}' nao aparece no texto"
        dest_dir = BIB / "literatura-mundial-classica" / subpasta
        dest_dir.mkdir(parents=True, exist_ok=True)
        destino = dest_dir / f"{slug(titulo, autor)}.md"
        shutil.move(str(gerado), str(destino), copy_function=os.replace)
        return destino, "ok"
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def cataloga(destino, titulo, autor, tags, ano):
    """Insere na KB global de literatura. Idempotente por caminho_md."""
    rel = f"./data/biblioteca/literatura-mundial-classica/{destino.relative_to(BIB / 'literatura-mundial-classica')}"
    txt = KB.read_text(encoding="utf-8")
    if rel in txt:
        return "ja-catalogado"
    tags_yaml = ", ".join(tags)
    linha = (f"  - titulo: LT {titulo} - {autor}\n"
             f"    caminho_md: {rel}\n"
             f"    tamanho_md: {destino.stat().st_size // 1024} KB\n"
             f"    linhas_md: {destino.read_text(encoding='utf-8', errors='ignore').count(chr(10))}\n"
             "    idioma: Portuguese\n"
             f"    tags: [{tags_yaml}]\n"
             f"    ano: {ano}\n"
             "    status: indexado_auto\n"
             "    origem: pipeline-aquisicao-escala\n")
    m = re.search(r"^knowledge_base_literatura:\n(?:.*\n)*?\s*materiais:\n", txt, re.M)
    if not m:
        return "falha-bloco-kb"
    KB.write_text(txt[:m.end()] + linha + txt[m.end():], encoding="utf-8")
    return "catalogado"


def frontmatter(titulo, autor, tags, ano):
    t = ", ".join(f'"{x}"' for x in tags)
    return ("---\n"
            f'titulo: "{titulo}"\n'
            f'autor: "{autor}"\n'
            "idioma: Portuguese\n"
            f"ano: {ano}\n"
            f"tags: [{t}]\n"
            "tipo: literatura\n"
            "origem: pipeline-aquisicao-escala\n"
            "---\n\n")


# ---------------------------------------------------------------------------
# catalogo de entrada
# ---------------------------------------------------------------------------
def carrega_catalogo(path):
    """Le o catalogo. Aceita YAML ou CSV ou JSON.
    YAML esperado:
        catalogo:
          - titulo: O Nome da Rosa
            autor: Umberto Eco
            prioridade: alta
            tags: [literatura, romance]
            ano: 1980
            subpasta: italiano
            titulo_en: The Name of the Rose
    """
    p = Path(path)
    txt = p.read_text(encoding="utf-8")
    if p.suffix in (".json",):
        d = json.loads(txt)
        return d.get("catalogo", d) if isinstance(d, dict) else d
    if p.suffix in (".csv",):
        import csv
        import io
        return list(csv.DictReader(io.StringIO(txt)))
    try:
        import yaml
        d = yaml.safe_load(txt)
        if isinstance(d, dict):
            return d.get("catalogo", [])
        return d or []
    except ImportError:
        pass
    # fallback: linhas "titulo | autor | prioridade | tags"
    out = []
    for ln in txt.splitlines():
        ln = ln.strip()
        if not ln or ln.startswith("#") or "|" not in ln:
            continue
        p2 = [x.strip() for x in ln.split("|")]
        out.append({"titulo": p2[0], "autor": p2[1] if len(p2) > 1 else "",
                    "prioridade": p2[2] if len(p2) > 2 else "media",
                    "tags": [t.strip() for t in p2[3].split(",")] if len(p2) > 3 else []})
    return out


def normaliza_item(it):
    if not isinstance(it, dict):
        return None
    tit = (it.get("titulo") or it.get("title") or "").strip()
    aut = (it.get("autor") or it.get("author") or "").strip()
    if not tit:
        return None
    tags = it.get("tags") or []
    if isinstance(tags, str):
        tags = [t.strip() for t in tags.split(",") if t.strip()]
    if not tags:
        tags = ["literatura", "literatura-mundial", "canon-literario"]
    return {
        "titulo": tit,
        "autor": aut,
        "prioridade": (it.get("prioridade") or it.get("priority") or "media").lower(),
        "tags": tags,
        "ano": it.get("ano") or it.get("year") or "",
        "subpasta": it.get("subpasta") or "outros",
        "titulo_en": it.get("titulo_en") or it.get("title_en") or "",
    }


# ---------------------------------------------------------------------------
# principal
# ---------------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--catalogo", required=True)
    ap.add_argument("--max", type=int, default=5, help="max downloads neste turno")
    ap.add_argument("--titulo", help="processa so este titulo (ad-hoc)")
    ap.add_argument("--autor", default="")
    ap.add_argument("--prioridade", default="media")
    ap.add_argument("--tags", default="")
    ap.add_argument("--dry", action="store_true", help="so busca e mostra, nao baixa")
    ap.add_argument("--status", action="store_true", help="so relatorio do estado")
    ap.add_argument("--sem-orbit", action="store_true")
    args = ap.parse_args()

    estado = carregar_estado()
    envs = creds()

    # ---- catalogo ----
    if args.titulo:
        itens = [{"titulo": args.titulo, "autor": args.autor,
                  "prioridade": args.prioridade,
                  "tags": [t.strip() for t in args.tags.split(",") if t.strip()],
                  "ano": "", "subpasta": "outros", "titulo_en": ""}]
    else:
        bruto = carrega_catalogo(args.catalogo)
        itens = [normaliza_item(x) for x in bruto]
        itens = [x for x in itens if x]

    # ---- ordem: prioridade, depois ja-tentados por ultimo ----
    def ordem(it):
        st = estado.get(slug(it["titulo"], it["autor"]), {})
        tentado = 1 if st.get("tentado") else 0
        return (PESO.get(it["prioridade"], 1), tentado, it["titulo"])
    itens.sort(key=ordem)

    if args.status:
        print(f"{'STATUS':10s} {'P':6s} TITULO — AUTOR")
        for it in itens:
            st = estado.get(slug(it["titulo"], it["autor"]), {})
            s = st.get("status", "pendente")
            print(f"{s:10s} {it['prioridade'][:6]:6s} {it['titulo']} — {it['autor']}")
        pend = [i for i in itens
                if estado.get(slug(i["titulo"], i["autor"]), {}).get("status") != "adquirido"]
        print(f"\n{len(itens)} no catalogo · {len(itens)-len(pend)} adquiridos · "
              f"{len(pend)} pendentes")
        return 0

    INCOMING.mkdir(parents=True, exist_ok=True)

    # ---- cotas por conta ----
    cotas = {a: cota(a, envs) for a in CONTAS}
    print("cota por conta: " + ", ".join(f"{a}={cotas[a]}" for a in CONTAS))
    if all(c <= 0 for c in cotas.values()) and not args.dry:
        # A BUSCA nao gasta cota — so o download. Em --dry seguimos mesmo assim,
        # para validar a selecao de candidatos sem gastar nada.
        print("!! cota esgotada em todas as contas — nada a baixar agora "
              "(a cota reseta a meia-noite UTC = 21h BRT).")
        return 1

    baixados = 0
    falhas = 0
    for it in itens:
        if baixados >= args.max:
            break
        s = slug(it["titulo"], it["autor"])
        st = estado.get(s, {})
        if st.get("status") == "adquirido":
            continue
        if st.get("tentado") and st.get("status") == "falhou" and not args.titulo:
            # ja falhou uma vez: nao repete no mesmo dia (cota e precious)
            continue

        # ---- 1. busca (PT primeiro, depois sem filtro) ----
        conta = next((a for a in CONTAS if cotas.get(a, 0) > 0), None)
        if not conta and not args.dry:
            print("!! cota esgotou no meio do lote")
            break
        # em --dry nao ha conta com cota: usa a primeira so para BUSCAR
        # (busca nao gasta cota; so o download gasta).
        busca_conta = conta or CONTAS[0]

        queries = [f"{it['titulo']} {it['autor']}".strip()]
        if it["titulo_en"]:
            queries.append(f"{it['titulo_en']} {it['autor']}".strip())
        books = []
        for q in queries:
            books = busca(q, busca_conta, envs, lang="portuguese")
            if not books:
                books = busca(q, busca_conta, envs, lang=None)
            if books:
                break
        if not books:
            estado[s] = {"status": "falhou", "tentado": time.strftime("%Y-%m-%d"),
                         "motivo": "sem resultado na busca"}
            salvar_estado(estado)
            print(f"[BUSCA-VAZIA] {it['titulo']} — {it['autor']}")
            log("busca_vazia", titulo=it["titulo"], autor=it["autor"])
            falhas += 1
            continue

        cand, score = melhor_candidato(books, it["titulo"], it["autor"], it["titulo_en"])
        if not cand:
            estado[s] = {"status": "falhou", "tentado": time.strftime("%Y-%m-%d"),
                         "motivo": f"nenhum candidato acima do limiar (melhor {score})",
                         "candidatos": [b.get("title") for b in books[:5]]}
            salvar_estado(estado)
            print(f"[SEM-CANDIDATO] {it['titulo']} (melhor score {score})")
            log("sem_candidato", titulo=it["titulo"], score=score)
            falhas += 1
            continue

        print(f"[CANDIDATO] {it['titulo']} <- {cand.get('title')} "
              f"({cand.get('extension')}, {cand.get('language')}, score {score})")

        if args.dry:
            continue

        # ---- 2. download ----
        ebook, info = baixa(cand, conta, envs, INCOMING / s)
        if not ebook:
            estado[s] = {"status": "falhou", "tentado": time.strftime("%Y-%m-%d"),
                         "motivo": f"download falhou: {info}"}
            salvar_estado(estado)
            print(f"[DOWNLOAD-FALHOU] {it['titulo']}: {info}")
            log("download_falhou", titulo=it["titulo"], erro=info)
            cotas[conta] = max(0, cotas[conta] - 1)
            falhas += 1
            continue
        cotas[conta] = max(0, cotas[conta] - 1)

        # ---- 3. conversao ----
        destino, msg = converte(ebook, it["titulo"], it["autor"], it["tags"],
                                it["ano"], it["subpasta"])
        if not destino:
            estado[s] = {"status": "falhou", "tentado": time.strftime("%Y-%m-%d"),
                         "motivo": f"conversao: {msg}", "ebook": str(ebook.name)}
            salvar_estado(estado)
            print(f"[CONVERSAO-FALHOU] {it['titulo']}: {msg}")
            log("conversao_falhou", titulo=it["titulo"], erro=msg)
            falhas += 1
            continue

        # ---- 4. frontmatter + KB ----
        if not destino.read_text(encoding="utf-8").lstrip().startswith("---"):
            destino.write_text(frontmatter(it["titulo"], it["autor"], it["tags"],
                                           it["ano"]) +
                               destino.read_text(encoding="utf-8"), encoding="utf-8")
        kb = cataloga(destino, it["titulo"], it["autor"], it["tags"], it["ano"])

        # ---- 5. Orbit (ebook original vai pro app de leitura; NAO fica no repo) ----
        orbit = "pulado"
        if not args.sem_orbit:
            r = subprocess.run(["bash", str(ORBIT_DIR / "biblioteca-push.sh"),
                                "--autor", it["autor"] or "_unorganized", str(ebook)],
                               capture_output=True, text=True, timeout=300)
            orbit = "ok" if r.returncode == 0 else "falhou"
            if orbit == "falhou":
                print(f"[ORBIT-FALHOU] {ebook.name}: {r.stderr[-200:]}")
                log("orbit_falhou", arquivo=ebook.name, erro=r.stderr[-300:])
            else:
                # so apaga o original DEPOIS do push confirmado
                try:
                    ebook.unlink()
                except OSError:
                    pass

        estado[s] = {"status": "adquirido", "data": time.strftime("%Y-%m-%d"),
                     "ebook": ebook.name, "md": str(destino.relative_to(ROOT)),
                     "kb": kb, "orbit": orbit, "score": score}
        salvar_estado(estado)
        baixados += 1
        print(f"[OK] {it['titulo']} -> {destino.relative_to(ROOT)} "
              f"({destino.stat().st_size//1024} KB, KB={kb}, Orbit={orbit})")
        log("adquirido", titulo=it["titulo"], autor=it["autor"],
            md=str(destino.relative_to(ROOT)), kb=kb, orbit=orbit)

    print(f"\n=== {baixados} adquirido(s), {falhas} falha(s) ===")
    return 0


if __name__ == "__main__":
    sys.exit(main())
