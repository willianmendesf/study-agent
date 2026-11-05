#!/usr/bin/env python3
"""Resume o resultado da rodada de ficcao e notifica o Telegram (sem spam).

Usado por `scripts/rodada-ficcao-cron.sh` (rodado pelo crontab do SISTEMA).

REGRA: notifica SO quando o numero de obras adquiridas no dia MUDA. Caso
contrario, o William receberia uma mensagem diaria sem conteudo novo.

ESTADO: data/perfil/bibliotecario/rodada-ficcao-estado.json (gitignored)
"""
import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ESTADO = ROOT / "data" / "perfil" / "bibliotecario" / "rodada-ficcao-estado.json"
PIPELINE_ESTADO = ROOT / "data" / "perfil" / "bibliotecario" / "pipeline-estado.json"


def adquiridos_hoje():
    """Obras marcadas como 'adquirido' com data de hoje no estado do pipeline."""
    try:
        d = json.loads(PIPELINE_ESTADO.read_text(encoding="utf-8"))
    except Exception:
        return 0
    hoje = time.strftime("%Y-%m-%d")
    return sum(1 for v in d.values()
               if isinstance(v, dict) and v.get("status") == "adquirido"
               and str(v.get("data") or "") == hoje)


def notificar(mensagem, status):
    r = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "orbit-notificar.py"),
         "--status", status, "--mensagem", mensagem],
        capture_output=True, text=True, timeout=120)
    return (r.stdout or "").strip()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--falhas", default="0")
    ap.add_argument("--forcar", action="store_true")
    args = ap.parse_args()

    novos = adquiridos_hoje()
    falhas = args.falhas

    prev = 0
    if ESTADO.exists():
        try:
            prev = json.loads(ESTADO.read_text(encoding="utf-8")).get("novos", 0)
        except Exception:
            prev = 0

    if novos == prev and not args.forcar:
        print(f"[rodada-ficcao] sem mudanca ({novos} == {prev}) — sem notificacao")
        return 0

    ESTADO.parent.mkdir(parents=True, exist_ok=True)
    ESTADO.write_text(json.dumps(
        {"novos": novos, "falhas": falhas, "ts": time.strftime("%Y-%m-%dT%H:%M:%S")},
        ensure_ascii=False, indent=1), encoding="utf-8")

    msg = (f"📚 Rodada de ficção (rampa): {novos} obra(s) nova(s) no acervo, "
           f"{falhas} falha(s). Os ebooks também foram enviados ao BookOrbit.")
    print(notificar(msg, f"rodada_ficcao_{novos}"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
