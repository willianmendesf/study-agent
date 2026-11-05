#!/usr/bin/env python3
"""Estado do reenvio ao BookOrbit + notificacao no Telegram (sem spam).

POR QUE EXISTE (2026-11-05)
  O reenvio automatico roda a cada 15 min. Como o BookOrbit so libera o
  upload quando o William promove a conta `study-agent` a Editor no app,
  a maioria das execucoes vai falhar com 403. Notificar o Telegram em
  CADA execucao seria ~96 mensagens/dia de puro spam.

  Aqui o estado e' um arquivo. A notificacao so sai quando o STATUS MUDA
  (ex.: "aguardando_permissao" -> "enviado_31"). Se o status nao mudou,
  nada e' enviado.

ESTADO: data/perfil/bibliotecario/orbit-estado.json  (gitignored)
"""
import argparse
import json
import re
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
STATE = ROOT / "data" / "perfil" / "bibliotecario" / "orbit-estado.json"
SECURITY = Path("/var/lib/picoclaw/.security.yml")
CHAT_ID = "916214383"


def _token() -> str:
    if not SECURITY.exists():
        return ""
    txt = SECURITY.read_text(encoding="utf-8", errors="replace")
    m = re.search(r"telegram\s*:\s*\n\s*settings\s*:\s*\n\s*token\s*:\s*(\S+)", txt)
    return m.group(1).strip("\"'") if m else ""


def _ler() -> dict:
    try:
        return json.loads(STATE.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _gravar(d: dict) -> None:
    STATE.parent.mkdir(parents=True, exist_ok=True)
    STATE.write_text(json.dumps(d, ensure_ascii=False, indent=2) + "\n",
                     encoding="utf-8")


def _enviar(texto: str) -> bool:
    """Envia via API do Telegram. Usa curl (o urllib desta LXC demorava
    >60s e o exec cortava em 60s)."""
    tok = _token()
    if not tok:
        print("[notificar] token do Telegram ausente — nada enviado", file=sys.stderr)
        return False
    try:
        proc = subprocess.run(
            ["curl", "-sS", "--max-time", "45", "-X", "POST",
             f"https://api.telegram.org/bot{tok}/sendMessage",
             "--data-urlencode", f"chat_id={CHAT_ID}",
             "--data-urlencode", f"text={texto}",
             "--data-urlencode", "disable_web_page_preview=true"],
            capture_output=True, text=True, timeout=55)
    except subprocess.TimeoutExpired:
        print("[notificar] timeout ao enviar", file=sys.stderr)
        return False
    except FileNotFoundError:
        print("[notificar] curl ausente", file=sys.stderr)
        return False
    ok = '"ok":true' in (proc.stdout or "").replace(" ", "")
    if ok:
        print("[notificar] mensagem enviada ao Telegram")
    else:
        print(f"[notificar] Telegram recusou: {(proc.stdout or proc.stderr)[:200]}",
              file=sys.stderr)
    return ok


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--status", required=True)
    ap.add_argument("--mensagem", default="")
    ap.add_argument("--seed", action="store_true",
                    help="grava o estado sem notificar (uso na 1a execucao)")
    ap.add_argument("--force", action="store_true", help="notifica sempre")
    args = ap.parse_args()

    st = _ler()
    anterior = st.get("status")

    if args.seed:
        _gravar({"status": args.status, "ts": time.strftime("%Y-%m-%dT%H:%M:%S"),
                 "notificado": False})
        print(f"[estado] seed: {args.status}")
        return 0

    if not args.force and anterior == args.status:
        print(f"[estado] sem mudanca ({args.status}) — sem notificacao")
        return 0

    _gravar({"status": args.status, "ts": time.strftime("%Y-%m-%dT%H:%M:%S"),
             "notificado": bool(args.mensagem)})

    if args.mensagem:
        _enviar(args.mensagem)
    else:
        print(f"[estado] status -> {args.status}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
