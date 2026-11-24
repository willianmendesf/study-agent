#!/usr/bin/env python3
"""Sincroniza o campo `orbit` do pipeline-estado.json com o que EXISTE no BookOrbit.

POR QUE EXISTE (2026-11-24, queixa do William: "precisa revisar isso aí, não está
marcando o que já foi baixado")

  O `pipeline-estado.json` é a memoria do pipeline: `status: adquirido` impede o
  DOWNLOAD repetido (isso funciona). Mas o campo `orbit` (`ok` / `falhou` / `None`)
  ficou defasado em 95 itens: o livro foi enviado ao BookOrbit numa rodada em que
  o app estava fora do ar, o upload deu erro, e depois o arquivo subiu pelo cron
  de `_incoming/` — sem ninguem voltar para corrigir o estado.

  Amostra medida em 2026-11-24: 9 de 10 itens marcados `orbit != ok` ESTAVAM no
  app. Ou seja, o estado mentia e o relatorio tambem.

O QUE FAZ
  1. Le o estado; seleciona `status == adquirido` e `orbit != 'ok'`.
  2. Para cada um, busca o TITULO em `GET /api/v1/books/search?q=` (so leitura).
  3. Se o titulo aparece no resultado -> grava `orbit: "ok"` + `orbit_bookId`.
  4. Grava o estado uma vez no fim (idempotente: rodar 2x nao muda nada).

NAO baixa, NAO envia, NAO apaga. So leitura na API + escrita no JSON local.

USO
  python3 scripts/sincronizar-orbit-estado.py --dry     # so relata
  python3 scripts/sincronizar-orbit-estado.py           # aplica
"""
import argparse
import importlib.util
import json
import re
import sys
import time
import unicodedata
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ESTADO = ROOT / "data" / "perfil" / "bibliotecario" / "pipeline-estado.json"
ORBIT = ROOT / "scripts" / "orbit-upload.py"


def norm(s):
    s = unicodedata.normalize("NFKD", s or "")
    s = "".join(c for c in s if not unicodedata.combining(c)).lower()
    return re.sub(r"[^a-z0-9 ]", " ", s)


def _ou():
    spec = importlib.util.spec_from_file_location("orbit_upload", ORBIT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def titulo_do_md(v):
    """Titulo a partir do frontmatter do .md (para itens antigos sem `titulo`)."""
    md = str(v.get("caminho_md") or v.get("md") or "").replace("acervo:", "")
    if not md:
        return ""
    p = ROOT / md
    if not p.exists():
        return ""
    try:
        with p.open(encoding="utf-8", errors="ignore") as fh:
            for _ in range(15):
                ln = fh.readline()
                m = re.match(r'\s*titulo:\s*"?([^"\n]+)"?', ln)
                if m:
                    return m.group(1).strip()
    except OSError:
        pass
    return ""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry", action="store_true")
    ap.add_argument("--limite", type=int, default=0, help="processa so N itens")
    args = ap.parse_args()

    estado = json.loads(ESTADO.read_text(encoding="utf-8"))
    # inclui os que so tem o titulo no frontmatter do .md
    for v in estado.values():
        if (v.get("status") == "adquirido" and not v.get("titulo")
                and (v.get("orbit") or "") != "ok"):
            t = titulo_do_md(v)
            if t:
                v["titulo"] = t
    pend = [(k, v) for k, v in estado.items()
            if v.get("status") == "adquirido"
            and (v.get("orbit") or "") != "ok"
            and (v.get("titulo") or "")]
    if args.limite:
        pend = pend[: args.limite]
    print(f"{len(pend)} item(ns) com orbit != ok")
    if not pend:
        return 0

    ou = _ou()
    token, _ = ou.login()

    def busca(q):
        url = ("http://192.168.15.26/api/v1/books/search?q="
               + urllib.parse.quote(q))
        req = urllib.request.Request(url,
                                     headers={"Authorization": f"Bearer {token}"})
        with urllib.request.urlopen(req, timeout=45) as r:
            return json.loads(r.read().decode("utf-8"))

    ok = nao = erro = 0
    for chave, v in pend:
        titulo = v["titulo"]
        # o titulo curto busca melhor: corta no ":" (subtitulo polui)
        q = titulo.split(":")[0].strip() or titulo
        try:
            livros = busca(q)
        except Exception as e:
            erro += 1
            print(f"  [ERRO] {titulo[:40]}: {e}")
            continue
        alvo = norm(q)[:22]
        achado = None
        for b in livros if isinstance(livros, list) else []:
            bt = norm(b.get("title") or "")
            if alvo and (alvo in bt or bt.startswith(alvo[:14])):
                achado = b
                break
        if achado:
            ok += 1
            v["orbit"] = "ok"
            v["orbit_bookId"] = achado.get("id")
            print(f"  [OK] {titulo[:42]:44s} -> bookId {achado.get('id')}")
        else:
            nao += 1
            print(f"  [--] {titulo[:42]:44s} nao encontrado no app")
        time.sleep(0.25)

    print(f"\nmarcados ok: {ok} | nao encontrados: {nao} | erro: {erro}")
    if args.dry:
        print("(dry — nada gravado)")
        return 0
    if ok:
        ESTADO.write_text(json.dumps(estado, ensure_ascii=False, indent=1),
                          encoding="utf-8")
        print("pipeline-estado.json atualizado")
    return 0


if __name__ == "__main__":
    sys.exit(main())
