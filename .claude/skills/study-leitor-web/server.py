#!/usr/bin/env python3
"""
server.py — runtime local do plugin study-leitor-web. Só stdlib (nada de pip, nada de banco).

Diferente do study-quiz-serio/study-h5p (que se auto-encerram num grace fixo depois de um evento
de "fim" — Finalizar/POST resultado), uma sessao de leitura nao tem fim garantido: o aluno pode
fechar a aba a qualquer momento. Por isso o self-shutdown aqui e por OCIOSIDADE:

  - o navegador manda POST /heartbeat a cada ~25s, so quando a aba esta visivel
  - uma thread separada verifica a cada ~30s se passou --idle segundos sem atividade
  - se sim, o servidor se encerra sozinho (nada fica pendurado em background)
  - POST /encerrar (botao "Terminar sessao") encerra na hora, sem esperar a ociosidade
  - todo evento (progresso, destaque, nota, pedido) grava em disco no MOMENTO em que acontece —
    nao ha um POST final garantido como o /finalizar do quiz-serio

Este arquivo duplica de proposito o boilerplate de servidor local ja usado em
study-quiz-serio/server.py e study-h5p/serve.py (ThreadingHTTPServer, bind so 127.0.0.1,
stdlib-only). So 2 skills faziam isso ate agora — nao vale a pena extrair um nucleo
compartilhado ainda (YAGNI); revisitar se uma 4a skill baseada em servidor local aparecer.

Uso:
    python3 server.py <pasta-da-sessao> [--port 8000] [--idle 600]

A pasta da sessao deve conter um conteudo.json (ver SKILL.md para o schema, 3 formatos:
markdown / epub / pdf).
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
VENDOR_DIR = os.path.join(SKILL_DIR, "vendor")
QUIZ_SERIO_SERVER = os.path.normpath(
    os.path.join(SKILL_DIR, "..", "study-quiz-serio", "server.py")
)
FLASHCARDS_SERVER = os.path.normpath(
    os.path.join(SKILL_DIR, "..", "study-flashcards", "server.py")
)

MIME_BY_EXT = {
    ".js": "application/javascript; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".map": "application/json; charset=utf-8",
    ".html": "text/html; charset=utf-8",
}

ARQUIVO_MIME_BY_FORMATO = {
    "epub": "application/epub+zip",
    "pdf": "application/pdf",
}


def _stamp():
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _progresso_inicial(conteudo, fila=False):
    prog = {
        "atualizado_em": _stamp(),
        "titulo": conteudo.get("titulo"),
        "materia": conteudo.get("materia"),
        "tema": conteudo.get("tema"),
        "formato": conteudo.get("formato", "markdown"),
        "local_atual": None,
        "percentual_lido": 0.0,
        "destaques": [],
        "notas": [],
        "pedidos_pendentes": [],
    }
    if fila:
        prog["fila"] = True
        prog["item_atual"] = 0
    return prog


def _carregar_item_da_fila(session_dir, fila, indice):
    item = fila["itens"][indice]
    path = os.path.join(session_dir, item["conteudo"])
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)


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
    """Sobe o study-quiz-serio numa porta livre, sem bloquear o processo atual.

    Fluxo contínuo pedido pelo usuário: ao terminar a fila, o proximo app ja abre sozinho —
    sem passar por um "peça no chat" intermediário (ver SKILL.md).
    """
    porta = _porta_livre()
    subprocess.Popen(
        [sys.executable, QUIZ_SERIO_SERVER, quiz_dir_abs, "--port", str(porta), "--grace", "90"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
    )
    _aguardar_porta_aberta("127.0.0.1", porta)
    return "http://127.0.0.1:%d/" % porta


def _iniciar_flashcards_auto(flashcards_dir_abs, quiz_dir_abs, quiz_titulo):
    """Sobe o study-flashcards numa porta livre; encadeia pro quiz se ele ja existir.

    Mesmo racional do _iniciar_quiz_auto: fluxo continuo, sem handoff via chat.
    """
    porta = _porta_livre()
    cmd = [sys.executable, FLASHCARDS_SERVER, flashcards_dir_abs, "--port", str(porta), "--grace", "90"]
    if quiz_dir_abs and os.path.isfile(os.path.join(quiz_dir_abs, "quiz.json")):
        cmd += ["--proximo-tipo", "quiz", "--proximo-dir", quiz_dir_abs]
        if quiz_titulo:
            cmd += ["--proximo-titulo", quiz_titulo]
    subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
    _aguardar_porta_aberta("127.0.0.1", porta)
    return "http://127.0.0.1:%d/" % porta


class Handler(BaseHTTPRequestHandler):
    session_dir = None  # set in main()
    conteudo = None  # conteudo do item atual (modo single: fixo; modo fila: reatribuido em /avancar)
    fila = None  # manifesto de fila.json, ou None em modo single
    idle_seg = 600
    httpd = None  # set in main(), usado pro self-shutdown

    _lock = threading.Lock()
    last_activity_ts = 0.0
    progresso = None  # dict em memoria, espelha progresso.json
    shutdown_started = False

    def log_message(self, fmt, *args):
        sys.stderr.write("  %s\n" % (fmt % args))

    def _touch(self):
        with self._lock:
            Handler.last_activity_ts = time.time()

    def _send_json(self, status, payload):
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _send_bytes(self, status, data, mime):
        self.send_response(status)
        self.send_header("Content-Type", mime)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def _send_file(self, full, mime):
        try:
            with open(full, "rb") as fh:
                data = fh.read()
        except OSError:
            self.send_error(404, "not found")
            return
        self._send_bytes(200, data, mime)

    # --- GET: player / conteudo.json / arquivo original / vendor -------
    def do_GET(self):
        self._touch()
        path = self.path.split("?", 1)[0]

        if path in ("", "/", "/index.html"):
            self._send_file(PLAYER_HTML, "text/html; charset=utf-8")
            return

        if path == "/conteudo.json":
            self._send_json(200, self.conteudo)
            return

        if path == "/fila.json":
            if self.fila is None:
                self.send_error(404, "esta sessao nao esta em modo fila")
                return
            self._send_json(200, dict(self.fila, item_atual=self.progresso.get("item_atual", 0)))
            return

        if path == "/arquivo":
            formato = self.conteudo.get("formato", "markdown")
            if formato not in ARQUIVO_MIME_BY_FORMATO:
                self.send_error(404, "esta sessao e markdown, nao tem arquivo original")
                return
            arquivo = self.conteudo.get("arquivo_original")
            full = os.path.join(self.session_dir, arquivo) if arquivo and not os.path.isabs(arquivo) else arquivo
            if not full or not os.path.isfile(full):
                self.send_error(404, "arquivo_original nao encontrado")
                return
            self._send_file(full, ARQUIVO_MIME_BY_FORMATO[formato])
            return

        if path.startswith("/vendor/"):
            rel = path[len("/vendor/"):]
            full = os.path.normpath(os.path.join(VENDOR_DIR, rel))
            if not full.startswith(VENDOR_DIR):
                self.send_error(403, "forbidden")
                return
            ext = os.path.splitext(full)[1]
            self._send_file(full, MIME_BY_EXT.get(ext, "application/octet-stream"))
            return

        self.send_error(404, "not found")

    # --- POST: heartbeat / evento / encerrar ----------------------------
    def do_POST(self):
        path = self.path.split("?")[0]
        length = int(self.headers.get("Content-Length", 0) or 0)
        raw = self.rfile.read(length) if length else b""

        if path == "/heartbeat":
            self._touch()
            self._append_evento({"ts": _stamp(), "tipo": "heartbeat"})
            self._send_json(200, {"ok": True})
            return

        if path == "/evento":
            try:
                payload = json.loads(raw.decode("utf-8")) if raw else {}
            except (ValueError, UnicodeDecodeError):
                self.send_error(400, "invalid json")
                return
            tipo = payload.get("tipo")
            if not tipo:
                self.send_error(400, "evento sem 'tipo'")
                return
            evento = dict(payload)
            evento["ts"] = _stamp()
            self._touch()
            self._append_evento(evento)
            self._aplicar_evento(evento)
            self._gravar_progresso()
            self._send_json(200, {"ok": True, "progresso": self.progresso})
            return

        if path == "/avancar":
            if self.fila is None:
                self.send_error(404, "esta sessao nao esta em modo fila")
                return
            self._touch()
            indice_atual = self.progresso.get("item_atual", 0)
            proximo = indice_atual + 1
            self._append_evento({"ts": _stamp(), "tipo": "avancar_item", "de": indice_atual, "para": proximo})

            if proximo < len(self.fila["itens"]):
                Handler.conteudo = _carregar_item_da_fila(self.session_dir, self.fila, proximo)
                self.progresso["item_atual"] = proximo
                self.progresso["local_atual"] = None
                self.progresso["percentual_lido"] = 0.0
                self.progresso["titulo"] = Handler.conteudo.get("titulo")
                self.progresso["atualizado_em"] = _stamp()
                self._gravar_progresso()
                self._send_json(200, {"fim_da_fila": False, "conteudo": Handler.conteudo})
                return

            ao_final = self.fila.get("ao_final") or {}
            self._append_evento({"ts": _stamp(), "tipo": "fila_concluida", "ao_final": ao_final})
            resposta = {"fim_da_fila": True, "ao_final": ao_final}
            if ao_final.get("tipo") == "quiz":
                def _abs(rel):
                    return rel if os.path.isabs(rel) else os.path.join(os.getcwd(), rel)

                quiz_dir = ao_final.get("quiz_dir") or ""
                quiz_dir_abs = _abs(quiz_dir) if quiz_dir else None
                tem_quiz = bool(quiz_dir_abs) and os.path.isfile(os.path.join(quiz_dir_abs, "quiz.json"))

                flashcards_dir = ao_final.get("flashcards_dir") or ""
                flashcards_dir_abs = _abs(flashcards_dir) if flashcards_dir else None
                tem_flashcards = bool(flashcards_dir_abs) and os.path.isfile(
                    os.path.join(flashcards_dir_abs, "flashcards.json")
                )

                if tem_flashcards:
                    resposta["proximo_url"] = _iniciar_flashcards_auto(
                        flashcards_dir_abs, quiz_dir_abs if tem_quiz else None, ao_final.get("titulo")
                    )
                    self._append_evento({
                        "ts": _stamp(), "tipo": "flashcards_auto_iniciado", "proximo_url": resposta["proximo_url"],
                    })
                elif tem_quiz:
                    resposta["proximo_url"] = _iniciar_quiz_auto(quiz_dir_abs)
                    self._append_evento({
                        "ts": _stamp(), "tipo": "quiz_auto_iniciado", "proximo_url": resposta["proximo_url"],
                    })
                elif flashcards_dir:
                    self.progresso["pedidos_pendentes"].append({
                        "tipo": "flashcards_pendente",
                        "flashcards_dir": ao_final.get("flashcards_dir"),
                        "titulo": ao_final.get("titulo"),
                        "ts": _stamp(),
                    })
                else:
                    self.progresso["pedidos_pendentes"].append({
                        "tipo": "quiz_pendente",
                        "quiz_dir": ao_final.get("quiz_dir"),
                        "titulo": ao_final.get("titulo"),
                        "ts": _stamp(),
                    })
            self.progresso["atualizado_em"] = _stamp()
            self._gravar_progresso()
            self._send_json(200, resposta)
            return

        if path == "/encerrar":
            motivo = "usuario_clicou"
            if raw:
                try:
                    motivo = json.loads(raw.decode("utf-8")).get("motivo", motivo)
                except (ValueError, UnicodeDecodeError):
                    pass
            self._append_evento({"ts": _stamp(), "tipo": "encerrar", "motivo": motivo})
            self._gravar_progresso()
            self._send_json(200, {"ok": True, "encerrando": True})
            print("  sessao encerrada pelo usuario — resultado ja salvo em disco.", file=sys.stderr)
            threading.Timer(0.2, self._shutdown_uma_vez).start()
            return

        self.send_error(404, "not found")

    def _append_evento(self, evento):
        path = os.path.join(self.session_dir, "eventos.jsonl")
        with open(path, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(evento, ensure_ascii=False) + "\n")

    def _aplicar_evento(self, evento):
        tipo = evento.get("tipo")
        prog = self.progresso
        prog["atualizado_em"] = evento["ts"]

        if tipo == "progresso":
            prog["local_atual"] = evento.get("local", prog.get("local_atual"))
            if "percentual_lido" in evento:
                prog["percentual_lido"] = evento["percentual_lido"]
        elif tipo == "destaque":
            prog["destaques"].append({
                "id": evento.get("id"),
                "local": evento.get("local"),
                "texto": evento.get("texto"),
                "cor": evento.get("cor", "amarelo"),
            })
        elif tipo == "nota":
            prog["notas"].append({
                "id": evento.get("id"),
                "local": evento.get("local"),
                "texto_ancora": evento.get("texto_ancora"),
                "conteudo": evento.get("conteudo"),
            })
        elif tipo in ("pedido_explicacao", "pedido_pratica"):
            prog["pedidos_pendentes"].append({
                "tipo": tipo,
                "local": evento.get("local"),
                "texto_selecionado": evento.get("texto_selecionado"),
                "ts": evento["ts"],
            })

    def _gravar_progresso(self):
        path = os.path.join(self.session_dir, "progresso.json")
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(self.progresso, fh, ensure_ascii=False, indent=2)

    def _shutdown_uma_vez(self):
        with self._lock:
            if Handler.shutdown_started:
                return
            Handler.shutdown_started = True
        if self.httpd is not None:
            self.httpd.shutdown()


def _idle_watch(check_interval_seg, stop_event):
    while not stop_event.wait(check_interval_seg):
        with Handler._lock:
            ocioso_ha = time.time() - Handler.last_activity_ts
            ja_encerrando = Handler.shutdown_started
        if ja_encerrando:
            return
        if ocioso_ha > Handler.idle_seg:
            print(
                "  ocioso ha %ds (limite %ds) — encerrando automaticamente." % (int(ocioso_ha), Handler.idle_seg),
                file=sys.stderr,
            )
            with Handler._lock:
                Handler.shutdown_started = True
            if Handler.httpd is not None:
                Handler.httpd.shutdown()
            return


def main(argv=None):
    ap = argparse.ArgumentParser(description="Runtime local do plugin study-leitor-web (stdlib only).")
    ap.add_argument("session_dir", help="pasta da sessao de leitura (contem conteudo.json)")
    ap.add_argument("--port", type=int, default=8000)
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument(
        "--idle", type=int, default=600,
        help="segundos sem heartbeat/atividade antes do self-shutdown (default 600 = 10min)",
    )
    args = ap.parse_args(argv)

    sess = os.path.abspath(args.session_dir)
    fila_path = os.path.join(sess, "fila.json")
    conteudo_path = os.path.join(sess, "conteudo.json")

    fila = None
    if os.path.isfile(fila_path):
        with open(fila_path, "r", encoding="utf-8") as fh:
            fila = json.load(fh)
        if not fila.get("itens"):
            sys.exit("erro: fila.json precisa de pelo menos 1 item em 'itens'")
    elif os.path.isfile(conteudo_path):
        with open(conteudo_path, "r", encoding="utf-8") as fh:
            conteudo = json.load(fh)
    else:
        sys.exit("erro: %s nao contem conteudo.json nem fila.json — gere a sessao primeiro (ver SKILL.md)" % sess)

    progresso_path = os.path.join(sess, "progresso.json")
    progresso_existente = None
    if os.path.isfile(progresso_path):
        with open(progresso_path, "r", encoding="utf-8") as fh:
            progresso_existente = json.load(fh)

    if fila is not None:
        indice = progresso_existente.get("item_atual", 0) if progresso_existente else 0
        conteudo = _carregar_item_da_fila(sess, fila, indice)

    formato = conteudo.get("formato", "markdown")
    if formato == "markdown":
        if not conteudo.get("corpo_markdown"):
            sys.exit("erro: conteudo.json formato=markdown precisa de 'corpo_markdown'")
    elif formato in ("epub", "pdf"):
        arquivo = conteudo.get("arquivo_original")
        full = os.path.join(sess, arquivo) if arquivo and not os.path.isabs(arquivo) else arquivo
        if not arquivo or not os.path.isfile(full):
            sys.exit("erro: conteudo.json formato=%s precisa de 'arquivo_original' existente" % formato)
    else:
        sys.exit("erro: conteudo.json 'formato' deve ser markdown, epub ou pdf")

    if progresso_existente is not None:
        progresso = progresso_existente
        print("  retomando sessao existente (progresso.json ja tinha destaques/notas).")
    else:
        progresso = _progresso_inicial(conteudo, fila=fila is not None)

    Handler.session_dir = sess
    Handler.conteudo = conteudo
    Handler.fila = fila
    Handler.idle_seg = args.idle
    Handler.progresso = progresso
    Handler.last_activity_ts = time.time()
    Handler.shutdown_started = False

    httpd = ThreadingHTTPServer((args.host, args.port), Handler)
    Handler.httpd = httpd

    stop_event = threading.Event()
    watcher = threading.Thread(target=_idle_watch, args=(30, stop_event), daemon=True)
    watcher.start()

    url = "http://%s:%d/" % (args.host, args.port)
    print("study-leitor-web rodando: %s" % url)
    print("  sessao: %s (formato: %s)" % (sess, formato))
    print("  encerra sozinho apos %ds sem heartbeat/atividade do navegador" % args.idle)
    print("  ou ao clicar 'Terminar sessao'. Ctrl+C tambem para manualmente.")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nparado.")
    stop_event.set()
    httpd.server_close()
    print("study-leitor-web encerrado.")


if __name__ == "__main__":
    main()
