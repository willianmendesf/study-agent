#!/usr/bin/env python3
"""Reenvia a capa textual de uma aula que já foi entregue só como áudio.

Lê o bloco CAPA_TEXTUAL de um log do enviar-aula.sh e manda pro Telegram
usando o MESMO caminho do script (curl + sendMessage), validando a correção
de 2026-11-17.

Uso: python3 scripts/reenviar-capa-aula.py /tmp/aula-31.log
"""
import re
import subprocess
import sys
from pathlib import Path

SECURITY = Path("/var/lib/picoclaw/.security.yml")
CHAT_ID = "916214383"


def token() -> str:
    txt = SECURITY.read_text(encoding="utf-8", errors="replace")
    m = re.search(r"telegram\s*:\s*\n\s*settings\s*:\s*\n\s*token\s*:\s*(\S+)", txt)
    return m.group(1).strip("\"'") if m else ""


def capa(log: str) -> str:
    txt = Path(log).read_text(encoding="utf-8", errors="replace")
    m = re.search(r"----- BEGIN CAPA_TEXTUAL -----\n(.*?)\n----- END CAPA_TEXTUAL -----",
                  txt, re.S)
    if not m:
        raise SystemExit("bloco CAPA_TEXTUAL não encontrado no log")
    return m.group(1)


def main() -> int:
    if len(sys.argv) < 2:
        raise SystemExit("uso: reenviar-capa-aula.py <log>")
    tok = token()
    if not tok:
        raise SystemExit("token do Telegram não encontrado em .security.yml")
    texto = capa(sys.argv[1])
    # remove a linha "Áudio na próxima mensagem" — o áudio já foi entregue
    texto = re.sub(r"\n+Áudio na próxima mensagem\.\s*👆\s*$",
                   "\n\n(Esta é a capa da aula que chegou só como áudio — "
                   "o texto completo está no arquivo da série.)", texto)
    p = subprocess.run(
        ["curl", "-sS", "--max-time", "60", "-X", "POST",
         f"https://api.telegram.org/bot{tok}/sendMessage",
         "--data-urlencode", f"chat_id={CHAT_ID}",
         "--data-urlencode", f"text={texto}",
         "--data-urlencode", "disable_web_page_preview=true"],
        capture_output=True, text=True, timeout=70)
    ok = '"ok":true' in (p.stdout or "").replace(" ", "")
    print("enviado" if ok else f"falhou: {(p.stdout or p.stderr)[:300]}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
