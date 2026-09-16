#!/usr/bin/env python3
"""
server.py — runtime local do plugin study-flashcards. Só stdlib (nada de pip, nada de banco).

Motor de flashcard SIMPLES — frente/verso, auto-avaliação ("Lembrei"/"Não lembrei"), sem nota,
sem retry por card. Diferente do study-h5p (H5P.Dialogcards, feedback imediato + retry ilimitado),
aqui o fluxo é sequencial (sem voltar), mesma simplicidade do study-quiz-serio — mas sem a
justificativa de "nota real" dele: é só a etapa de prática antes do quiz do módulo.

Fluxo contínuo (opcional): se --proximo-tipo/--proximo-dir forem passados e o quiz.json do
--proximo-dir já existir, ao finalizar este mini-app ele sobe o study-quiz-serio numa porta livre
e devolve "proximo_url" — o player redireciona na hora, sem passar pelo chat.

Uso:
    python3 server.py <pasta-com-flashcards.json> [--port 8000] [--grace 90]
        [--proximo-tipo quiz --proximo-dir <pasta-do-quiz> --proximo-titulo "..."]

A pasta deve conter um flashcards.json (ver SKILL.md para o schema).
"""
import argparse
import datetime
import json
import os
import socket
import subprocess
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

SKILL_DIR = os.path.dirname(os.path.abspath(__file__))
PLAYER_HTML = os.path.join(SKILL_DIR, "player", "index.html")
QUIZ_SERIO_SERVER = os.path.normpath(os.path.join(SKILL_DIR, "..", "study-quiz-serio", "server.py"))


def _stamp():
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _porta_livre():
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


def _aguardar_porta_aberta(host, port, tentativas=20, intervalo=0.1):
    for _ in range(tentativas):
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(intervalo)
        try:
            s.connect((host, port))
            return True
        except OSError:
            time.sleep(intervalo)
        finally:
            s.close()
    return False


def _iniciar_quiz_auto(quiz_dir_abs):
    porta = _porta_livre()
    subprocess.Popen(
        [sys.executable, QUIZ_SERIO_SERVER, quiz_dir_abs, "--port", str(porta), "--grace", "90"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
    )
    _aguardar_porta_aberta("127.0.0.1", porta)
    return "http://127.0.0.1:%d/" % porta


def _gerar_relatorio_md(flashcards, resultado):
    linhas = []
    linhas.append("# Relatório — %s" % flashcards.get("titulo", "Flashcards"))
    linhas.append("")
    linhas.append(
        "**Matéria:** %s · **Tema:** %s"
        % (flashcards.get("materia", "—"), flashcards.get("tema", "—"))
    )
    linhas.append(
        "**Lembrou:** %s/%s · **Concluído em:** %s"
        % (resultado["lembrou_raw"], resultado["lembrou_max"], resultado["finalizado_em"])
    )
    linhas.append("")

    fracos = resultado.get("pontos_fracos") or []
    if fracos:
        linhas.append("## Cards a revisar")
        linhas.append("")
        for pf in fracos:
            linhas.append("### %s — %d/%d não lembrados" % (pf["topico"], pf["erros"], pf["total"]))
            linhas.append("")
    else:
        linhas.append("## Cards a revisar")
        linhas.append("Nenhum — lembrou de todos. 🎉")
        linhas.append("")
    return "\n".join(linhas)


class Handler(BaseHTTPRequestHandler):
    session_dir = None  # set in main()
    flashcards = None  # conteudo de flashcards.json, carregado uma vez em main()
    grace_seg = 90
    proximo = None  # dict {tipo, dir, titulo} ou None
    httpd = None  # set in main(), usado pro self-shutdown

    def log_message(self, fmt, *args):
        sys.stderr.write("  %s\n" % (fmt % args))

    def _send_json(self, status, payload):
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _send_file(self, full, mime):
        try:
            with open(full, "rb") as fh:
                data = fh.read()
        except OSError:
            self.send_error(500, "read error")
            return
        self.send_response(200)
        self.send_header("Content-Type", mime)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    # --- GET: player + flashcards.json ---------------------------------
    def do_GET(self):
        path = self.path.split("?", 1)[0]
        if path in ("", "/", "/index.html"):
            self._send_file(PLAYER_HTML, "text/html; charset=utf-8")
            return
        if path == "/flashcards.json":
            self._send_json(200, self.flashcards)
            return
        self.send_error(404, "not found")

    # --- POST /finalizar: grava resultado + agenda self-shutdown -------
    def do_POST(self):
        if self.path.split("?")[0] != "/finalizar":
            self.send_error(404, "not found")
            return
        length = int(self.headers.get("Content-Length", 0) or 0)
        raw = self.rfile.read(length) if length else b""
        try:
            payload = json.loads(raw.decode("utf-8"))
        except (ValueError, UnicodeDecodeError):
            self.send_error(400, "invalid json")
            return

        stamp = _stamp()
        respostas = payload.get("respostas") or []
        lembrou_raw = sum(1 for r in respostas if r.get("lembrou"))
        lembrou_max = len(respostas)

        por_topico = {}
        for r in respostas:
            topico = r.get("topico") or "Geral"
            slot = por_topico.setdefault(topico, {"erros": 0, "total": 0})
            slot["total"] += 1
            if not r.get("lembrou"):
                slot["erros"] += 1

        pontos_fracos = [
            {"topico": t, "erros": s["erros"], "total": s["total"]}
            for t, s in por_topico.items()
            if s["erros"] > 0
        ]
        pontos_fracos.sort(key=lambda p: (p["erros"] / p["total"]), reverse=True)
        topicos_dominados = sorted(t for t, s in por_topico.items() if s["erros"] == 0)

        resultado = {
            "atualizado_em": stamp,
            "titulo": self.flashcards.get("titulo"),
            "materia": self.flashcards.get("materia"),
            "tema": self.flashcards.get("tema"),
            "iniciado_em": payload.get("iniciado_em"),
            "finalizado_em": payload.get("finalizado_em") or stamp,
            "duracao_total_seg": payload.get("duracao_total_seg", 0),
            "lembrou_raw": lembrou_raw,
            "lembrou_max": lembrou_max,
            "respostas": respostas,
            "pontos_fracos": pontos_fracos,
            "topicos_dominados": topicos_dominados,
        }

        with open(os.path.join(self.session_dir, "resultado.json"), "w", encoding="utf-8") as fh:
            json.dump(resultado, fh, ensure_ascii=False, indent=2)
        with open(os.path.join(self.session_dir, "resultado.jsonl"), "a", encoding="utf-8") as fh:
            fh.write(json.dumps({"recebido_em": stamp, "resultado": resultado}, ensure_ascii=False) + "\n")
        with open(os.path.join(self.session_dir, "relatorio.md"), "w", encoding="utf-8") as fh:
            fh.write(_gerar_relatorio_md(self.flashcards, resultado))

        resposta = {"ok": True, "resultado": resultado}
        proximo_url = None
        if self.proximo and self.proximo.get("tipo") == "quiz":
            quiz_dir_abs = self.proximo["dir"]
            if os.path.isfile(os.path.join(quiz_dir_abs, "quiz.json")):
                proximo_url = _iniciar_quiz_auto(quiz_dir_abs)
                resposta["proximo_url"] = proximo_url

        if proximo_url is None:
            resposta["encerra_em_seg"] = self.grace_seg

        self._send_json(200, resposta)

        print(
            "  resultado salvo (%d/%d lembrados)%s"
            % (lembrou_raw, lembrou_max, " — abrindo proximo app" if proximo_url else " — servidor encerra em %ds" % self.grace_seg),
            file=sys.stderr,
        )

        def _shutdown():
            sys.stderr.write("  encerrando automaticamente (resultado ja salvo em disco).\n")
            if self.httpd is not None:
                self.httpd.shutdown()

        threading.Timer(self.grace_seg, _shutdown).start()


def main(argv=None):
    ap = argparse.ArgumentParser(description="Runtime local do plugin study-flashcards (stdlib only).")
    ap.add_argument("session_dir", help="pasta com flashcards.json")
    ap.add_argument("--port", type=int, default=8000)
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--grace", type=int, default=90, help="segundos de espera apos finalizar antes do self-shutdown")
    ap.add_argument("--proximo-tipo", choices=["quiz"], default=None,
                     help="app pra abrir automaticamente ao finalizar (fluxo continuo)")
    ap.add_argument("--proximo-dir", default=None)
    ap.add_argument("--proximo-titulo", default=None)
    args = ap.parse_args(argv)

    sess = os.path.abspath(args.session_dir)
    flashcards_path = os.path.join(sess, "flashcards.json")
    if not os.path.isfile(flashcards_path):
        sys.exit("erro: %s nao contem flashcards.json — gere os cards primeiro (ver SKILL.md)" % sess)
    with open(flashcards_path, "r", encoding="utf-8") as fh:
        flashcards = json.load(fh)
    if not flashcards.get("cards"):
        sys.exit("erro: flashcards.json sem campo 'cards'")

    proximo = None
    if args.proximo_tipo:
        if not args.proximo_dir:
            sys.exit("erro: --proximo-tipo exige --proximo-dir")
        proximo = {
            "tipo": args.proximo_tipo,
            "dir": os.path.abspath(args.proximo_dir),
            "titulo": args.proximo_titulo,
        }

    Handler.session_dir = sess
    Handler.flashcards = flashcards
    Handler.grace_seg = args.grace
    Handler.proximo = proximo
    httpd = ThreadingHTTPServer((args.host, args.port), Handler)
    Handler.httpd = httpd
    url = "http://%s:%d/" % (args.host, args.port)
    print("study-flashcards rodando: %s" % url)
    print("  sessao: %s" % sess)
    print("  ao finalizar: resultado.json + relatorio.md salvos" +
          (", proximo app sobe automatico" if proximo else ", servidor cai sozinho ~%ds depois" % args.grace))
    print("  Ctrl+C para parar manualmente antes disso.")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nparado.")
    httpd.server_close()
    print("study-flashcards encerrado.")


if __name__ == "__main__":
    main()
