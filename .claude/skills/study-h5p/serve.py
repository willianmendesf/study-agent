#!/usr/bin/env python3
"""
serve.py — runtime local do plugin study-h5p. Só stdlib (nada de pip, nada de banco).

Serve UMA pasta de exercício (h5p.json + content/) + os assets vendorizados do plugin
(player h5p-standalone + bibliotecas H5P), e grava o resultado que o player manda por xAPI.

Uso:
    python3 serve.py <pasta-do-exercicio> [--port 8000]

O player abre em http://localhost:<port>/ . Ao terminar a atividade, o navegador faz
POST /resultado com a statement xAPI; cada uma é anexada a <pasta>/resultado.jsonl e a
última com score vira <pasta>/resultado.json (resumo que o Orquestrador lê depois).
"""
import argparse
import json
import os
import sys
import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

SKILL_DIR = os.path.dirname(os.path.abspath(__file__))
VENDOR_DIR = os.path.join(SKILL_DIR, "vendor")

MIME = {
    ".html": "text/html; charset=utf-8", ".js": "text/javascript; charset=utf-8",
    ".mjs": "text/javascript; charset=utf-8", ".css": "text/css; charset=utf-8",
    ".json": "application/json; charset=utf-8", ".svg": "image/svg+xml",
    ".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
    ".gif": "image/gif", ".webp": "image/webp", ".woff": "font/woff",
    ".woff2": "font/woff2", ".ttf": "font/ttf", ".eot": "application/vnd.ms-fontobject",
    ".mp4": "video/mp4", ".webm": "video/webm", ".mp3": "audio/mpeg", ".m4a": "audio/mp4",
    ".txt": "text/plain; charset=utf-8", ".xml": "text/xml", ".vtt": "text/vtt",
}


def guess_mime(path):
    return MIME.get(os.path.splitext(path)[1].lower(), "application/octet-stream")


class Handler(BaseHTTPRequestHandler):
    exercise_dir = None  # set in main()

    def log_message(self, fmt, *args):
        sys.stderr.write("  %s\n" % (fmt % args))

    # --- static serving -----------------------------------------------------
    def _resolve(self, url_path):
        """Map a URL path to a file on disk. /vendor/* -> plugin assets; rest -> exercise dir."""
        clean = url_path.split("?", 1)[0].split("#", 1)[0].lstrip("/")
        if clean in ("", "index.html"):
            return os.path.join(SKILL_DIR, "player", "index.html")
        if clean.startswith("vendor/"):
            base, rel = VENDOR_DIR, clean[len("vendor/"):]
        else:
            base, rel = self.exercise_dir, clean
        full = os.path.normpath(os.path.join(base, rel))
        if full != base and not full.startswith(os.path.normpath(base) + os.sep):
            return None  # path traversal guard
        return full

    def do_GET(self):
        full = self._resolve(self.path)
        if not full or not os.path.isfile(full):
            self.send_error(404, "not found")
            return
        try:
            with open(full, "rb") as fh:
                data = fh.read()
        except OSError:
            self.send_error(500, "read error")
            return
        self.send_response(200)
        self.send_header("Content-Type", guess_mime(full))
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    # --- result capture ---------------------------------------------------
    def do_POST(self):
        if self.path.split("?")[0] != "/resultado":
            self.send_error(404, "not found")
            return
        length = int(self.headers.get("Content-Length", 0) or 0)
        raw = self.rfile.read(length) if length else b""
        try:
            statement = json.loads(raw.decode("utf-8"))
        except (ValueError, UnicodeDecodeError):
            self.send_error(400, "invalid json")
            return

        stamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        record = {"recebido_em": stamp, "statement": statement}
        with open(os.path.join(self.exercise_dir, "resultado.jsonl"), "a", encoding="utf-8") as fh:
            fh.write(json.dumps(record, ensure_ascii=False) + "\n")

        # Se a statement traz score/conclusão, grava/atualiza o resumo legível.
        result = statement.get("result", {}) if isinstance(statement, dict) else {}
        score = result.get("score", {}) if isinstance(result, dict) else {}
        if "raw" in score or result.get("completion"):
            verb = (statement.get("verb", {}) or {}).get("display", {})
            summary = {
                "atualizado_em": stamp,
                "verbo": next(iter(verb.values()), None) if isinstance(verb, dict) else None,
                "score_raw": score.get("raw"),
                "score_max": score.get("max"),
                "score_scaled": score.get("scaled"),
                "sucesso": result.get("success"),
                "completou": result.get("completion"),
                "duracao": result.get("duration"),
                "objeto": (statement.get("object", {}) or {}).get("id"),
                "respostas": result.get("response"),
            }
            with open(os.path.join(self.exercise_dir, "resultado.json"), "w", encoding="utf-8") as fh:
                json.dump(summary, fh, ensure_ascii=False, indent=2)

        self.send_response(204)
        self.send_header("Cache-Control", "no-store")
        self.end_headers()


def main(argv=None):
    ap = argparse.ArgumentParser(description="Runtime local do plugin study-h5p (stdlib only).")
    ap.add_argument("exercise_dir", help="pasta do exercício (contém h5p.json e content/)")
    ap.add_argument("--port", type=int, default=8000)
    ap.add_argument("--host", default="127.0.0.1")
    args = ap.parse_args(argv)

    ex = os.path.abspath(args.exercise_dir)
    if not os.path.isfile(os.path.join(ex, "h5p.json")):
        sys.exit("erro: %s nao contem h5p.json — gere o exercicio primeiro (ver SKILL.md)" % ex)
    if not os.path.isdir(os.path.join(VENDOR_DIR, "libraries")):
        sys.exit("erro: assets do plugin ausentes em %s — repo incompleto" % VENDOR_DIR)

    Handler.exercise_dir = ex
    httpd = ThreadingHTTPServer((args.host, args.port), Handler)
    url = "http://%s:%d/" % (args.host, args.port)
    print("study-h5p rodando: %s" % url)
    print("  exercicio: %s" % ex)
    print("  resultado: %s/resultado.json (gravado quando voce terminar a atividade)" % ex)
    print("  Ctrl+C para parar.")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nparado.")
        httpd.server_close()


if __name__ == "__main__":
    main()
