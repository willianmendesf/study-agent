#!/usr/bin/env python3
"""backlog-memos-aulas-portugues.py — fecha o buraco do Memos nas aulas de Português.

PROBLEMA QUE RESOLVE (2026-11-17):
  `enviar-aula.sh` posta a aula no Memos e grava `memos_id` no frontmatter e no
  `_catalogo.md`. Quando o Memos está fora do ar (tailnet caído / MagicDNS off),
  a postagem falha, o script segue (correto: capa+áudio têm de sair de qualquer
  forma) e a aula fica `status: enviado` com `memos_id: ""` — PARA SEMPRE. Nada
  volta depois para publicá-la: o script só olha a aula do dia.
  Resultado: aulas 26, 31 e 32 estão enviadas no Telegram e AUSENTES do Memos.

O QUE FAZ:
  1. Descobre o endpoint do Memos (IPv6 -> IPv4 -> hostname, igual ao memos-post.sh).
     Se nenhum responder, sai com 0 sem tocar em arquivo nenhum (não é erro).
  2. Varre `data/estudos/notas/portugues-aulas-diarias/aula-*.md` e seleciona
     `status: enviado` + `memos_id` vazio/`-`.
  3. Para cada uma: chama `memos-post.sh --file ... --tags ...`, captura o id e
     grava no frontmatter (`memos_id:`) e na linha do `_catalogo.md`.

IDEMPOTENTE: roda quantas vezes quiser; só age em aula sem memo_id.
Uso:
  python3 scripts/backlog-memos-aulas-portugues.py            # executa
  python3 scripts/backlog-memos-aulas-portugues.py --dry-run   # só lista
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PASTA = ROOT / "data/estudos/notas/portugues-aulas-diarias"
CATALOGO = PASTA / "_catalogo.md"
MEMOS_POST = ROOT / ".claude/skills/study-memos-sync/bin/memos-post.sh"
ENV_FILE = ROOT / "data/config-backup/memos/memos.env"

TAGS = "study-agent,estudo/portugues,tipo/aula,serie/aulas-portugues"

CANDIDATOS = [
    "http://[2804:7f0:6942:a634:e221:6309:fdc:f815]",
    "http://100.103.64.20",
]


def ler_env() -> dict[str, str]:
    env: dict[str, str] = {}
    if not ENV_FILE.is_file():
        return env
    for linha in ENV_FILE.read_text(encoding="utf-8", errors="replace").splitlines():
        linha = linha.strip()
        if not linha or linha.startswith("#") or "=" not in linha:
            continue
        k, v = linha.split("=", 1)
        env[k.strip()] = v.strip().strip('"').strip("'")
    return env


def memos_online(env: dict[str, str]) -> str | None:
    """Devolve a base URL que responde a listagem, ou None."""
    pat = env.get("MEMOS_PAT", "")
    host = (env.get("MEMOS_URL") or "").rstrip("/")
    candidatos = list(CANDIDATOS)
    if host:
        candidatos.append(host)
    for base in candidatos:
        req = urllib.request.Request(
            f"{base}/api/v1/memos?pageSize=1",
            headers={"Authorization": f"Bearer {pat}"} if pat else {},
        )
        try:
            with urllib.request.urlopen(req, timeout=12) as r:
                if r.status == 200:
                    return base
        except (urllib.error.URLError, OSError, ValueError):
            continue
    return None


def frontmatter(path: Path) -> dict[str, str]:
    campos: dict[str, str] = {}
    texto = path.read_text(encoding="utf-8", errors="replace")
    if not texto.startswith("---"):
        return campos
    fim = texto.find("\n---", 3)
    if fim < 0:
        return campos
    for linha in texto[3:fim].splitlines():
        m = re.match(r"^([a-z_]+):\s*(.*)$", linha)
        if m:
            campos[m.group(1)] = m.group(2).strip().strip('"').strip("'")
    return campos


def pendentes() -> list[tuple[Path, dict[str, str]]]:
    out = []
    for arq in sorted(PASTA.glob("aula-*.md")):
        fm = frontmatter(arq)
        if fm.get("status") != "enviado":
            continue
        memo = fm.get("memos_id", "")
        if memo in ("", "-"):
            out.append((arq, fm))
    return out


def gravar_memo_id(arq: Path, memo_id: str) -> bool:
    texto = arq.read_text(encoding="utf-8", errors="replace")
    novo, n = re.subn(
        r"^memos_id:.*$", f"memos_id: {memo_id}", texto, count=1, flags=re.MULTILINE
    )
    if n == 0:
        novo = texto.replace("\n---\n", f"\nmemos_id: {memo_id}\n---\n", 1)
    if novo == texto:
        return False
    arq.write_text(novo, encoding="utf-8")
    return True


def gravar_catalogo(numero: str, memo_id: str) -> bool:
    if not CATALOGO.is_file():
        return False
    texto = CATALOGO.read_text(encoding="utf-8", errors="replace")
    linhas = texto.splitlines()
    achou = False
    for i, linha in enumerate(linhas):
        if not linha.startswith(f"| {numero} |"):
            continue
        cols = [c.strip() for c in linha.strip().strip("|").split("|")]
        if len(cols) < 7:
            continue
        atual = cols[5].strip().strip('"').strip("'")
        if atual not in ("-", ""):
            continue
        cols[5] = memo_id
        linhas[i] = "| " + " | ".join(cols) + " |"
        achou = True
        break
    if achou:
        CATALOGO.write_text("\n".join(linhas) + "\n", encoding="utf-8")
    return achou


def main() -> int:
    dry = "--dry-run" in sys.argv
    alvos = pendentes()
    if not alvos:
        print("✅ Nenhuma aula pendente de Memos.")
        return 0

    print(f"📋 {len(alvos)} aula(s) sem memo_id: "
          + ", ".join(a.name.split('-')[1] for a, _ in alvos))

    env = ler_env()
    base = memos_online(env)
    if not base:
        print("⚠️  Memos fora do ar (IPv6, IPv4 e hostname sem resposta) — "
              "nada alterado; o backlog tenta de novo amanhã.")
        return 0
    print(f"   Memos em: {base}")

    if dry:
        print("🔍 --dry-run: nada postado.")
        return 0

    ok = falhou = 0
    for arq, fm in alvos:
        numero = fm.get("numero") or arq.name.split("-")[1]
        numero = str(int(numero)) if numero.isdigit() else numero
        print(f"📤 aula {numero}: {arq.name}")
        try:
            r = subprocess.run(
                ["bash", str(MEMOS_POST), "--file", str(arq),
                 "--visibility", "PRIVATE", "--tags", TAGS],
                capture_output=True, text=True, timeout=180,
            )
        except subprocess.TimeoutExpired:
            print("   ❌ timeout")
            falhou += 1
            continue
        saida = (r.stdout or "") + (r.stderr or "")
        m = re.search(r"memos/([A-Za-z0-9_-]{6,})", saida)
        if not m:
            print(f"   ❌ sem id na resposta: {saida.strip()[:160]}")
            falhou += 1
            continue
        memo_id = m.group(1)
        gravar_memo_id(arq, memo_id)
        gravar_catalogo(numero.zfill(2), memo_id)
        print(f"   ✅ memo {memo_id}")
        ok += 1

    print(f"\nResumo: {ok} publicado(s), {falhou} falha(s).")
    return 0 if falhou == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
