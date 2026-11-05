#!/usr/bin/env python3
"""Corrigir a prova do William e dizer o que ele errou e COMO acertar.

DECISAO DO WILLIAM (2026-11-05):
  "sem gabarito no memos ele e' seu, voce corrige, a prova, e informa se errei e
   como acertar e etc"

O gabarito (resposta + "Por que" + "Onde reler") esta em
  data/estudos/exercicios/gabaritos/*.md
O resultado da prova esta em
  <pasta-do-quiz>/resultado.json   (gerado pelo study-quiz-serio)

Este script junta os dois e produz um relatorio de correcao:
  - nota
  - questoes erradas: o que voce marcou, o que era certo, POR QUE, ONDE RELER

Nao escreve nada no Memos.
"""
import argparse
import glob
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
GABDIR = ROOT / "data" / "estudos" / "exercicios" / "gabaritos"

LETRAS = "ABCDEFGH"


def parse_gabarito(path):
    """Le o .md do gabarito -> {n: {resposta, por_que, onde_reler}}."""
    texto = path.read_text(encoding="utf-8")
    blocos = re.split(r"^##\s*Q(\d+)\s*$", texto, flags=re.M)
    out = {}
    for i in range(1, len(blocos) - 1, 2):
        n = int(blocos[i])
        corpo = blocos[i + 1]
        # corta a secao da chave de referencia
        corpo = corpo.split("## Chave de referencia")[0]
        resp = por_que = onde = ""
        m = re.search(r"\*\*Resposta:\s*(.+?)\*\*", corpo)
        if m:
            resp = m.group(1).strip()
        # FORMATO B (medido): a justificativa vem NA MESMA LINHA da resposta
        #   "**B)** Abraão é o pai da fé, patriarca da aliança. Noé vem antes..."
        #   "Onde reler:** Gênesis 12-25."
        # Separa a letra da justificativa que vem depois.
        m = re.match(r"^\s*\*?\*?([A-Da-d])[)\.]\*?\*?\s*(.*)$", resp, re.S)
        if m:
            letra = m.group(1).upper()
            resto = m.group(2).strip()
            resp = f"{letra}) {resto}" if resto else f"{letra})"
            # se o resto for longo, ele E' a justificativa (o gabarito .md
            # nao separou "resposta" de "por que")
            if resto and len(resto) > 40 and not por_que:
                # separa: a resposta curta e o resto
                frases = re.split(r"(?<=[.!?])\s+", resto)
                resp = f"{letra}) {frases[0]}"
                por_que = " ".join(frases[1:]).strip()
        # "Por que/Por quê/Justificativa: <texto>"
        m = re.search(
            r"^(?:Por que|Por quê|Justificativa|Explicação)\s*:\s*(.+?)"
            r"(?=\n\s*\n|\n\s*Onde (?:reler|estudar|ver)|\n## |\Z)",
            corpo, re.S | re.M)
        if m:
            por_que = m.group(1).strip()
        # "Onde reler/estudar: <texto>" (pode estar em **...** ou solto)
        m = re.search(
            r"(?:\*\*)?\s*Onde (?:reler|estudar|ver)(?:\*\*)?\s*:\s*(.+?)(?=\n\s*\n|\n## |\Z)",
            corpo, re.S | re.M)
        if m:
            onde = m.group(1).strip().strip("*").strip()
        out[n] = {"resposta": resp, "por_que": por_que, "onde_reler": onde}
    return out


def achar_gabarito(titulo):
    """Encontra o .md do gabarito pelo titulo do quiz."""
    alvo = re.sub(r"[^0-9a-zà-ÿ]+", " ", titulo.lower()).strip()
    partes = [p for p in alvo.split() if len(p) > 2]
    melhor, score = None, 0
    for p in GABDIR.glob("*.md"):
        nome = re.sub(r"[^0-9a-zà-ÿ]+", " ", p.stem.lower()).strip()
        s = sum(1 for parte in partes if parte in nome)
        if s > score:
            melhor, score = p, s
    return melhor if score >= 2 else None


def achar_quiz_por_resultado(resultado_path):
    """resultado.json -> quiz.json irmao (mesma pasta)."""
    q = resultado_path.parent / "quiz.json"
    return q if q.exists() else None


def main():
    ap = argparse.ArgumentParser(description="Corrige a prova e diz como acertar")
    ap.add_argument("resultado", help="caminho do resultado.json")
    ap.add_argument("--gabarito", help="caminho do gabarito.md (opcional)")
    ap.add_argument("--json", action="store_true", help="saida em JSON")
    args = ap.parse_args()

    rp = Path(args.resultado)
    if not rp.exists():
        sys.exit(f"ERRO: nao achei {rp}")

    res = json.loads(rp.read_text(encoding="utf-8"))
    quiz = None
    qp = achar_quiz_por_resultado(rp)
    if qp:
        quiz = json.loads(qp.read_text(encoding="utf-8"))

    # gabarito
    gab_path = Path(args.gabarito) if args.gabarito else None
    if gab_path is None:
        titulo = res.get("titulo") or (quiz or {}).get("titulo") or rp.parent.name
        gab_path = achar_gabarito(titulo)
    gab = parse_gabarito(gab_path) if gab_path and gab_path.exists() else {}

    questoes = (quiz or {}).get("questoes") or []
    respostas = res.get("respostas") or []

    # as respostas do motor nao carregam o indice da questao explicitamente?
    # -> usa a ordem (o motor grava em ordem)
    erradas = []
    for i, r in enumerate(respostas):
        if r.get("acertou"):
            continue
        esc = r.get("alternativa_selecionada_idx")
        corr = r.get("correta_idx")
        q = questoes[i] if i < len(questoes) else {}
        gab_q = gab.get(i + 1, {})
        # gabarito do .md e a fonte da verdade da justificativa
        resp_texto = gab_q.get("resposta") or ""
        if not resp_texto and q:
            ci = q.get("correta")
            if isinstance(ci, int) and ci < len(q.get("alternativas") or []):
                resp_texto = f"{LETRAS[ci]}) {q['alternativas'][ci]}"
        erradas.append({
            "n": i + 1,
            "pergunta": (q.get("pergunta") or r.get("pergunta") or "").strip(),
            "voce_marcou": (f"{LETRAS[esc]}) {q['alternativas'][esc]}"
                            if isinstance(esc, int) and esc < len(q.get("alternativas") or [])
                            else (r.get("alternativa_escolhida") or "?")),
            "voce_marcou_idx": esc,
            "correta_idx": corr,
            "correta": resp_texto,
            "por_que": gab_q.get("por_que", ""),
            "onde_reler": gab_q.get("onde_reler", ""),
            "topico": r.get("topico") or q.get("topico") or "",
            "estudar": r.get("estudar") or q.get("estudar") or "",
        })

    saida = {
        "titulo": res.get("titulo") or (quiz or {}).get("titulo") or rp.parent.name,
        "nota": res.get("score_raw"),
        "total": res.get("score_max"),
        "pct": res.get("score_pct"),
        "duracao_seg": res.get("duracao_total_seg"),
        "gabarito": str(gab_path.relative_to(ROOT)) if gab_path else None,
        "erros": erradas,
        "pontos_fracos": res.get("pontos_fracos") or [],
    }

    if args.json:
        print(json.dumps(saida, ensure_ascii=False, indent=1))
        return

    print(f"# Correcao — {saida['titulo']}")
    print()
    print(f"**Nota: {saida['nota']}/{saida['total']} ({saida['pct']}%)**")
    if saida["duracao_seg"]:
        mm, ss = divmod(int(saida["duracao_seg"]), 60)
        print(f"**Tempo: {mm}min {ss:02d}s**")
    print()
    if not erradas:
        print("**Nota cheia — zero erros.** Nada a corrigir.")
        return
    print(f"## {len(erradas)} erro(s) — o que errou e como acertar")
    print()
    for e in erradas:
        print(f"### Q{e['n']}" + (f" — {e['topico']}" if e["topico"] else ""))
        if e["pergunta"]:
            print(f"> {e['pergunta']}")
            print()
        print(f"**Você marcou:** {e['voce_marcou']}")
        print(f"**Resposta correta:** {e['correta'] or '—'}")
        print()
        if e["por_que"]:
            print(f"**Por quê:** {e['por_que']}")
            print()
        if e["onde_reler"]:
            print(f"**Onde reler:** {e['onde_reler']}")
            print()
        if e["estudar"]:
            print(f"**Estudar:** {e['estudar']}")
            print()


if __name__ == "__main__":
    main()
