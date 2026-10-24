#!/usr/bin/env python3
"""Converte EPUB/PDF (puro Python + pdftotext) para .md com frontmatter mínimo.

Sem markitdown/pip — só stdlib (zipfile, html.parser, re) + poppler-utils (pdftotext).
Saída: data/biblioteca/<categoria>/<slug>.md com frontmatter `titulo` + `tags`.
A normalização de letras espaçadas fica para `.claude/scripts/normalizar_md.py`.

Uso:
  python3 .claude/scripts/ingestionar_incoming.py <arquivo> <categoria> <autor> <titulo> [<tags_csv>]
"""
import os
import re
import sys
import zipfile
import html
import subprocess
from html.parser import HTMLParser
from pathlib import Path


RAIZ = Path("/dados/study-agent")
BIBLIOTECA = RAIZ / "data" / "biblioteca"


class _EpubParaTexto(HTMLParser):
    """Extrai texto de HTML/XHTML de EPUB, mantendo estrutura de parágrafos."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.partes = []
        self._em_bloco = False
        self._bloco = []
        self._pular = 0  # profundidade de tags puladas (script/style)

    def handle_starttag(self, tag, attrs):
        if tag in ('script', 'style'):
            self._pular += 1
            return
        if tag in ('p', 'div', 'br', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'li', 'blockquote'):
            self._fechar_bloco()
            self._em_bloco = True

    def handle_endtag(self, tag):
        if tag in ('script', 'style'):
            self._pular = max(0, self._pular - 1)
            return
        if tag in ('p', 'div', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'li', 'blockquote'):
            self._fechar_bloco()
            self._em_bloco = False

    def handle_data(self, data):
        if self._pular:
            return
        texto = data.strip()
        if not texto:
            return
        if self._em_bloco:
            self._bloco.append(texto)
        else:
            self._bloco.append(texto)

    def _fechar_bloco(self):
        if self._bloco:
            linha = ' '.join(self._bloco).strip()
            linha = re.sub(r'\s+', ' ', linha)
            if linha:
                self.partes.append(linha)
            self._bloco = []

    def texto(self):
        self._fechar_bloco()
        # remove linhas duplicadas consecutivas
        saida = []
        for linha in self.partes:
            if not saida or saida[-1] != linha:
                saida.append(linha)
        return '\n\n'.join(saida)


def converter_epub(caminho: Path) -> str:
    """Lê todos os .xhtml/.html do EPUB e devolve texto markdown-like."""
    saida = []
    with zipfile.ZipFile(caminho) as z:
        # 1) tenta ler metadata dc:title
        try:
            with z.open('OEBPS/content.opf') as f:
                meta = f.read().decode('utf-8', errors='replace')
                m = re.search(r'<dc:title[^>]*>(.*?)</dc:title>', meta, re.DOTALL)
                if m:
                    saida.append(f'# {html.unescape(m.group(1).strip())}')
        except KeyError:
            pass
        # 2) ordena arquivos por caminho (ordem natural)
        nomes = sorted([n for n in z.namelist() if n.lower().endswith(('.xhtml', '.html', '.htm'))])
        for nome in nomes:
            with z.open(nome) as f:
                raw = f.read().decode('utf-8', errors='replace')
            parser = _EpubParaTexto()
            try:
                parser.feed(raw)
                parser.close()
            except Exception:
                continue
            texto = parser.texto()
            if texto.strip():
                saida.append(texto)
    return '\n\n'.join(saida)


def converter_pdf(caminho: Path) -> str:
    """Usa pdftotext (poppler) — preserva melhor layout que OCR."""
    try:
        res = subprocess.run(
            ['pdftotext', '-layout', '-enc', 'UTF-8', str(caminho), '-'],
            capture_output=True, text=True, check=True, timeout=600,
        )
        return res.stdout
    except subprocess.TimeoutExpired:
        sys.stderr.write(f'[aviso] pdftotext excedeu 600s em {caminho.name}\n')
        return ''
    except subprocess.CalledProcessError as e:
        sys.stderr.write(f'[erro] pdftotext falhou em {caminho.name}: {e.stderr}\n')
        return ''


def slug(texto: str) -> str:
    s = texto.lower()
    # remove acentos
    import unicodedata
    s = ''.join(c for c in unicodedata.normalize('NFD', s) if unicodedata.category(c) != 'Mn')
    s = re.sub(r'[^a-z0-9]+', '-', s)
    s = s.strip('-')
    return s[:120] or 'livro'


def main():
    if len(sys.argv) < 5:
        print(__doc__, file=sys.stderr)
        sys.exit(2)
    arquivo = Path(sys.argv[1])
    categoria = sys.argv[2]
    autor = sys.argv[3]
    titulo = sys.argv[4]
    tags = sys.argv[5].split(',') if len(sys.argv) > 5 and sys.argv[5] else []

    if not arquivo.is_file():
        print(f'[erro] arquivo não existe: {arquivo}', file=sys.stderr)
        sys.exit(1)

    ext = arquivo.suffix.lower()
    if ext == '.epub':
        texto = converter_epub(arquivo)
    elif ext == '.pdf':
        texto = converter_pdf(arquivo)
    else:
        print(f'[erro] extensão não suportada: {ext}', file=sys.stderr)
        sys.exit(1)

    if not texto.strip():
        print(f'[erro] conversão vazia para {arquivo.name}', file=sys.stderr)
        sys.exit(3)

    # frontmatter
    tags_yaml = '[' + ', '.join(tags) + ']' if tags else '[]'
    autor_linha = f'  autor: "{autor}"\n' if autor else ''
    frontmatter = (
        '---\n'
        f'titulo: "{titulo}"\n'
        f'{autor_linha}'
        f'tags: {tags_yaml}\n'
        f'caminho_origem: "{arquivo.name}"\n'
        '---\n\n'
    )
    corpo = frontmatter + f'# {titulo}\n\n' + texto.strip() + '\n'

    # destino
    dest_dir = BIBLIOTECA / categoria
    dest_dir.mkdir(parents=True, exist_ok=True)
    nome_dest = f'{slug(autor + "-" + titulo if autor else titulo)}.md'
    dest = dest_dir / nome_dest
    if dest.exists():
        # não sobrescreve
        i = 2
        while True:
            cand = dest_dir / f'{dest.stem}-{i}.md'
            if not cand.exists():
                dest = cand
                break
            i += 1

    dest.write_text(corpo, encoding='utf-8')
    print(f'OK  {arquivo.name}')
    print(f'    -> {dest.relative_to(RAIZ)}  ({len(corpo):,} bytes, {len(texto.split()):,} palavras)')


if __name__ == '__main__':
    main()
