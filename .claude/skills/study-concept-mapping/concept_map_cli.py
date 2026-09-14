#!/usr/bin/env python3
"""
concept_map_cli.py — CLI do study-concept-mapping.

Uso:
    python3 concept_map_cli.py <mapa.yaml> mermaid [--saida arquivo.md]
    python3 concept_map_cli.py <mapa.yaml> comunidades
    python3 concept_map_cli.py <mapa.yaml> resumo
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import concept_map as cm  # noqa: E402


def main(argv=None):
    ap = argparse.ArgumentParser(description="Gera/consulta um mapa conceitual (grafo de relações tipadas).")
    ap.add_argument("mapa", help="caminho do YAML do mapa de conceitos")
    sub = ap.add_subparsers(dest="comando", required=True)

    p_mermaid = sub.add_parser("mermaid", help="gera o diagrama Mermaid (texto)")
    p_mermaid.add_argument("--saida", help="grava em arquivo em vez de imprimir no stdout")

    sub.add_parser("comunidades", help="detecta clusters de conceitos (greedy modularity)")
    sub.add_parser("resumo", help="contagens + nó mais conectado + nº de comunidades")

    args = ap.parse_args(argv)

    try:
        g = cm.carregar_mapa(args.mapa)
    except (cm.MapaInvalido, FileNotFoundError, OSError) as e:
        sys.exit("erro: %s" % e)

    if args.comando == "mermaid":
        texto = cm.gerar_mermaid(g)
        if args.saida:
            with open(args.saida, "w", encoding="utf-8") as fh:
                fh.write("```mermaid\n%s\n```\n" % texto)
            print("gravado em %s" % args.saida)
        else:
            print(texto)
    elif args.comando == "comunidades":
        print(json.dumps(cm.detectar_comunidades(g), ensure_ascii=False, indent=2))
    elif args.comando == "resumo":
        print(json.dumps(cm.resumo(g), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
