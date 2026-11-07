#!/usr/bin/env python3
"""Consolida `pipeline-estado.json` — corrige as chaves ORFAAS.

POR QUE (bug de 2026-11-07):
  O `pipeline-estado.json` e' escrito por TRES scripts querokeram o mesmo
  arquivo (`pipeline-aquisicao.py`, `pipeline-biblio.py`,
  `semear-estado-pipeline.py`), e as chaves derivadas do CATALOGO mudaram
  de formato ao longo do tempo (ex.: "capital-eca-queiroz" ->
  "A-Capital-Eca-de-Queiroz"). Resultado: 32 chaves do estado ficaram
  ORFAAS — o pipeline nunca mais as le, porque consulta o estado pelo slug
  ATUAL. Efeito real:
    - obra ja ADQUIRIDA (ex.: "Anna Karenina") voltava a "pendente";
    - obra que ja FALHOU era re-tentada (e a cota gasta de novo);
    - o `--status` reportava numeros que nao batiam com a realidade.

  Este script reconstroi o estado a partir de 3 fontes de verdade:
    (1) o proprio estado (migrando a chave antiga -> chave canonica);
    (2) o ACERVO (os .md em data/biblioteca/literatura-mundial-classica),
        lidos pelo FRONTMATTER (titulo + autor) — a ordem do nome do arquivo
        varia ("Contos-Voltaire.md" vs "Cervantes-Dom-Quixote.md"), entao
        casar pelo NOME do arquivo nao funciona;
    (3) o CATALOGO (define o conjunto canonico de chaves).

  REGRA de precedencia: "adquirido" > "falhou". Uma obra que consta como
  adquirida NUNCA volta a ser tentada.

USO:
  python3 scripts/migrar-estado-pipeline.py            # migra e mostra o resumo
  python3 scripts/migrar-estado-pipeline.py --dry      # so mostra o que faria
"""
import argparse
import difflib
import json
import re
import sys
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ESTADO = ROOT / "data" / "perfil" / "bibliotecario" / "pipeline-estado.json"
CATALOGO = ROOT / "data" / "perfil" / "bibliotecario" / "catalogo-ficcao.yaml"
BIB = ROOT / "data" / "biblioteca" / "literatura-mundial-classica"


def sem_acento(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFKD", s or "")
                   if not unicodedata.combining(c))


def slug(titulo, autor):
    """Slug CANONICO — identico ao de pipeline-aquisicao.py/finalizar-rampa.py.

    NAO mexa neste formato sem migrar o estado: a chave e' a identidade da
    obra dentro do estado.
    """
    s = sem_acento(f"{titulo} - {autor}")
    s = s.replace("—", "-").replace("–", "-")
    s = re.sub(r"[^\w\s-]", "", s)
    s = re.sub(r"[\s_]+", "-", s)
    s = re.sub(r"-{2,}", "-", s).strip("-")
    return s[:70].strip("-")


def chave_compacta(s: str) -> str:
    """Forma canonica de COMPARACAO (sem acentos, minusculas, so alfanumerico)."""
    return re.sub(r"[^a-z0-9]", "", sem_acento(s or "").lower())


def similar(a: str, b: str) -> float:
    return difflib.SequenceMatcher(None, chave_compacta(a),
                                   chave_compacta(b)).ratio()


def frontmatter(path: Path) -> dict:
    """Le o frontmatter (--- ... ---) de um .md. Tolera arquivo quebrado."""
    try:
        txt = path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return {}
    if not txt.lstrip().startswith("---"):
        return {}
    fim = txt.find("\n---", 3)
    if fim < 0:
        return {}
    bloco = txt[3:fim]
    out = {}
    for ln in bloco.splitlines():
        if ":" not in ln:
            continue
        k, _, v = ln.partition(":")
        v = v.strip().strip('"').strip("'")
        out[k.strip()] = v
    return out


def indexar_acervo():
    """-> [(titulo, autor, caminho_rel), ...] de cada .md do acervo."""
    out = []
    if not BIB.exists():
        return out
    for p in sorted(BIB.rglob("*.md")):
        fm = frontmatter(p)
        tit = fm.get("titulo") or p.stem.replace("-", " ")
        aut = fm.get("autor") or ""
        out.append((tit, aut, str(p.relative_to(ROOT))))
    return out


def casar_acervo(titulo, autor, acervo):
    """True se a obra ja esta no acervo (titulo E autor batem)."""
    if not titulo:
        return False
    ct = chave_compacta(titulo)
    for t, a, _ in acervo:
        cta = chave_compacta(t)
        # o frontmatter as vezes grava "Autor Titulo" (titulo = "Contos",
        # autor = "Voltaire") — compara os dois conjuntos de tokens
        if ct and (ct == cta or ct in cta or cta in ct):
            if not autor:
                return True
            if not a:
                return True
            ca = chave_compacta(autor)
            if not ca or ca == chave_compacta(a):
                return True
            if ca in chave_compacta(a) or chave_compacta(a) in ca:
                return True
            # autor pode estar embutido no titulo ("Doyle A Volta...")
            if ca in cta or chave_compacta(a) in cta:
                return True
    return False


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry", action="store_true")
    args = ap.parse_args()

    import yaml
    cat = yaml.safe_load(CATALOGO.read_text(encoding="utf-8")).get("catalogo", [])
    slugs_canon = {}
    for it in cat:
        slugs_canon[slug(it.get("titulo") or "", it.get("autor") or "")] = it
    acervo = indexar_acervo()

    estado = {}
    if ESTADO.exists():
        try:
            estado = json.loads(ESTADO.read_text(encoding="utf-8"))
        except Exception:
            estado = {}

    antes = len(estado)
    novo = {}
    migradas = []
    nao_mapeadas = []

    # --- 1. mapeia cada chave antiga para a chave canonica ---
    for k, v in estado.items():
        destino = None
        if k in slugs_canon:
            destino = k
        else:
            melhor, ratio = None, 0.0
            for s in slugs_canon:
                r = similar(k, s)
                if r > ratio:
                    melhor, ratio = s, r
            if melhor and ratio >= 0.82:
                destino = melhor
        if destino is None:
            nao_mapeadas.append(k)
            novo[k] = v            # preserva o que nao deu para mapear
            continue
        if destino in novo:
            # conflito: "adquirido" ganha de "falhou"
            a, b = novo[destino], v
            if a.get("status") == "falhou" and b.get("status") == "adquirido":
                novo[destino] = b
                migradas.append((k, destino, "adquirido>falhou"))
            else:
                migradas.append((k, destino, "duplicado"))
        else:
            novo[destino] = v
            if destino != k:
                migradas.append((k, destino, "rekey"))

    # --- 2. o ACERVO manda: marca como adquirido o que ja esta no acervo ---
    marcados = []
    for s, it in slugs_canon.items():
        reg = novo.get(s)
        if reg and reg.get("status") == "adquirido":
            continue
        if casar_acervo(it.get("titulo") or "", it.get("autor") or "", acervo):
            novo[s] = {"status": "adquirido", "data": "2026-11-07",
                       "md": "acervo:", "kb": "ja-catalogado",
                       "orbit": "pulado", "origem": "migracao-acervo"}
            marcados.append((it.get("titulo"), it.get("autor")))

    # --- 3. resumo ---
    adq = sum(1 for v in novo.values() if v.get("status") == "adquirido")
    fal = sum(1 for v in novo.values() if v.get("status") == "falhou")
    print(f"estado: {antes} -> {len(novo)} chaves | adquiridos={adq} falhos={fal}")
    print(f"chaves rekeyadas/migradas: {len(migradas)}")
    for a, b, m in migradas[:40]:
        print(f"   {a}  ->  {b}   ({m})")
    if len(migradas) > 40:
        print(f"   ... e mais {len(migradas)-40}")
    print(f"\nnovos marcados como adquirido (ja estavam no acervo): {len(marcados)}")
    for t, a in marcados:
        print(f"   [OK] {t} — {a}")
    if nao_mapeadas:
        print(f"\nchaves sem correspondencia no catalogo (preservadas): "
              f"{len(nao_mapeadas)}")
        for k in nao_mapeadas:
            print(f"   ? {k} ({novo[k].get('status')})")

    if args.dry:
        return 0
    ESTADO.parent.mkdir(parents=True, exist_ok=True)
    ESTADO.write_text(json.dumps(novo, ensure_ascii=False, indent=1),
                       encoding="utf-8")
    print(f"\nestado gravado: {ESTADO}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
