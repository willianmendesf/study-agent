#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
digitalizar-fisico.py — pipeline de ESCANEAMENTO de livro fisico.

Por que existe (pedido do William, 2026-11-07):
  "se eu tiver fisico, escanear ele o livro, assim voce consegue raspar o livro
   e ter ele catalogado."

  A triagem de aquisicao tem 3 vias e o ORDEM IMPORTA:
    1. ja esta no acervo digital?  -> usar, nao comprar
    2. nao esta no acervo digital MAS o William tem fisico? -> ESCANEAR (nao comprar)
    3. nao tem nem digital nem fisico? -> AI sim vale comprar/baixar

  Este script faz a via 2: recebe imagens (ou PDF) do livro fisico, passa por
  OCR (tesseract PT), gera o `.md` do acervo, normaliza (Regra 2) e cataloga.

Nao compra. Nao faz upload sozinho. Nao escreve em sistema externo.

Fluxo:
  1. `python3 scripts/digitalizar-fisico.py --preparar` -> cria a pasta do
     trabalho e imprime o comando de captura.
  2. Coloque as fotos (ou um PDF) em data/biblioteca/_incoming/<slug>/
  3. `python3 scripts/digitalizar-fisico.py --slug <slug> --titulo "..." \\
        --autor "..."` -> gera .md + cataloga na KB

Regras:
  - OCR em portugues (tesseract-ocr-por) com fallback para eng.
  - O `.md` gerado passa por .claude/scripts/normalizar_md.py (junta letras
    espacadas do OCR).
  - Nunca grava segredo. Nunca baixa nada.
"""
import argparse
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
INCOMING = ROOT / "data/biblioteca/_incoming"
BIBLIOTECA = ROOT / "data/biblioteca"

TESS = shutil.which("tesseract")
TESS_LANG = "por+eng"


def slugificar(titulo: str) -> str:
    s = (titulo or "").strip()
    s = re.sub(r"[^\w\s-]", "", s, flags=re.UNICODE)
    s = re.sub(r"[\s_-]+", "-", s).strip("-")
    return s or "livro-sem-titulo"


def imagem_para_txt(caminho: Path, lang=TESS_LANG) -> str:
    """OCR de uma imagem. Retorna '' se nao conseguir."""
    if not TESS:
        return ""
    cmd = [TESS, str(caminho), "stdout", "-l", lang, "--psm", "3"]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
        return r.stdout or ""
    except Exception as e:  # noqa
        sys.stderr.write(f"[ocr falhou] {caminho}: {e}\n")
        return ""


def pdf_para_txt(caminho: Path, lang=TESS_LANG) -> str:
    """PDF escaneado (sem texto) -> OCR. Se o PDF ja tem texto, extrai direto."""
    if not shutil.which("pdftotext"):
        return ""
    # 1) tenta extrair texto nativo (rapido e melhor)
    try:
        r = subprocess.run(["pdftotext", str(caminho), "-"],
                           capture_output=True, text=True, timeout=300)
        txt = (r.stdout or "").strip()
        if len(txt) > 400:  # tem texto de verdade
            return txt
    except Exception:
        pass
    # 2) fallback: rasteriza e faz OCR
    if not shutil.which("pdftoppm"):
        return ""
    tmp = Path("/tmp/ocrpdf")
    tmp.mkdir(exist_ok=True)
    for f in tmp.glob("pg-*"):
        f.unlink()
    subprocess.run(["pdftoppm", "-r", "300", "-png", str(caminho), str(tmp / "pg")],
                   capture_output=True, timeout=900)
    paginas = sorted(tmp.glob("pg-*.png"))
    partes = []
    for i, p in enumerate(paginas, 1):
        t = imagem_para_txt(p, lang)
        partes.append(f"\n\n===== [página {i}] =====\n\n{t}")
        print(f"  OCR página {i}/{len(paginas)}", file=sys.stderr)
    return "".join(partes)


def limpar_ocr(txt: str) -> str:
    """Limpeza minima: hifenizacao de fim de linha, espacos duplicados."""
    txt = re.sub(r"(\w)-\n(\w)", r"\1\2", txt)   # palavra partida
    txt = re.sub(r"[ \t]{2,}", " ", txt)
    txt = re.sub(r"\n{3,}", "\n\n", txt)
    return txt.strip()


def frontmatter(titulo, autor, slug, palavras, paginas):
    return (
        "---\n"
        f'titulo: "{titulo}"\n'
        f'tags: [literatura, literatura-mundial, digitalizado-fisico]\n'
        f'tagged_em: \'{_hoje()}\'\n'
        "tagged_por: bibliotecario (digitalizacao de exemplar fisico)\n"
        f"autor: \"{autor or ''}\"\n"
        f"origem: fisico-digitalizado\n"
        f"slug: {slug}\n"
        f"palavras_aprox: {palavras}\n"
        f"paginas_estimadas: {paginas}\n"
        "---\n\n"
    )


def _hoje():
    import datetime
    return datetime.date.today().isoformat()


def preparar(slug: str) -> Path:
    pasta = INCOMING / slug
    pasta.mkdir(parents=True, exist_ok=True)
    (pasta / "COMO-ENVIAR.md").write_text(
        f"""# Como enviar o livro fisico para digitalizacao

Pasta: `{pasta}`

**Opcao A — fotos (recomendado, mais simples):**
Fotografe as paginas em PDF ou JPG, na ordem, e coloque aqui:
- `pagina-001.jpg`, `pagina-002.jpg`, ...
- Ou um unico `livro.pdf` com todas as paginas.

**Opcao B — PDF pronto:**
Um PDF escaneado tambem serve. Se ele tiver texto (nao for so imagem),
o pipeline extrai direto (melhor resultado). Se for imagem, faz OCR.

**Qualidade:**
- Resolucao minima: 200 dpi (ideal 300).
- Luz uniforme, sem sombra na dobra, pagina reta.
- Sem flash.

**Depois:** chame o IAM com `--slug {slug}`.
""", encoding="utf-8")
    print(f"[digitalizar] pasta preparada: {pasta}")
    return pasta


def processar(slug, titulo, autor, destino_subpasta="digitalizados"):
    pasta = INCOMING / slug
    if not pasta.exists():
        raise SystemExit(f"pasta ausente: {pasta} (use --preparar antes)")
    arquivos = sorted([p for p in pasta.iterdir()
                        if p.suffix.lower() in {".jpg", ".jpeg", ".png", ".pdf", ".webp"}])
    if not arquivos:
        raise SystemExit(f"nenhum arquivo de imagem/PDF em {pasta}")

    partes = []
    paginas = 0
    for a in arquivos:
        if a.suffix.lower() == ".pdf":
            print(f"[digitalizar] PDF: {a.name}", file=sys.stderr)
            t = pdf_para_txt(a)
            n = len(re.findall(r"\[página \d+\]", t))
        else:
            print(f"[digitalizar] imagem: {a.name}", file=sys.stderr)
            t = imagem_para_txt(a)
            n = 1
        if t.strip():
            partes.append(f"\n\n===== [{a.name}] =====\n\n{t}")
            paginas += n
    if not partes:
        raise SystemExit("OCR nao produziu texto — verifique a qualidade das imagens")

    txt = limpar_ocr("".join(partes))
    palavras = len(re.findall(r"\w+", txt))
    if palavras < 50:
        raise SystemExit(f"texto curto demais ({palavras} palavras) — provavelmente falha de OCR")

    dest = BIBLIOTECA / destino_subpasta
    dest.mkdir(parents=True, exist_ok=True)
    nome = f"{slug}.md"
    md = dest / nome
    md.write_text(frontmatter(titulo, autor, slug, palavras, paginas) + txt + "\n",
                  encoding="utf-8")

    # normalizador (Regra 2: junta letras espacadas do OCR)
    norm = ROOT / ".claude/scripts/normalizar_md.py"
    if norm.exists():
        r = subprocess.run([sys.executable, str(norm), str(md)],
                           capture_output=True, text=True)
        print(f"[normalizar] {r.stdout.strip() or r.stderr.strip()}", file=sys.stderr)

    print(f"[digitalizar] OK -> {md}  ({palavras} palavras, {paginas} paginas)")
    return md


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--preparar", metavar="SLUG", help="cria a pasta de envio")
    ap.add_argument("--slug")
    ap.add_argument("--titulo")
    ap.add_argument("--autor")
    ap.add_argument("--destino", default="digitalizados")
    args = ap.parse_args()

    if args.preparar:
        preparar(args.preparar)
        return 0
    if args.slug:
        if not args.titulo:
            raise SystemExit("--titulo e obrigatorio")
        processar(args.slug, args.titulo, args.autor, args.destino)
        return 0
    ap.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
