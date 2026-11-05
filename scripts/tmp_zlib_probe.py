#!/usr/bin/env python3
"""Testa o dominio vivo do z-library e a cota das 4 contas (via eAPI direto)."""
import json
import subprocess
from pathlib import Path

creds = json.load(open(Path.home() / ".zlib-mcp" / ".account-env-cache.json"))
UA = "Mozilla/5.0 (Android 12; Mobile)"


def curl(args, timeout=25):
    r = subprocess.run(["curl", "-s", "-m", str(timeout), *args],
                       capture_output=True, text=True)
    return r.stdout


def cookie_for(acct):
    e = creds[acct]
    return f"remix_userid={e['ZLIB_REMIX_ID']}; remix_userkey={e['ZLIB_REMIX_KEY']}"


DOMINIOS = ["z-lib.gd", "z-lib.sk", "z-lib.se", "z-lib.li"]

print("=== 1. Qual dominio responde (conta zlib2) ===")
vivo = None
for dom in DOMINIOS:
    out = curl(["-o", "/dev/null", "-w", "%{http_code}",
                f"https://{dom}/eapi/book/search",
                "-H", f"User-Agent: {UA}",
                "-b", cookie_for("zlib2"),
                "-d", "message=Dostoyevsky&limit=3"])
    print(f"  {dom:14s} http={out}")
    if out == "200":
        vivo = dom
print(f"  -> dominio vivo: {vivo}")

if not vivo:
    raise SystemExit("nenhum dominio respondeu 200")

print("\n=== 2. Cota por conta ===")
for acct in ["zlib", "zlib2", "zlib3", "zlib4"]:
    if acct not in creds:
        # conta principal vem do yaml do perfil
        import re
        p = Path("/home/willian/study-agent/data/perfil/bibliotecario/zlib-credentials.yaml")
        txt = p.read_text(encoding="utf-8")
        blocks = txt.split("- alias:")
        order = ["zlib", "zlib2", "zlib3", "zlib4"]
        for i, b in enumerate(blocks[1:]):
            rid = re.search(r"remix_id:\s*'?([0-9]+)'?", b)
            rkey = re.search(r"remix_key:\s*'?([A-Za-z0-9]+)'?", b)
            if rid and rkey and i < len(order):
                creds.setdefault(order[i], {})["ZLIB_REMIX_ID"] = rid.group(1)
                creds.setdefault(order[i], {})["ZLIB_REMIX_KEY"] = rkey.group(1)
    if acct not in creds:
        print(f"  {acct}: sem credencial")
        continue
    out = curl([f"https://{vivo}/eapi/user/profile",
                "-H", f"User-Agent: {UA}",
                "-b", cookie_for(acct)])
    try:
        d = json.loads(out)
        u = d.get("user", d)
        print(f"  {acct:6s} hoje={u.get('downloads_today')} limite={u.get('downloads_limit')} "
              f"email={u.get('email')}")
    except Exception:
        print(f"  {acct:6s} resposta nao-JSON: {out[:160]}")
