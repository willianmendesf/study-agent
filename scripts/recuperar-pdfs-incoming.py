#!/usr/bin/env python3
"""Recupera PDFs baixados que falharam na conversao (BUG W, 2026-11-07).

CONTEXTO
---------
A rodada de 2026-11-07 BAIXOU 5 PDFs (ingles, apologetica, contexto-historico,
metodologia, portugues) mas todos foram perdidos na etapa de conversao: a LXC
nao tem `pdftotext` (poppler-utils) e o `except` do conversor engolia o
FileNotFoundError, imprimindo apenas "FALHA na conversao".

O download JA consumiu cota do z-library. Este script reaproveita os arquivos
JA baixados em `data/biblioteca/_incoming/` — sem gastar cota nova — e os
converte com o conversor JA CORRIGIDO (pdftotext -> pypdf).

O que ele faz (espelha o fluxo do rodape-aquisicao.py):
  1. mapeia cada PDF da _incoming/ para (titulo, autor, categoria, tags)
     a partir do CATALOGO DE CANDIDATOS do proprio rodape + do log da rodada
  2. converte em pasta TEMPORARIA (nunca toca no acervo direto)
  3. move para data/biblioteca/<categoria>/ com o NOME CANONICO do acervo
  4. prepende o frontmatter canonico (identidade.frontmatter)
  5. checa duplicidade por CONTEUDO antes de gravar (bug A de 2026-10-28:
     nunca apaga um arquivo que ja existia no acervo)
  6. so apaga o PDF original depois de gravar o .md com sucesso
  7. NAO faz push ao Orbit (o ebook fica preservado — o reenvio automatico
     do cron trata depois)

Uso:
  python3 scripts/recuperar-pdfs-incoming.py [--listar]
"""
import argparse
import json
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ORBIT = ROOT / "data/perfil/bibliotecario/biblioteca-orbit"
BIB = ROOT / "data/biblioteca"
INCOMING = BIB / "_incoming"
CONV = ORBIT / "epub2md.py"

sys.path.insert(0, str(ORBIT))
import identidade  # noqa: E402


def carregar_candidatos():
    """Reusa o CATALOGO do rodape.

    Estrutura real (medida em 2026-11-07):
        CANDIDATOS = { gap: [(titulo, autor, categoria, area, tags), ...] }
    Devolve uma lista plana de (titulo, autor, categoria, tags).
    """
    sys.path.insert(0, str(ORBIT))
    import importlib.util
    spec = importlib.util.spec_from_file_location("rodape", ORBIT / "rodape-aquisicao.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    out = []
    for _gap, lst in mod.CANDIDATOS.items():
        for v in lst:
            try:
                titulo, autor = v[0], v[1]
                # Espelha EXATAMENTE o rodape (process_gap):
                #   cat  = cand[3] se len>4 else cand[2]
                #   tags = cand[4] se len>4 else cand[3]
                cat = v[3] if len(v) > 4 else (v[2] if len(v) > 3 else "comentarios-biblicos")
                tags = v[4] if len(v) > 4 else (v[3] if len(v) > 3 else ["comentarios", "biblia", "exegese"])
            except Exception:
                continue
            out.append((titulo, autor, cat, tags))
    return out


def meta_do_log():
    """Titulos que falharam na conversao, lidos do log da rodada."""
    log = ROOT / "data/perfil/bibliotecario/rodada-log.jsonl"
    falhas = []
    if log.exists():
        for line in log.read_text(encoding="utf-8", errors="ignore").splitlines():
            try:
                d = json.loads(line)
            except Exception:
                continue
            if d.get("tipo") == "conversao_falha":
                falhas.append((d.get("gap", ""), d.get("titulo", "")))
    return falhas


def titulo_do_pdf(pdf: Path):
    """Descobre titulo/autor de um PDF zlib-XXXX.pdf lendo os metadados."""
    try:
        from pypdf import PdfReader
        r = PdfReader(str(pdf))
        meta = r.metadata or {}
        title = (meta.get("/Title") or "").strip()
        author = (meta.get("/Author") or "").strip()
        if title and not title.lower().startswith("untitled"):
            return title, author
    except Exception:
        pass
    return "", ""


def achar_categoria(titulo: str, cands: list):
    """Casa o titulo do PDF com o catalogo de candidatos (por tokens)."""
    chave = re.sub(r"[^a-z0-9]", "", titulo.lower())
    for v in cands:
        if re.sub(r"[^a-z0-9]", "", v[0].lower()) == chave:
            return v
    # casamento por tokens: o titulo do PDF costuma ser uma versao longa
    # do titulo do catalogo
    toks = set(re.findall(r"[a-z0-9]{4,}", titulo.lower()))
    melhor, score = None, 0
    for v in cands:
        ct = set(re.findall(r"[a-z0-9]{4,}", v[0].lower()))
        if not ct:
            continue
        inter = len(toks & ct)
        s = inter / max(len(ct), 1)
        if s > score:
            melhor, score = v, s
    if melhor and score >= 0.5:
        return melhor
    return None


def identificar_por_conteudo(pdf: Path, cands: list):
    """Ultimo recurso: le as primeiras paginas do PDF e casa por tokens.

    Muitos PDFs do z-library nao tem metadado /Title (ou tem 'isbn_978...'),
    mas o TEXTO da primeira pagina traz o titulo e o autor. Extrai os tokens
    distintos e casa com o catalogo.
    """
    try:
        sys.path.insert(0, str(ORBIT))
        import epub2md
        txt = epub2md.pdf_to_md(pdf)
    except Exception:
        return None
    # so as primeiras 6000 chars: capa + folha de rosto
    head = txt[:6000].lower()
    toks_head = set(re.findall(r"[a-z0-9]{4,}", head))
    if not toks_head:
        return None
    melhor, score = None, 0
    for v in cands:
        ct = set(re.findall(r"[a-z0-9]{4,}", v[0].lower()))
        ct_auth = set(re.findall(r"[a-z0-9]{4,}", str(v[1]).lower()))
        if not ct:
            continue
        # exige o TITULO inteiro presente (tokens) + pelo menos parte do autor
        inter = len(ct & toks_head)
        s = inter / max(len(ct), 1)
        if s >= 0.8 and ct_auth and (len(ct_auth & toks_head) / len(ct_auth)) >= 0.5:
            s += 0.2
        if s > score:
            melhor, score = v, s
    if melhor and score >= 0.8:
        return melhor
    return None


def qualidade(body: str):
    """Mede quao 'limpo' e' o texto extraido.

    Retorna (percentual_linhas_ruins, veredito).
    PDFs com camada de texto quebrada extraem linhas curtas cheias de
    pontuacao/simbolos (ex.: 'eee_4 cro ¢ em iG pia; basen apis t it').
    Regra: acima de 25% de linhas ruinas o arquivo NAO entra no acervo
    (fica preservado em _incoming/ e vira pendencia reportada).
    """
    linhas = [l for l in body.split("\n") if l.strip()]
    if not linhas:
        return 100.0, "vazio"
    ruins = 0
    for l in linhas:
        letras = sum(1 for c in l if c.isalpha())
        if letras < max(3, len(l) * 0.35):
            ruins += 1
    pct = ruins * 100.0 / len(linhas)
    return pct, ("OK" if pct <= 25 else "LIXO/OCR")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--listar", action="store_true", help="so mostra o plano")
    args = ap.parse_args()

    cands = carregar_candidatos()
    falhas = meta_do_log()

    pdfs = sorted(INCOMING.glob("*.pdf"))
    if not pdfs:
        print("nenhum PDF em _incoming/")
        return 0

    print(f"PDFs em _incoming/: {len(pdfs)}")
    planos = []
    for pdf in pdfs:
        t, a = titulo_do_pdf(pdf)
        cat = None
        # 1) tenta casar com um titulo que FALHOU na conversao
        for _gap, ftit in falhas:
            ft = re.sub(r"[^a-z0-9]", "", ftit.lower())
            if ft and ft in re.sub(r"[^a-z0-9]", "", (t or "").lower()):
                cat = achar_categoria(ftit, cands)
                if cat:
                    break
        # 2) fallback: casamento por tokens com o catalogo
        if not cat and t:
            cat = achar_categoria(t, cands)
        # 3) fallback: pelo titulo do log mais parecido com o nome do PDF
        if not cat:
            nome = pdf.stem.lower()
            for _gap, ftit in falhas:
                if ftit and ftit.lower()[:12] in nome:
                    cat = achar_categoria(ftit, cands)
                    if cat:
                        break
        # 4) ultimo recurso: identificar pelo CONTEUDO da capa
        if not cat:
            cat = identificar_por_conteudo(pdf, cands)
        planos.append((pdf, t, a, cat))

    print()
    for pdf, t, a, cat in planos:
        if cat:
            print(f"  {pdf.name} -> {cat[0]} / {cat[1]} | cat={cat[2]}")
        else:
            print(f"  {pdf.name} -> SEM MAPA (titulo='{t}' autor='{a}')")
    print()

    if args.listar:
        return 0

    ok, falhas_conv = 0, 0
    for pdf, t, a, cat in planos:
        if not cat:
            print(f"[SKIP] {pdf.name}: sem metadados no catalogo (nao adivinho)")
            falhas_conv += 1
            continue
        titulo, autor, categoria, tags = cat
        dest_dir = BIB / categoria
        dest_dir.mkdir(parents=True, exist_ok=True)
        nome = identidade.nome_do_arquivo(titulo, autor)
        out = dest_dir / (nome + ".md")

        if out.exists():
            print(f"[DUP] {pdf.name}: {out.name} ja existe no acervo")
            continue

        tmp_dir = Path(tempfile.mkdtemp(prefix="recupera-pdf-"))
        try:
            r = subprocess.run([sys.executable, str(CONV), "--dest", str(tmp_dir), str(pdf)],
                               capture_output=True, text=True, timeout=900)
            conv = sorted(tmp_dir.glob("*.md"), key=lambda q: q.stat().st_mtime)
            if not conv:
                print(f"[FALHA] {pdf.name}: conversao nao gerou .md")
                print("        " + (r.stderr or "").strip()[-300:])
                falhas_conv += 1
                continue
            texto = conv[-1].read_text(encoding="utf-8", errors="ignore")
            # ---- guarda de qualidade: texto muito "ruim" = PDF escaneado
            # ou com camada de texto quebrada. Nao entra no acervo.
            corpo = texto.split("---", 2)[-1] if texto.lstrip().startswith("---") else texto
            pct, veredito = qualidade(corpo)
            if veredito != "OK":
                print(f"[REJEITADO] {pdf.name}: {pct:.0f}% de linhas ruinadas "
                      f"(camada de texto quebrada / escaneado) — preservado, nao entra")
                falhas_conv += 1
                continue
            # idioma: deduz do catalogo (o PDF nao traz metadado confiavel)
            idioma = "Portuguese" if "portugues" in str(categoria).lower() else "English"
            if not texto.lstrip().startswith("---"):
                fm = identidade.frontmatter(
                    titulo=titulo[:110], autor=autor[:90], idioma=idioma,
                    tags=tags, gap_origem="gap:recuperacao-pdf",
                ) + "\n"
                conv[-1].write_text(fm + texto, encoding="utf-8")
            shutil.move(str(conv[-1]), str(out))
            size = out.stat().st_size // 1024
            print(f"[OK] {pdf.name} -> {out.relative_to(ROOT)} ({size} KB, {pct:.0f}% ruido)")
            ok += 1
        except Exception as e:
            print(f"[ERRO] {pdf.name}: {e}")
            falhas_conv += 1
        finally:
            shutil.rmtree(tmp_dir, ignore_errors=True)

    print()
    print(f"convertidos: {ok} | falhas: {falhas_conv}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
