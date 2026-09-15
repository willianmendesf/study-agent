#!/usr/bin/env python3
"""
server.py — runtime local do plugin study-quiz-serio. Só stdlib (nada de pip, nada de banco).

Diferente do study-h5p (que usa H5P.QuestionSet — mostra certo/errado por questão e permite
tentar de novo/voltar), este motor serve um quiz PRÓPRIO onde:
  - nao ha feedback de certo/errado por questao (so no final)
  - nao ha botao "verificar" nem "ver solucao" — so "avancar"
  - nao ha como voltar a uma questao ja respondida
  - tempo e acerto/erro de cada questao sao sempre registrados
  - ao finalizar, o cronometro para, o resultado + relatorio (pontos fracos + o que reler,
    nunca a resposta certa) sao salvos em disco, e o servidor se auto-encerra pouco depois

Uso:
    python3 server.py <pasta-do-exercicio> [--port 8000] [--grace 90]

A pasta do exercicio deve conter um quiz.json (ver SKILL.md para o schema).
"""
import argparse
import datetime
import json
import os
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

SKILL_DIR = os.path.dirname(os.path.abspath(__file__))
PLAYER_HTML = os.path.join(SKILL_DIR, "player", "index.html")


def _fmt_mmss(total_seg):
    total_seg = int(total_seg or 0)
    return "%02d:%02d" % (total_seg // 60, total_seg % 60)


def _gerar_relatorio_md(quiz, resultado):
    linhas = []
    linhas.append("# Relatório — %s" % quiz.get("titulo", "Quiz"))
    linhas.append("")
    linhas.append("**Matéria:** %s · **Tema:** %s" % (quiz.get("materia", "—"), quiz.get("tema", "—")))
    linhas.append(
        "**Nota:** %s/%s (%s%%) · **Tempo total:** %s · **Concluído em:** %s"
        % (
            resultado["score_raw"],
            resultado["score_max"],
            resultado["score_pct"],
            _fmt_mmss(resultado["duracao_total_seg"]),
            resultado["finalizado_em"],
        )
    )
    linhas.append("")

    fracos = resultado.get("pontos_fracos") or []
    if fracos:
        linhas.append("## Pontos fracos — revisar antes da próxima tentativa")
        linhas.append("")
        for pf in fracos:
            linhas.append("### %s — %d/%d questões erradas" % (pf["topico"], pf["erros"], pf["total"]))
            for est in pf.get("estudar") or []:
                linhas.append("- 📖 Para entender melhor, leia: %s" % est)
            linhas.append("")
    else:
        linhas.append("## Pontos fracos")
        linhas.append("Nenhum — acertou tudo. 🎉")
        linhas.append("")

    dominados = resultado.get("topicos_dominados") or []
    if dominados:
        linhas.append("## Pontos dominados (100% de acerto)")
        for t in dominados:
            linhas.append("- %s" % t)
        linhas.append("")

    pct = resultado["score_pct"]
    if pct >= 100:
        msg = "Domínio completo — pode avançar pro próximo bloco."
    elif pct >= 60:
        msg = "Boa base. Revise os pontos fracos acima antes de considerar o tema fechado."
    else:
        msg = "Vale revisar o material antes de tentar de novo — foque nos pontos fracos listados acima."
    linhas.append("## Próximo passo")
    linhas.append(msg)
    linhas.append("")
    return "\n".join(linhas)


class Handler(BaseHTTPRequestHandler):
    exercise_dir = None  # set in main()
    quiz = None  # conteudo de quiz.json, carregado uma vez em main()
    grace_seg = 90
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

    # --- GET: player + quiz.json --------------------------------------
    def do_GET(self):
        path = self.path.split("?", 1)[0]
        if path in ("", "/", "/index.html"):
            self._send_file(PLAYER_HTML, "text/html; charset=utf-8")
            return
        if path == "/quiz.json":
            body = json.dumps(self.quiz, ensure_ascii=False).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)
            return
        self.send_error(404, "not found")

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

        stamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        respostas = payload.get("respostas") or []
        score_raw = sum(1 for r in respostas if r.get("acertou"))
        score_max = len(respostas)
        score_pct = round(100.0 * score_raw / score_max, 1) if score_max else 0.0

        por_topico = {}
        for r in respostas:
            topico = r.get("topico") or "Geral"
            slot = por_topico.setdefault(topico, {"erros": 0, "total": 0, "estudar": set()})
            slot["total"] += 1
            if not r.get("acertou"):
                slot["erros"] += 1
                if r.get("estudar"):
                    slot["estudar"].add(r["estudar"])

        pontos_fracos = [
            {"topico": t, "erros": s["erros"], "total": s["total"], "estudar": sorted(s["estudar"])}
            for t, s in por_topico.items()
            if s["erros"] > 0
        ]
        pontos_fracos.sort(key=lambda p: (p["erros"] / p["total"]), reverse=True)
        topicos_dominados = sorted(t for t, s in por_topico.items() if s["erros"] == 0)

        resultado = {
            "atualizado_em": stamp,
            "titulo": self.quiz.get("titulo"),
            "materia": self.quiz.get("materia"),
            "tema": self.quiz.get("tema"),
            "iniciado_em": payload.get("iniciado_em"),
            "finalizado_em": payload.get("finalizado_em") or stamp,
            "duracao_total_seg": payload.get("duracao_total_seg", 0),
            "score_raw": score_raw,
            "score_max": score_max,
            "score_pct": score_pct,
            "respostas": respostas,
            "pontos_fracos": pontos_fracos,
            "topicos_dominados": topicos_dominados,
        }

        with open(os.path.join(self.exercise_dir, "resultado.json"), "w", encoding="utf-8") as fh:
            json.dump(resultado, fh, ensure_ascii=False, indent=2)
        with open(os.path.join(self.exercise_dir, "resultado.jsonl"), "a", encoding="utf-8") as fh:
            fh.write(json.dumps({"recebido_em": stamp, "resultado": resultado}, ensure_ascii=False) + "\n")

        relatorio_md = _gerar_relatorio_md(self.quiz, resultado)
        with open(os.path.join(self.exercise_dir, "relatorio.md"), "w", encoding="utf-8") as fh:
            fh.write(relatorio_md)

        self._send_json(200, {"ok": True, "encerra_em_seg": self.grace_seg, "resultado": resultado})

        print(
            "  resultado salvo (%d/%d, %.1f%%) — servidor encerra em %ds"
            % (score_raw, score_max, score_pct, self.grace_seg),
            file=sys.stderr,
        )

        def _shutdown():
            sys.stderr.write("  encerrando automaticamente (resultado ja salvo em disco).\n")
            if self.httpd is not None:
                self.httpd.shutdown()

        threading.Timer(self.grace_seg, _shutdown).start()


def main(argv=None):
    ap = argparse.ArgumentParser(description="Runtime local do plugin study-quiz-serio (stdlib only).")
    ap.add_argument("exercise_dir", help="pasta do exercicio (contem quiz.json)")
    ap.add_argument("--port", type=int, default=8000)
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--grace", type=int, default=90, help="segundos de espera apos finalizar antes do self-shutdown")
    args = ap.parse_args(argv)

    ex = os.path.abspath(args.exercise_dir)
    quiz_path = os.path.join(ex, "quiz.json")
    if not os.path.isfile(quiz_path):
        sys.exit("erro: %s nao contem quiz.json — gere o quiz primeiro (ver SKILL.md)" % ex)
    with open(quiz_path, "r", encoding="utf-8") as fh:
        quiz = json.load(fh)
    if not quiz.get("questoes"):
        sys.exit("erro: quiz.json sem campo 'questoes'")

    Handler.exercise_dir = ex
    Handler.quiz = quiz
    Handler.grace_seg = args.grace
    httpd = ThreadingHTTPServer((args.host, args.port), Handler)
    Handler.httpd = httpd
    url = "http://%s:%d/" % (args.host, args.port)
    print("study-quiz-serio rodando: %s" % url)
    print("  exercicio: %s" % ex)
    print("  ao finalizar: resultado.json + relatorio.md salvos, servidor cai sozinho ~%ds depois" % args.grace)
    print("  Ctrl+C para parar manualmente antes disso.")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nparado.")
    httpd.server_close()
    print("study-quiz-serio encerrado.")


if __name__ == "__main__":
    main()
