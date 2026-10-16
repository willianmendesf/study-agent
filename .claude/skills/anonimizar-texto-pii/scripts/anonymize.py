#!/usr/bin/env python3
import json
import logging
import os
import re
import sys
from pathlib import Path

BASE_DIR = Path(os.environ.get("ANON_HOME", str(Path.home() / ".local" / "share" / "anonimizador-dp")))
MODEL_DIR = Path(os.environ.get("ANON_MODEL", str(BASE_DIR / "model")))
TAG_PATTERN = re.compile(r"<\s*\|?\s*(\w+_\d+)\s*\|?\s*>")


def anonymize(text: str, extractor) -> dict:
    entities = sorted(
        extractor.extract_entities(text, return_type="label_position"),
        key=lambda e: e["start_position"],
    )
    counts, mapping, parts, cursor = {}, {}, [], 0
    for entity in entities:
        start, end = entity["start_position"], entity["end_position"]
        if start < cursor:
            continue
        counts[entity["label"]] = counts.get(entity["label"], 0) + 1
        tag = f"<|{entity['label']}_{counts[entity['label']]}|>"
        mapping[tag] = text[start:end]
        parts.append(text[cursor:start])
        parts.append(tag)
        cursor = end
    parts.append(text[cursor:])
    return {"text": "".join(parts), "map": mapping, "counts": counts}


def restore(text: str, mapping: dict) -> dict:
    ids = {tag[2:-2]: value for tag, value in mapping.items()}
    used = set()

    def swap(match):
        key = match.group(1)
        if key in ids:
            used.add(key)
            return ids[key]
        return match.group(0)

    final = TAG_PATTERN.sub(swap, text)
    return {
        "text": final,
        "unrestored": [f"<|{k}|>" for k in ids if k not in used],
        "stray": TAG_PATTERN.findall(final),
    }


def main() -> int:
    request = json.load(sys.stdin)
    mode = request.get("mode", "anonymize")
    if mode == "restore":
        json.dump(restore(request.get("text", ""), request.get("map", {})), sys.stdout)
        return 0
    if not MODEL_DIR.exists():
        json.dump({"error": "anonymizer model not installed; run scripts/install.sh"}, sys.stdout)
        return 2
    logging.getLogger("anonimizar").setLevel(logging.WARNING)
    from anonimizar import Anonimizar

    extractor = Anonimizar(model_path=str(MODEL_DIR))
    json.dump(anonymize(request.get("text", ""), extractor), sys.stdout)
    return 0


if __name__ == "__main__":
    sys.exit(main())
