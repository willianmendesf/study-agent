#!/usr/bin/env python3
"""Semeia `pipeline-estado.json` a partir da KB de literatura (fonte de verdade).

POR QUE (2026-11-05, bug 4 da rodada de ficcao):
  O `pipeline-aquisicao.py` guarda o que ja foi tentado/adquirido em
  `data/perfil/bibliotecario/pipeline-estado.json`. Esse arquivo foi criado
  HOJE, depois do lote noturno de 30 ebook (que rodou pelo
  `finalizar-rampa.py`, um caminho diferente). Resultado: o estado estava
  VAZIO e o pipeline ia RE-BAIXAR 30 livros que ja estao no acervo e na KB
  — queimando cota do z-library (40/dia) e criando duplicatas.

  Este script le a KB (`data/biblioteca/global/kb-literatura.yaml`), que e' a
  fonte de verdade do acervo, e marca no estado todos os itens do catalogo
  que JA estao catalogados. E' idempotente.

USO:
  python3 scripts/semear-estado-pipeline.py            # semeia e mostra o resumo
  python3 scripts/semear-estado-pipeline.py --dry      # so mostra o que faria
  python3 scripts/semear-estado-pipeline.py --forcar    # sobrescreve status
                                                      # "adquirido" tambem p/ os
                                                      # marcados como falha
"""
import argparse
import json
import re
import sys
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
KB = ROOT / "data" / "biblioteca" / "global" / "kb-literatura.yaml"
CATALOGO = ROOT / "data" / "perfil" / "bibliotecario" / "catalogo-ficcao.yaml"
ESTADO = ROOT / "data" / "perfil" / "bibliotecario" / "pipeline-estado.json"

STOP = {"o", "a", "os", "as", "de", "do", "da", "dos", "das", "e", "em", "no",
        "na", "um", "uma", "para", "com", "que", "se", "por", "ao", "the",
        "of", "and", "ou", "nao", "mais"}


def norm(s: str) -> str:
    s = "".join(c for c in unicodedata.normalize("NFKD", s or "")
                if not unicodedata.combining(c)).lower()
    s = re.sub(r"[^\w\s]", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def toks(s: str) -> set:
    return {t for t in re.findall(r"[a-z0-9]+", norm(s))
            if t not in STOP and len(t) > 2}


def slug(titulo, autor):
    s = unicodedata.normalize("NFKD", f"{titulo} - {autor}")
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = s.replace("—", "-").replace("–", "-")
    s = re.sub(r"[^\w\s-]", "", s)
    s = re.sub(r"[\s_]+", "-", s)
    s = re.sub(r"-{2,}", "-", s).strip("-")
    return s[:70].strip("-")


def kb_entradas():
    """(titulo, caminho_md) de cada material da KB de literatura.

    USA O PARSER YAML (nao regex): a KB tem entradas sem `caminho_md`
    (ex.: 'O Demônio da Teoria' usa `fonte:`) e o parser pega TODAS, sem
    depender da adjacencia das linhas. A versao por regex (2026-11-05) parava
    em 34 de 39 entradas.
    """
    if not KB.exists():
        return []
    try:
        import yaml
        d = yaml.safe_load(KB.read_text(encoding="utf-8")) or {}
    except Exception:
        return []
    materiais = (d.get("knowledge_base_literatura") or {}).get("materiais") or []
    out = []
    for m in materiais:
        if not isinstance(m, dict):
            continue
        tit = str(m.get("titulo") or "").strip()
        cam = str(m.get("caminho_md") or "").strip()
        if tit:
            out.append((tit, cam))
    return out


def acervo_candidatos():
    """Todos os sinais de 'ja existe no acervo':
       (a) os .md da pasta literatura-mundial-classica (nome do arquivo)
       (b) as entradas da KB de literatura (titulo)
    """
    cands = []
    base = ROOT / "data" / "biblioteca" / "literatura-mundial-classica"
    if base.exists():
        for p in base.rglob("*.md"):
            cands.append((p.stem.replace("-", " "), f"acervo:{p.relative_to(ROOT)}"))
    for tit, cam in kb_entradas():
        if cam:
            cands.append((tit, cam))
    return cands


def casa(cand_titulo, item_titulo, cand_extra, item_autor):
    """True se o candidato do acervo e' a MESMA obra do item do catalogo.

    Criterio (calibrado contra os casos reais):
      - TITULO: pelo menos 75% dos tokens distintivos do titulo do catalogo
        aparecem no texto do candidato. Tokens > 2 letras, sem stopwords.
        ("Dom Quixote" -> {dom, quixote} casa com 'Cervantes-Dom-Quixote').
      - AUTOR: pelo menos 50% dos tokens do autor batem. Aceita o sobrenome
        ('Miguel de Cervantes' casa pelo token 'cervantes'), porque a KB e o
        nome do arquivo grafam o autor de formas diferentes.
    """
    ct = toks(cand_titulo)
    it = toks(item_titulo)
    if not it:
        return False
    cobertura = len(it & ct) / len(it)
    if cobertura < 0.75:
        return False
    ia = toks(item_autor)
    if ia:
        ka = toks(cand_extra) | ct
        if len(ia & ka) / len(ia) < 0.5:
            return False
    return True


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry", action="store_true")
    ap.add_argument("--forcar", action="store_true",
                    help="marca como adquirido mesmo o que ja estava como falha")
    args = ap.parse_args()

    import yaml
    cat = yaml.safe_load(CATALOGO.read_text(encoding="utf-8")).get("catalogo", [])
    kb = kb_entradas()
    cands = acervo_candidatos()
    print(f"catalogo: {len(cat)} itens · KB: {len(kb)} materiais · "
          f"candidatos no acervo: {len(cands)}")

    estado = {}
    if ESTADO.exists():
        try:
            estado = json.loads(ESTADO.read_text(encoding="utf-8"))
        except Exception:
            estado = {}
    antes_n = len(estado)

    marcados = []
    for it in cat:
        tit = it.get("titulo") or ""
        aut = it.get("autor") or ""
        s = slug(tit, aut)
        if estado.get(s, {}).get("status") == "adquirido" and not args.forcar:
            continue
        achou = None
        for ct, cam in cands:
            if casa(ct, tit, cam, aut):
                achou = cam
                break
        if achou:
            estado[s] = {"status": "adquirido", "data": "2026-11-05",
                         "md": achou, "kb": "ja-catalogado", "orbit": "ok",
                         "origem": "semente-acervo"}
            marcados.append((tit, aut, achou))

    print(f"\n{len(marcados)} item(ns) do catalogo marcados como JA ADQUIRIDO "
          f"(estado: {antes_n} -> {len(estado)} entradas)")
    for t, a, p in marcados:
        print(f"  [OK] {t} — {a}\n        {p}")

    pend = [it for it in cat
            if estado.get(slug(it.get("titulo") or "", it.get("autor") or ""),
                          {}).get("status") != "adquirido"]
    print(f"\npendentes reais: {len(pend)} de {len(cat)}")

    if args.dry:
        return 0

    ESTADO.parent.mkdir(parents=True, exist_ok=True)
    ESTADO.write_text(json.dumps(estado, ensure_ascii=False, indent=1),
                       encoding="utf-8")
    print(f"\nestado gravado: {ESTADO}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
