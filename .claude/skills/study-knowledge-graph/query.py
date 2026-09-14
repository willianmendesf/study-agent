#!/usr/bin/env python3
"""
query.py — CLI do study-knowledge-graph. Consulta uma ontologia YAML via graph_tools (networkx).

Uso:
    python3 query.py <ontologia.yaml> caminho <conceito>
    python3 query.py <ontologia.yaml> gaps <conceito> [--aprendidos "A,B,C"]
    python3 query.py <ontologia.yaml> dificuldade <conceito> [--aprendidos "A,B,C"]
    python3 query.py <ontologia.yaml> listar

Sem --aprendidos, usa o campo `progresso.aprendidos` do próprio YAML (se existir).
Saída em JSON (fácil de a IA ler e transformar em texto pro usuário).
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import graph_tools as gt  # noqa: E402


def main(argv=None):
    ap = argparse.ArgumentParser(description="Consulta uma ontologia pedagógica (grafo de pré-requisitos).")
    ap.add_argument("ontologia", help="caminho do YAML da ontologia")
    sub = ap.add_subparsers(dest="comando", required=True)

    p_caminho = sub.add_parser("caminho", help="ordem de estudo até o conceito")
    p_caminho.add_argument("conceito")

    p_gaps = sub.add_parser("gaps", help="pré-requisitos ainda faltando para o conceito")
    p_gaps.add_argument("conceito")
    p_gaps.add_argument("--aprendidos", help="lista separada por vírgula (sobrescreve o YAML)")

    p_dif = sub.add_parser("dificuldade", help="dificuldade efetiva do conceito")
    p_dif.add_argument("conceito")
    p_dif.add_argument("--aprendidos", help="lista separada por vírgula (sobrescreve o YAML)")

    sub.add_parser("listar", help="lista todos os conceitos em ordem topológica")

    args = ap.parse_args(argv)

    try:
        g = gt.carregar_ontologia(args.ontologia)
    except (gt.OntologiaInvalida, FileNotFoundError, OSError) as e:
        sys.exit("erro: %s" % e)

    aprendidos = None
    if getattr(args, "aprendidos", None):
        aprendidos = [c.strip() for c in args.aprendidos.split(",") if c.strip()]

    try:
        if args.comando == "caminho":
            resultado = gt.caminho_para(g, args.conceito)
        elif args.comando == "gaps":
            resultado = gt.gaps(g, args.conceito, aprendidos)
        elif args.comando == "dificuldade":
            resultado = gt.dificuldade_efetiva(g, args.conceito, aprendidos)
        elif args.comando == "listar":
            resultado = gt.listar_conceitos(g)
    except gt.OntologiaInvalida as e:
        sys.exit("erro: %s" % e)

    print(json.dumps(resultado, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
