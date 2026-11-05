#!/usr/bin/env python3
"""Finaliza a aquisicao da rampa de ficcao — versao 3 (isolada).

BUGS CORRIGIDOS NESTA VERSAO:
  BUG A (2026-11-05, v1): o finalizador apagava .md ja convertidos porque usava
    o mtime do EPUB como criterio de "gerado agora" — o mtime do EPUB e ANTERIOR a
    todas as conversoes. Resultado: em pastas com >1 epub, restava so o ultimo .md.
  BUG B (2026-11-05, v2): quando a conversao FALHAVA (PDF sem pdftotext, MOBI sem
    conversor), o fallback "pega o .md mais recente" reaproveitava o .md de OUTRO
    livro, criando .md com o conteudo errado e o frontmatter de outra obra.
    Exemplo real: "A-Eneida-Virgilio.md" continha o texto da Odisseia.

SOLUCAO: cada arquivo e convertido num DIRETORIO TEMPORARIO proprio. O .md
resultante e movido para o destino so se a conversao produziu texto real. O
conteudo e validado (tamanho minimo + conferencia de que o titulo do livro
aparece no texto) antes de ser aceito.

Uso: python3 finalizar-rampa.py [--sem-push]
"""
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

ROOT = Path("/home/willian/study-agent")
BIB = ROOT / "data" / "biblioteca"
INCOMING = BIB / "_incoming"
DEST = BIB / "literatura-mundial-classica"
EPUB2MD = ROOT / "data" / "perfil" / "bibliotecario" / "biblioteca-orbit" / "epub2md.py"
KB = BIB / "global" / "kb-literatura.yaml"
LOG = ROOT / "data" / "perfil" / "bibliotecario" / "logs" / "rampa-ficcao-downloads.jsonl"

META = {
    "Dostoievski-Crime-e-Castigo": ("Crime e Castigo", "Fiodor Dostoievski", "dostoievski",
        ["literatura", "literatura-mundial", "romance", "canon-literario", "russo", "dostoievski"], 1866),
    "Dostoievski-Irmãos-Karamázov": ("Os Irmãos Karamázov", "Fiodor Dostoievski", "dostoievski",
        ["literatura", "literatura-mundial", "romance", "canon-literario", "russo", "dostoievski"], 1880),
    "Dostoievski-O-Idiota": ("O Idiota", "Fiodor Dostoievski", "dostoievski",
        ["literatura", "literatura-mundial", "romance", "canon-literario", "russo", "dostoievski"], 1869),
    "Dostoievski-Os-Demônios": ("Os Demônios", "Fiodor Dostoievski", "dostoievski",
        ["literatura", "literatura-mundial", "romance", "canon-literario", "russo", "dostoievski"], 1871),
    "Dostoievski-O-Jogador": ("O Jogador", "Fiodor Dostoievski", "dostoievski",
        ["literatura", "literatura-mundial", "romance", "canon-literario", "russo", "dostoievski"], 1866),
    "Tolstoi-Guerra-e-Paz": ("Guerra e Paz", "Lev Tolstoi", "tolstoi",
        ["literatura", "literatura-mundial", "romance", "canon-literario", "russo", "tolstoi"], 1869),
    "Tolstoi-Anna-Karênina": ("Anna Karênina", "Lev Tolstoi", "tolstoi",
        ["literatura", "literatura-mundial", "romance", "canon-literario", "russo", "tolstoi"], 1878),
    "Tolstoi-Ressurreição": ("Ressurreição", "Lev Tolstoi", "tolstoi",
        ["literatura", "literatura-mundial", "romance", "canon-literario", "russo", "tolstoi"], 1899),
    "Austen-Orgulho-e-Preconceito": ("Orgulho e Preconceito", "Jane Austen", "austen",
        ["literatura", "literatura-mundial", "romance", "canon-literario", "ingles", "austen"], 1813),
    "Austen-Emma": ("Emma", "Jane Austen", "austen",
        ["literatura", "literatura-mundial", "romance", "canon-literario", "ingles", "austen"], 1815),
    "Brontë-Jane-Eyre": ("Jane Eyre", "Charlotte Brontë", "bronte",
        ["literatura", "literatura-mundial", "romance", "canon-literario", "ingles", "bronte"], 1847),
    "Dickens-Grandes-Esperanças": ("Grandes Esperanças", "Charles Dickens", "dickens",
        ["literatura", "literatura-mundial", "romance", "canon-literario", "ingles", "dickens"], 1861),
    "Dickens-Casa-Cassandra": ("Casa de Cassandra", "Charles Dickens", "dickens",
        ["literatura", "literatura-mundial", "romance", "canon-literario", "ingles", "dickens"], 1853),
    "Dickens-David-Copperfield": ("David Copperfield", "Charles Dickens", "dickens",
        ["literatura", "literatura-mundial", "romance", "canon-literario", "ingles", "dickens"], 1850),
    "Agostinho-Cidade-de-Deus": ("A Cidade de Deus", "Santo Agostinho", "agostinho",
        ["literatura", "literatura-mundial", "canon-literario", "latim", "teologia"], 426),
    "Agostinho-Confissoes": ("Confissões", "Santo Agostinho", "agostinho",
        ["literatura", "literatura-mundial", "canon-literario", "latim", "teologia", "autobiografia"], 397),
    "Dante-Divina-Comédia": ("A Divina Comédia", "Dante Alighieri", "dante",
        ["literatura", "literatura-mundial", "poesia", "canon-literario", "italiano"], 1321),
    "Flaubert-Madame-Bovary": ("Madame Bovary", "Gustave Flaubert", "frances",
        ["literatura", "literatura-mundial", "romance", "canon-literario", "frances"], 1857),
    "Proust-Em-Busca-do-Tempo-Perdido-1": ("Em Busca do Tempo Perdido I", "Marcel Proust", "proust",
        ["literatura", "literatura-mundial", "romance", "canon-literario", "frances", "modernismo"], 1913),
    "Homero-A-Odissia": ("A Odisséia", "Homero", "antigos",
        ["literatura", "literatura-mundial", "poesia", "canon-literario", "grego", "antigos"], -700),
    "Virgilio-A-Eneida": ("A Eneida", "Virgílio", "antigos",
        ["literatura", "literatura-mundial", "poesia", "canon-literario", "latim", "antigos"], -29),
    "Goethe-Fausto": ("Fausto", "Johann Wolfgang von Goethe", "antigos",
        ["literatura", "literatura-mundial", "poesia", "canon-literario", "alemao", "dramaturgia"], 1808),
    "Hugo-Les-Miserables": ("Os Miséráveis", "Victor Hugo", "frances",
        ["literatura", "literatura-mundial", "romance", "canon-literario", "frances"], 1862),
    "Melville-Moby-Dick": ("Moby Dick", "Herman Melville", "anglo-saxoes",
        ["literatura", "literatura-mundial", "romance", "canon-literario", "ingles"], 1851),
    "Eliot-George-Middlemarch": ("Middlemarch", "George Eliot", "anglo-saxoes",
        ["literatura", "literatura-mundial", "romance", "canon-literario", "ingles"], 1871),
    "Shelley-Frankenstein": ("Frankenstein", "Mary Shelley", "anglo-saxoes",
        ["literatura", "literatura-mundial", "romance", "canon-literario", "ingles", "gotico"], 1818),
    "Twain-As-Aventuras-de-Tom-Sawyer": ("As Aventuras de Tom Sawyer", "Mark Twain", "anglo-saxoes",
        ["literatura", "literatura-mundial", "romance", "canon-literario", "ingles"], 1876),
    "Twain-Huckleberry-Finn": ("As Aventuras de Huckleberry Finn", "Mark Twain", "anglo-saxoes",
        ["literatura", "literatura-mundial", "romance", "canon-literario", "ingles"], 1884),
    "Orwell-1984": ("1984", "George Orwell", "anglo-saxoes",
        ["literatura", "literatura-mundial", "romance", "canon-literario", "ingles", "distopia"], 1949),
    "Orwell-A-Revolucao-dos-Animais": ("A Revolução dos Animais", "George Orwell", "anglo-saxoes",
        ["literatura", "literatura-mundial", "fabula", "canon-literario", "ingles", "distopia"], 1945),
    "Joyce-Retratos": ("Retratos", "James Joyce", "anglo-saxoes",
        ["literatura", "literatura-mundial", "contos", "canon-literario", "ingles", "modernismo"], 1914),
    "Woolf-A-Mrs-Dalloway": ("Mrs Dalloway", "Virginia Woolf", "anglo-saxoes",
        ["literatura", "literatura-mundial", "romance", "canon-literario", "ingles", "modernismo"], 1925),
    "Maupassant-Contos": ("Contos", "Guy de Maupassant", "contos",
        ["literatura", "literatura-mundial", "contos", "canon-literario", "frances"], 1884),
    "Kipling-Kim": ("Kim", "Rudyard Kipling", "anglo-saxoes",
        ["literatura", "literatura-mundial", "romance", "canon-literario", "ingles"], 1901),
    "Chesterton-Ortodoxia": ("Ortodoxia", "G. K. Chesterton", "cristiana",
        ["literatura", "literatura-mundial", "canon-literario", "ingles", "cristiana", "apologetica"], 1908),
    "Chesterton-O-Homem-que-foi-Quinta-feira": ("O Homem que foi Quinta-feira", "G. K. Chesterton", "cristiana",
        ["literatura", "literatura-mundial", "romance", "canon-literario", "ingles", "cristiana"], 1905),
    "Lewis-O-Problema-da-Dor": ("O Problema da Dor", "C. S. Lewis", "cristiana",
        ["literatura", "literatura-mundial", "canon-literario", "ingles", "cristiana", "apologetica"], 1940),
    "Bunyan-O-Peregrino": ("O Peregrino", "John Bunyan", "cristiana",
        ["literatura", "literatura-mundial", "canon-literario", "ingles", "cristiana", "alegoria"], 1678),
    "Greene-O-Poder-e-a-Gloria": ("O Poder e a Glória", "Graham Greene", "cristiana",
        ["literatura", "literatura-mundial", "romance", "canon-literario", "ingles", "cristiana"], 1940),
    "OConnor-A-Wise-Blood": ("A Wise Blood", "Flannery O'Connor", "cristiana",
        ["literatura", "literatura-mundial", "romance", "canon-literario", "ingles", "cristiana"], 1952),
}

MIN_BYTES = 40000          # abaixo disso, nao e um livro (erro de conversao)
MIN_LINHAS = 800


def sem_acento(s):
    return "".join(c for c in unicodedata.normalize("NFKD", s or "")
                   if not unicodedata.combining(c))


def slug_canonico(titulo, autor):
    s = f"{titulo} - {autor}"
    s = sem_acento(s).replace("\u00a0", " ").replace("\u202f", " ").replace("\u2014", "-")
    s = re.sub(r"[^\w\s-]", "", s)
    s = re.sub(r"[\s_]+", "-", s)
    s = re.sub(r"-{2,}", "-", s).strip("-")
    return s[:70].strip("-")


def frontmatter(titulo, autor, tags, ano):
    t = ", ".join(f'"{x}"' for x in tags)
    return ("---\n"
            f'titulo: "{titulo}"\n'
            f'autor: "{autor}"\n'
            "idioma: Portuguese\n"
            f"ano: {ano}\n"
            f"tags: [{t}]\n"
            "tipo: literatura\n"
            "origem: rampa-ficcao-2026-11\n"
            "---\n\n")


def log(ev, **kw):
    rec = {"ts": time.strftime("%Y-%m-%dT%H:%M:%S"), "event": ev, **kw}
    with LOG.open("a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")


def cataloga_kb(entrada):
    txt = KB.read_text(encoding="utf-8")
    if entrada["caminho_md"] in txt:
        return "ja-catalogado"
    linha = (f"  - titulo: {entrada['titulo']}\n"
             f"    caminho_md: {entrada['caminho_md']}\n"
             f"    tamanho_md: {entrada['tamanho_md']}\n"
             f"    linhas_md: {entrada['linhas_md']}\n"
             "    idioma: Portuguese\n"
             f"    tags: [{entrada['tags_yaml']}]\n"
             f"    ano: {entrada['ano']}\n"
             "    status: indexado_auto\n"
             "    nota: Adquirido 2026-11-05 (rampa de ficcao, traducao PT-BR).\n")
    m = re.search(r"^knowledge_base_literatura:\n(?:.*\n)*?\s*materiais:\n", txt, re.M)
    if not m:
        return "falha-bloco"
    KB.write_text(txt[:m.end()] + linha + txt[m.end():], encoding="utf-8")
    return "catalogado"


def conteudo_confere(texto, titulo):
    """Confere que o texto parece ser o livro certo: o titulo (ou parte dele)
    aparece no corpo. Evita o BUG B (md de outro livro).

    BUG C (2026-11-05): a busca era feita so nos primeiros 60.000 chars.
    Livros SEM folha de rosto (EPUBs de z-library sem pagina de titulo) so
    mencionam o proprio titulo no apendice/posfacio, no FIM do texto. O 1984
    foi rejeitado por isso e nunca entrou no acervo. Agora busca no texto INTEIRO
    (e os primeiros 60k continuam valendo para o caminho rapido)."""
    t = sem_acento(titulo).lower()
    corpo = sem_acento(texto).lower()
    if t in corpo:
        return True
    # titulo com particles: testa sem os articles
    partes = [p for p in re.split(r"\s+", t) if len(p) > 3 and p not in ("de", "da", "do", "e")]
    if partes and all(p in corpo for p in partes[:3]):
        return True
    return False


def main():
    sem_push = "--sem-push" in sys.argv
    # remove artefatos dos testes anteriores
    for pasta in DEST.rglob("*"):
        if pasta.is_dir() and pasta.name == "outros":
            for f in pasta.glob("TESTE-*.md"):
                f.unlink()
            if not any(pasta.iterdir()):
                pasta.rmdir()

    arquivos = [f for f in sorted(INCOMING.iterdir())
                if f.suffix.lower() in (".epub", ".pdf", ".mobi", ".azw3")
                and not f.stem.startswith("TESTE")]
    print(f"{len(arquivos)} arquivo(s) a finalizar\n")
    prontos, falhas = [], []
    for e in arquivos:
        meta = META.get(e.stem)
        if not meta:
            print(f"[SEM-META] {e.name}")
            falhas.append((e.name, "sem-meta"))
            continue
        titulo, autor, subpasta, tags, ano = meta
        sub = DEST / subpasta
        sub.mkdir(parents=True, exist_ok=True)
        destino = sub / f"{slug_canonico(titulo, autor)}.md"

        # ---- conversao ISOLADA em tempdir (BUG B resolvido) ----
        tmp = Path(tempfile.mkdtemp(prefix="rampa-conv-"))
        try:
            r = subprocess.run([sys.executable, str(EPUB2MD), "--dest", str(tmp), str(e)],
                               capture_output=True, text=True, timeout=1800)
            mds = list(tmp.glob("*.md"))
            if not mds:
                print(f"[FALHA-CONV] {e.name}: {r.stdout[-200:]}")
                falhas.append((e.name, "conversao-sem-md"))
                continue
            gerado = max(mds, key=lambda p: p.stat().st_size)
            txt = gerado.read_text(encoding="utf-8", errors="ignore")
            linhas = txt.count("\n")
            if gerado.stat().st_size < MIN_BYTES or linhas < MIN_LINHAS:
                print(f"[FALHA-CONV] {e.name}: texto curto demais "
                      f"({gerado.stat().st_size//1024} KB, {linhas} lin) — provavelmente erro de extracao")
                falhas.append((e.name, "texto-curto"))
                continue
            if not conteudo_confere(txt, titulo):
                print(f"[FALHA-CONV] {e.name}: titulo '{titulo}' nao aparece no texto extraido "
                      f"— conteudo provavelmente de outro livro")
                falhas.append((e.name, "conteudo-divergente"))
                continue
            # move ATOMICO: os.shutil.move ja substitui, e nao ha janela
            # em que o destino fica ausente (bug que apagava o .md).
            shutil.move(str(gerado), str(destino), copy_function=os.replace)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

        txt = destino.read_text(encoding="utf-8", errors="ignore")
        if not txt.lstrip().startswith("---"):
            destino.write_text(frontmatter(titulo, autor, tags, ano) + txt, encoding="utf-8")
        final = destino.read_text(encoding="utf-8", errors="ignore")
        entrada = {
            "titulo": f"LT {titulo} - {autor}",
            "caminho_md": f"./data/biblioteca/literatura-mundial-classica/{subpasta}/{destino.name}",
            "tamanho_md": f"{destino.stat().st_size // 1024} KB",
            "linhas_md": final.count("\n"),
            "tags_yaml": ", ".join(tags),
            "ano": ano,
        }
        st = cataloga_kb(entrada)
        prontos.append((destino, e, titulo, autor))
        print(f"[OK] {subpasta}/{destino.name[:54]:54s} {destino.stat().st_size//1024:5d} KB "
              f"{entrada['linhas_md']:6d} lin | KB={st}")
        log("finalizado", arquivo=str(destino.relative_to(ROOT)), kb=st)

    print(f"\n=== prontos: {len(prontos)} | falhas: {len(falhas)} ===")
    for f, m in falhas:
        print("  falha:", f, "-", m)

    if sem_push or not prontos:
        return
    print("\n=== push para o Orbit ===")
    push = ROOT / "data" / "perfil" / "bibliotecario" / "biblioteca-orbit" / "biblioteca-push.sh"
    for destino, e, titulo, autor in prontos:
        r = subprocess.run(["bash", str(push), "--autor", autor, str(e)],
                           capture_output=True, text=True, timeout=300)
        ok = r.returncode == 0
        print(f"  {'OK  ' if ok else 'ERRO'} {e.name[:46]:46s} {r.stdout.strip()[:70]}")
        if ok:
            e.unlink()
            log("orbit-push", arquivo=e.name, autor=autor)


if __name__ == "__main__":
    main()
