#!/usr/bin/env python3
"""md2epub.py — converte um .md (extraido de PDF, com sujeira de OCR) em EPUB.

POR QUE EXISTE (2026-11-25, pedido do William):
  "se os arquivos existem e estao localmente, sobe no bookorbit; se nao existe
  baixe e sobe." Dois volumes do acervo existem so como .md e o William quer
  ler no celular (BookOrbit). O .md desses PDFs tem lixo de extracao:
    - texto vertical letra-por-letra (capa girada)
    - `(cid:138)` (glifo sem unicode)
    - cabecalho corrido repetido a cada pagina
    - numero de pagina solto
    - hifenizacao de fim de linha ("compreendê-la" -> "compreen-\nda-la")
    - espacos duplos de justificacao

O QUE FAZ
  1. Limpa (frontmatter, cid, vertical, cabecalho, numero de pagina, hifen).
  2. Junta linhas em paragrafos (blocos separados por linha em branco).
  3. Divide em capitulos por LINHAS fixas ou por TITULOS de sumario.
  4. Grava EPUB 3 com sumario.

USO
  python3 scripts/md2epub.py SPEC.json

SPEC.json:
{
  "md": "caminho.md",
  "epub": "saida.epub",
  "titulo": "...", "autor": "...", "idioma": "pt",
  "ignorar_ate_linha": 45,
  "cabecalhos_corridos": ["Manual bíblico das questões difíceis"],
  "capitulos_por_linha": [{"linha": 287, "titulo": "...", "autor": "..."}],
  "capitulos_por_titulo": {"fonte": "sumario", "min_palavras": 3}
}
"""
import html
import json
import re
import sys
import unicodedata
from pathlib import Path

from ebooklib import epub

# ---------------------------------------------------------------- limpeza


def sem_acento(s):
    return "".join(c for c in unicodedata.normalize("NFD", s)
                   if unicodedata.category(c) != "Mn")


def norm(s):
    """Chave de casamento: minuscula, sem acento, so letras/numeros."""
    s = sem_acento(s.lower())
    s = re.sub(r"[^a-z0-9 ]+", " ", s)
    return re.sub(r"\s+", " ", s).strip()


RE_CID = re.compile(r"\(cid:\d+\)")
RE_PAGINA = re.compile(r"^\s*\d{1,3}\s*$")
RE_DOTS = re.compile(r"\.{4,}")


def limpar_linhas(linhas, cabecalhos=()):
    """Remove lixo linha a linha. Devolve lista de linhas uteis.

    PRESERVA OS INDICES (2026-11-25): linha removida vira "" em vez de sair
    da lista. O spec do md2epub usa numero de linha do arquivo ORIGINAL; se a
    limpeza encurtasse a lista, todo capitulo comecaria deslocado (bug
    medido: o capitulo 7 comecava no meio do 6).
    """
    out = []
    cab = [norm(c) for c in cabecalhos]
    for ln in linhas:
        s = ln.rstrip("\n")
        s = RE_CID.sub("", s)
        t = s.strip()
        if not t:
            out.append("")
            continue
        # texto vertical (capa girada): linha de 1 caractere
        if len(t) <= 1:
            out.append("")
            continue
        if RE_PAGINA.match(t):
            out.append("")
            continue
        nt = norm(t)
        if any(nt.startswith(c) for c in cab if c):
            out.append("")
            continue
        out.append(re.sub(r"[ \t]{2,}", " ", s).strip())
    return out


def juntar_paragrafos(linhas):
    """Blocos separados por linha em branco -> paragrafos (hifen resolvido)."""
    blocos, atual = [], []
    for ln in linhas:
        if ln == "":
            if atual:
                blocos.append(atual)
                atual = []
        else:
            atual.append(ln)
    if atual:
        blocos.append(atual)

    paragrafos = []
    for b in blocos:
        txt = ""
        for ln in b:
            if not txt:
                txt = ln
                continue
            if txt.endswith("-") and len(txt) > 1 and txt[-2].isalpha():
                # hifenizacao de fim de linha
                txt = txt[:-1] + ln
            else:
                txt = txt + " " + ln
        txt = re.sub(r"\s+", " ", txt).strip()
        if txt:
            paragrafos.append(txt)
    return paragrafos


def paragrafos_html(paragrafos):
    partes = []
    for p in paragrafos:
        if p.upper() == p and len(p) < 60 and len(p.split()) <= 8:
            partes.append(f"<h2>{html.escape(p)}</h2>")
        else:
            partes.append(f"<p>{html.escape(p)}</p>")
    return "\n".join(partes)


# ------------------------------------------------------- capitulos


def _drop_titulo(corpo, titulo):
    """Tira do inicio do corpo as linhas que repetem o titulo (vem do <h1>).

    O titulo do sumario quase nunca e' igual ao do corpo (small-caps, quebra de
    linha, hifen), entao compara-se o SQUASH (so letras minusculas sem acento)
    do comeco do corpo contra o squash do titulo. Tambem tenta o titulo sem o
    prefixo de secao ("Perguntas e Respostas — X" -> "X").
    """
    cands = [titulo]
    if "—" in titulo:
        cands.append(titulo.split("—")[-1].strip())
    if ":" in titulo:
        cands.append(titulo.split(":", 1)[1].strip())
    melhor = 0
    for cand in cands:
        alvo = norm(cand).replace(" ", "")
        if len(alvo) < 8:
            continue
        acc, i = "", 0
        limite = max(12, int(len(alvo) * 0.75))
        while i < len(corpo) and i < 25:
            t = norm(corpo[i]).replace(" ", "")
            i += 1
            if not t:
                continue
            acc += t
            if len(acc) >= limite and alvo.startswith(acc):
                melhor = max(melhor, i)
                break
            if len(acc) >= len(alvo):
                if alvo.startswith(acc[:len(alvo)]):
                    melhor = max(melhor, i)
                break
        else:
            if acc and alvo.startswith(acc[:len(alvo)]):
                melhor = max(melhor, i)
    return corpo[melhor:] if melhor else corpo


def _parece_nome(t):
    """'Paul Randolph 1', 'David A. Powlison', 'Heather L . Rice 1'.

    Exige que TODAS as palavras (menos particulas) comecem em maiuscula —
    sem isso "Quais sao suas primeiras associacoes" passava por nome e o
    primeiro paragrafo do capitulo era comido (bug medido 2026-11-25).
    """
    t = t.strip()
    if not t or len(t) > 45:
        return False
    if not re.match(r"^[A-ZÀ-Ý]", t):
        return False
    if re.search(r"[.;!?]$", t):
        return False
    palavras = t.split()
    if not (2 <= len(palavras) <= 6):
        return False
    particulas = {"de", "da", "dos", "das", "e", ".", "-"}
    for w in palavras:
        if w in particulas or w.isdigit():
            continue
        if not re.match(r"^[A-ZÀ-Ý]", w):
            return False
    return True


def _squash(s):
    return norm(s).replace(" ", "")


def _parece_secao(t):
    """'Pratica do Aconselhamento Biblico' — titulo de secao da revista."""
    n = norm(t)
    return n in {"aconselhamento", "pratica do aconselhamento biblico",
                 "bases do aconselhamento biblico", "perguntas e respostas",
                 "a palavra do editor"}


def _pular_cabecalho(corpo, autor, titulo=""):
    """Devolve o corpo sem o cabecalho do PDF.

    O cabecalho do PDF termina na linha do AUTOR. Tudo antes dela que seja
    linha de secao ou pedaco do titulo sai; o resto (epigrafe, por exemplo)
    fica. Depois da linha do autor sai o credito ("1Traducao de ...") e
    qualquer repeticao do titulo.
    """
    alvo_t = _squash(titulo)
    sobrenome = _squash(autor.split()[-1]) if autor.split() else ""
    alvo_a = _squash(autor)

    idx_autor = -1
    for i in range(min(len(corpo), 25)):
        ln = corpo[i].strip()
        if not ln:
            continue
        s = _squash(ln)
        if alvo_a and len(alvo_a) >= 6 and (s.startswith(alvo_a) or alvo_a.startswith(s)):
            idx_autor = i
            break
        if (sobrenome and len(sobrenome) >= 4 and len(ln) < 45
                and sobrenome in s and not s.startswith(alvo_t[:12])):
            idx_autor = i
            break
        if len(ln) > 150:
            break

    if idx_autor < 0:
        # sem autor reconhecivel: corta o titulo repetido do inicio
        i, acc = 0, ""
        while i < len(corpo) and i < 20:
            ln = corpo[i].strip()
            i += 1
            if not ln:
                continue
            if _parece_secao(ln):
                continue
            s = _squash(ln)
            if alvo_t and (alvo_t.startswith(acc + s) or s == alvo_t):
                acc += s
                continue
            i -= 1
            break
        return _limpar_inicio(corpo[i:], titulo)

    # 1. cabeca: mantem so o que nao for secao nem pedaco do titulo
    cabeca, acc = [], ""
    for ln in corpo[:idx_autor]:
        t = ln.strip()
        if not t:
            continue
        if _parece_secao(t):
            continue
        s = _squash(t)
        if alvo_t and (alvo_t.startswith(acc + s) or s == alvo_t):
            acc += s
            continue
        if not acc and len(t) < 45 and _parece_nome(t):
            continue
        cabeca.append(t)
    resto = cabeca + [""] + list(corpo[idx_autor + 1:])
    return _limpar_inicio(resto, titulo)


def _limpar_inicio(corpo, titulo=""):
    """Tira linhas iniciais sem valor: preenchimento, nome, titulo repetido."""
    alvo = _squash(titulo)
    i = 0
    while i < len(corpo) and i < 10:
        ln = corpo[i].strip()
        if not ln:
            i += 1
            continue
        if set(ln) <= set("_ -."):
            i += 1
            continue
        s = _squash(ln)
        if alvo and (s == alvo or (len(s) >= 10 and alvo.startswith(s))):
            i += 1
            continue
        if len(ln) < 45 and _parece_nome(ln):
            i += 1
            continue
        break
    return corpo[i:]


def capitulos_por_linha(linhas, spec):
    marcas = sorted(spec["capitulos_por_linha"], key=lambda c: c["linha"])
    caps = []
    for i, m in enumerate(marcas):
        ini = m["linha"] - 1
        fim = marcas[i + 1]["linha"] - 1 if i + 1 < len(marcas) else len(linhas)
        corpo = [l for l in linhas[ini:fim]]
        while corpo and not corpo[0].strip():
            corpo = corpo[1:]
        titulo, autor = m["titulo"], m.get("autor", "")
        corpo = _pular_cabecalho(corpo, autor, titulo)
        caps.append({"titulo": titulo, "autor": autor, "linhas": corpo})
    return caps


def titulos_do_sumario(linhas):
    """Extrai titulos de um sumario com pontilhado ('Titulo ..... 292').

    BUG (2026-11-25): titulos longos quebram em 2-3 linhas no PDF. A versao
    anterior usava so a linha imediatamente acima e cortava o titulo
    ("O que sao sacramentos e quantos sacramentos existem na Biblia?" virava
    "domingo de manha?"). Agora ACUMULA todas as linhas sem pontilhado ate
    achar a linha com pontilhado + numero de pagina.
    """
    titulos, pend = [], []
    for ln in linhas:
        t = ln.strip()
        if not t:
            continue
        if not RE_DOTS.search(t):
            # linha sem pontilhado: candidata a comeco de titulo (ou lixo)
            if len(t) > 3 and not t.isdigit():
                pend.append(t)
                if len(pend) > 4:
                    pend = pend[-4:]
            continue
        esq = RE_DOTS.split(t)[0].strip()
        partes = pend + ([esq] if esq else [])
        pend = []
        tit = re.sub(r"\s+", " ", " ".join(partes)).strip(" .-–—")
        tit = re.sub(r"\s+(\d{1,4})$", "", tit).strip()
        if len(tit.split()) >= 2:
            titulos.append(tit)
    vistos, out = set(), []
    for t in titulos:
        k = norm(t)
        if k and k not in vistos:
            vistos.add(k)
            out.append(t)
    return out


def _drop_fragmentos(corpo, titulo):
    """Tira linhas iniciais que sao pedaco do titulo (quebra de linha do PDF)."""
    alvo = _squash(titulo)
    if not alvo:
        return corpo
    i, acc = 0, ""
    while i < len(corpo) and i < 8:
        ln = corpo[i].strip()
        if not ln:
            i += 1
            continue
        s = _squash(ln)
        if not s:
            i += 1
            continue
        if s in alvo or (acc + s) in alvo:
            acc += s
            i += 1
            continue
        break
    return corpo[i:]


def capitulos_por_titulo(linhas, spec, linhas_orig=None):
    """Casa os titulos do sumario com o corpo (squash global + mapa de linha)."""
    cfg = spec.get("capitulos_por_titulo", {})
    ini_toc = cfg.get("linha_fim_sumario", 0)
    fonte_toc = linhas_orig if linhas_orig is not None else linhas
    titulos = titulos_do_sumario(fonte_toc[:ini_toc or len(fonte_toc)])
    # corpo: depois do sumario
    corpo_ini = ini_toc
    mapa, buf = [], []
    for i in range(corpo_ini, len(linhas)):
        for ch in norm(linhas[i]):
            if ch == " ":
                continue
            buf.append(ch)
            mapa.append(i)
    squash = "".join(buf)

    achados = []
    pos = 0
    for t in titulos:
        chave = norm(t).replace(" ", "")
        if len(chave) < 12:
            continue
        k = squash.find(chave, pos)
        if k < 0:
            k = squash.find(chave)
        if k < 0:
            continue
        linha = mapa[k]
        achados.append((linha, t))
        pos = k + len(chave)
    achados.sort()

    caps = []
    for i, (linha, t) in enumerate(achados):
        fim = achados[i + 1][0] if i + 1 < len(achados) else len(linhas)
        corpo = _drop_fragmentos(linhas[linha + 1:fim], t)
        caps.append({"titulo": t, "autor": "", "linhas": corpo})
    return caps, len(titulos), len(achados)


# ------------------------------------------------------------- main


def main():
    spec = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    md = Path(spec["md"])
    raw = md.read_text(encoding="utf-8", errors="ignore")

    # frontmatter -> vira linha vazia (preserva os indices do arquivo original)
    if raw.startswith("---"):
        fim = raw.find("\n---", 3)
        if fim > 0:
            pre = raw[:fim + 4]
            raw = "\n" * pre.count("\n") + raw[fim + 4:]
    linhas = raw.split("\n")

    linhas_orig = list(linhas)  # o sumario precisa dos indices ORIGINAIS
    corte = spec.get("ignorar_ate_linha") or 0
    if corte:
        # NAO fatiar: os numeros de linha do spec sao os do arquivo ORIGINAL.
        # Zerar o conteudo preserva os indices (bug medido 2026-11-25: fatiar
        # deslocava tudo e o capitulo comecava no meio do anterior).
        linhas = [""] * min(corte, len(linhas)) + linhas[corte:]

    linhas = limpar_linhas(linhas, spec.get("cabecalhos_corridos", []))

    if spec.get("capitulos_por_linha"):
        caps = capitulos_por_linha(linhas, spec)
    else:
        caps, n_toc, n_ok = capitulos_por_titulo(linhas, spec, linhas_orig)
        print(f"sumario: {n_toc} titulos | casados no corpo: {n_ok}")

    print(f"capitulos: {len(caps)}")

    book = epub.EpubBook()
    book.set_identifier("studyagent-" + re.sub(r"\W+", "-", spec["titulo"]).lower())
    book.set_title(spec["titulo"])
    book.set_language(spec.get("idioma", "pt"))
    book.add_author(spec.get("autor", "") or "Desconhecido")

    itens, spine = [], ["nav"]
    for i, c in enumerate(caps, 1):
        paras = juntar_paragrafos(c["linhas"])
        if not paras:
            continue
        h1 = html.escape(c["titulo"])
        sub = f'<p class="autor"><em>{html.escape(c["autor"])}</em></p>' if c["autor"] else ""
        ch = epub.EpubHtml(title=c["titulo"][:80],
                           file_name=f"cap{i:03d}.xhtml",
                           lang=spec.get("idioma", "pt"))
        ch.content = f"<h1>{h1}</h1>{sub}\n{paragrafos_html(paras)}"
        book.add_item(ch)
        itens.append(ch)
        spine.append(ch)

    book.toc = tuple(itens)
    book.add_item(epub.EpubNcx())
    book.add_item(epub.EpubNav())
    book.spine = spine
    out = Path(spec["epub"])
    out.parent.mkdir(parents=True, exist_ok=True)
    epub.write_epub(str(out), book, {})
    print(f"OK: {out} ({out.stat().st_size} bytes, {len(itens)} capitulos)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
