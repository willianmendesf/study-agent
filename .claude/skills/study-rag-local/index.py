#!/usr/bin/env python3
"""
index.py — indexação semântica local de arquivos .md da biblioteca (ChromaDB persistente).

Existe pra evitar Read completo em livros grandes (alguns passam de 10 MB — ver CLAUDE.md
Regra 9 "trava de tamanho"). Quebra o arquivo em pedaços (por heading markdown, com fallback
por tamanho fixo + overlap pra blocos sem heading — comum em livro escaneado/OCR), gera
embeddings com sentence-transformers e guarda em data/rag/ com metadados de arquivo + linha,
pra permitir citar a fonte exata (Regra 9) sem carregar o arquivo inteiro no contexto.

Uso:
    python3 index.py <arquivo.md ou pasta>
    python3 index.py <arquivo.md ou pasta> --min-size-kb 150   # só indexa acima desse tamanho
    python3 index.py <arquivo.md ou pasta> --force              # reindexar mesmo se já indexado

Requer: bash setup.sh (chromadb + sentence-transformers) — ver SKILL.md.
"""
import argparse
import hashlib
import re
import sys
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parent
STUDY_AGENT_ROOT = SKILL_DIR.parents[2]
DATA_DIR = STUDY_AGENT_ROOT / "data"
RAG_DIR = DATA_DIR / "rag"
MODEL_NAME = "all-MiniLM-L6-v2"
COLLECTION = "biblioteca"


def chunk_markdown(text, max_chars=1500, overlap_chars=150):
    """Quebra por heading markdown primeiro; sub-quebra blocos ainda grandes por tamanho fixo
    com overlap (necessário pra texto de OCR sem heading nenhum). Retorna lista de
    (texto, linha_inicio, linha_fim), linhas 1-indexed."""
    lines = text.splitlines()
    if not lines:
        return []
    heading_idx = [i for i, l in enumerate(lines) if re.match(r"^#{1,6}\s", l)]
    if not heading_idx or heading_idx[0] != 0:
        heading_idx = [0] + heading_idx
    heading_idx.append(len(lines))

    blocks = []
    for i in range(len(heading_idx) - 1):
        start, end = heading_idx[i], heading_idx[i + 1]
        block_lines = lines[start:end]
        block_text = "\n".join(block_lines)
        if not block_text.strip():
            continue
        if len(block_text) <= max_chars:
            blocks.append((block_text, start + 1, end))
            continue
        pos = 0
        step = max(max_chars - overlap_chars, 1)
        while pos < len(block_text):
            sub = block_text[pos : pos + max_chars]
            l_start = start + block_text[:pos].count("\n") + 1
            l_end = start + block_text[: pos + len(sub)].count("\n") + 1
            blocks.append((sub, l_start, l_end))
            pos += step
    return blocks


def iter_targets(path, min_size_kb):
    p = Path(path)
    if p.is_file():
        yield p
        return
    for f in sorted(p.rglob("*.md")):
        if f.stat().st_size >= min_size_kb * 1024:
            yield f


def doc_id(rel_path, chunk_index):
    h = hashlib.sha1(f"{rel_path}::{chunk_index}".encode()).hexdigest()[:16]
    return f"{h}"


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("path", help="arquivo .md ou pasta (indexa recursivamente)")
    ap.add_argument("--min-size-kb", type=int, default=150, help="pula arquivos menores que isso (padrão 150KB)")
    ap.add_argument("--force", action="store_true", help="reindexa mesmo se o arquivo já tiver chunks indexados")
    args = ap.parse_args()

    try:
        import chromadb
        from sentence_transformers import SentenceTransformer
    except ImportError as e:
        sys.exit(f"Dependência faltando ({e}). Rode: bash {SKILL_DIR}/setup.sh")

    RAG_DIR.mkdir(parents=True, exist_ok=True)
    client = chromadb.PersistentClient(path=str(RAG_DIR))
    # sentence-transformers é calibrado pra similaridade de cosseno — o padrão do chromadb (L2)
    # rankeia errado. Força hnsw:space=cosine na criação da coleção.
    collection = client.get_or_create_collection(COLLECTION, metadata={"hnsw:space": "cosine"})
    model = SentenceTransformer(MODEL_NAME)

    targets = list(iter_targets(args.path, args.min_size_kb))
    if not targets:
        print(f"Nenhum arquivo .md >= {args.min_size_kb}KB encontrado em {args.path}")
        return

    total_chunks = 0
    for f in targets:
        rel = str(f.resolve().relative_to(STUDY_AGENT_ROOT))
        if not args.force:
            existing = collection.get(where={"arquivo": rel}, limit=1)
            if existing["ids"]:
                print(f"  já indexado, pulando (use --force pra reindexar): {rel}")
                continue

        text = f.read_text(encoding="utf-8", errors="ignore")
        chunks = chunk_markdown(text)
        if not chunks:
            continue

        titulo = f.stem
        ids, docs, metas = [], [], []
        for i, (chunk_text, l_start, l_end) in enumerate(chunks):
            ids.append(doc_id(rel, i))
            docs.append(chunk_text)
            metas.append({"arquivo": rel, "titulo": titulo, "chunk_index": i, "linha_inicio": l_start, "linha_fim": l_end})

        embeddings = model.encode(docs, show_progress_bar=False, batch_size=32).tolist()
        # upsert em lotes (chromadb tem limite de batch)
        BATCH = 500
        for i in range(0, len(ids), BATCH):
            collection.upsert(
                ids=ids[i : i + BATCH],
                documents=docs[i : i + BATCH],
                embeddings=embeddings[i : i + BATCH],
                metadatas=metas[i : i + BATCH],
            )
        total_chunks += len(ids)
        print(f"  ✅ {rel}: {len(ids)} chunks ({f.stat().st_size // 1024} KB)")

    print(f"\nTotal: {len(targets)} arquivo(s) processado(s), {total_chunks} chunks indexados em {RAG_DIR}")


if __name__ == "__main__":
    main()
