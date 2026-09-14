#!/usr/bin/env python3
"""
search.py — busca semântica no índice gerado por index.py (data/rag/).

Uso:
    python3 search.py "pergunta em linguagem natural" [--top-k 5] [--arquivo <caminho-relativo>]

Devolve, por resultado: arquivo, faixa de linha, distância (menor = mais similar), e o trecho —
o suficiente pra citar a fonte (Regra 9) e, se precisar de mais contexto, fazer um Read pontual
com esse offset/linha em vez do arquivo inteiro.
"""
import argparse
import json
import sys
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parent
STUDY_AGENT_ROOT = SKILL_DIR.parents[2]
RAG_DIR = STUDY_AGENT_ROOT / "data" / "rag"
MODEL_NAME = "all-MiniLM-L6-v2"
COLLECTION = "biblioteca"


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("query")
    ap.add_argument("--top-k", type=int, default=5)
    ap.add_argument("--arquivo", help="filtra por caminho relativo exato de um arquivo já indexado")
    ap.add_argument("--json", action="store_true", help="saída em JSON (pra uso programático)")
    args = ap.parse_args()

    try:
        import chromadb
        from sentence_transformers import SentenceTransformer
    except ImportError as e:
        sys.exit(f"Dependência faltando ({e}). Rode: bash {SKILL_DIR}/setup.sh")

    if not RAG_DIR.exists():
        sys.exit(f"{RAG_DIR} não existe ainda — rode index.py primeiro.")

    client = chromadb.PersistentClient(path=str(RAG_DIR))
    try:
        collection = client.get_collection(COLLECTION)
    except Exception:
        sys.exit(f"Coleção '{COLLECTION}' não existe ainda — rode index.py primeiro.")

    model = SentenceTransformer(MODEL_NAME)
    embedding = model.encode([args.query]).tolist()

    where = {"arquivo": args.arquivo} if args.arquivo else None
    result = collection.query(query_embeddings=embedding, n_results=args.top_k, where=where)

    hits = []
    ids = result.get("ids", [[]])[0]
    docs = result.get("documents", [[]])[0]
    metas = result.get("metadatas", [[]])[0]
    dists = result.get("distances", [[]])[0]
    for doc, meta, dist in zip(docs, metas, dists):
        hits.append(
            {
                "arquivo": meta["arquivo"],
                "titulo": meta.get("titulo"),
                "linha_inicio": meta["linha_inicio"],
                "linha_fim": meta["linha_fim"],
                "distancia": round(dist, 4),
                "trecho": doc,
            }
        )

    if args.json:
        print(json.dumps(hits, ensure_ascii=False, indent=2))
        return

    if not hits:
        print("Nada encontrado.")
        return

    for i, h in enumerate(hits, 1):
        print(f"--- resultado {i} (distância {h['distancia']}) ---")
        print(f"Fonte: {h['arquivo']}, linhas {h['linha_inicio']}-{h['linha_fim']}")
        trecho = h["trecho"][:600]
        print(trecho + ("..." if len(h["trecho"]) > 600 else ""))
        print()


if __name__ == "__main__":
    main()
