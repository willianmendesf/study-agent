#!/usr/bin/env python3
"""
zlib-reconectar.py — reconecta e valida as contas do z-library.

POR QUE ESTE SCRIPT (2026-11-05)
    A conta 1 (`zlib`, alias `principal`, remix_id 31625441) ficou SEM
    credencial no cache depois da migracao da LXC. O `zlib-api.py` so aceita
    cookie (remix_userid + remix_userkey); nao ha login por e-mail/senha nele.
    Este script fecha o ciclo: loga por e-mail/senha, grava o par
    remix_id/remix_key no cache, e VALIDA (profile) antes de dar baixa.

USO
    # 1. Verificar o estado de todas as contas (nao escreve nada)
    python3 scripts/zlib-reconectar.py --verify

    # 2. Reconectar uma conta (a senha vem do ambiente, nunca do historico)
    ZLIB_PASSWORD='...' python3 scripts/zlib-reconectar.py \
        --alias zlib --email 'conta@exemplo.com'

    # 3. Só conferir o cache
    python3 scripts/zlib-reconectar.py --list

NUNCA imprime a senha nem a remix_key completa (mostra so os 4 ultimos).
"""
import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CACHE = Path.home() / ".zlib-mcp" / ".account-env-cache.json"
CREDS_YAML = ROOT / "data" / "perfil" / "bibliotecario" / "zlib-credentials.yaml"
DOMINIO = "https://z-lib.gd"
UA = "Mozilla/5.0 (Android 12; Mobile)"

# id -> alias do cache (a ordem e' historica: zlib = "conta 1")
ALIASES = ["zlib", "zlib2", "zlib3", "zlib4"]


# --------------------------------------------------------------------------
def _curl(args, timeout=40):
    try:
        r = subprocess.run(["curl", "-sS", "--max-time", str(timeout)] + args,
                           capture_output=True, text=True, timeout=timeout + 15)
    except subprocess.TimeoutExpired:
        return None
    if r.returncode != 0:
        return None
    return r.stdout


def _json(out):
    if not out:
        return {"success": 0, "error": "sem resposta"}
    out = out.strip()
    try:
        return json.loads(out)
    except Exception:
        i = out.find("{")
        if i >= 0:
            try:
                return json.loads(out[i:])
            except Exception:
                pass
        return {"success": 0, "error": out[:160]}


def carregar_cache():
    if not CACHE.exists():
        return {}
    try:
        return json.load(open(CACHE))
    except Exception:
        return {}


def salvar_cache(envs):
    CACHE.parent.mkdir(parents=True, exist_ok=True)
    CACHE.write_text(json.dumps(envs, indent=2))
    CACHE.chmod(0o600)


def profile(remix_id, remix_key):
    """Consulta /eapi/user/profile e devolve (ok, hoje, limite, erro)."""
    # /eapi/user/profile responde GET (POST devolve "Requested page not found")
    out = _curl(["-X", "GET", f"{DOMINIO}/eapi/user/profile",
                 "-H", f"User-Agent: {UA}",
                 "-b", f"remix_userid={remix_id}; remix_userkey={remix_key}"],
                timeout=30)
    d = _json(out)
    if d.get("success"):
        u = d.get("user") or {}
        return True, u.get("downloads_today") or 0, u.get("downloads_limit") or 0, ""
    return False, 0, 0, str(d.get("error") or "desconhecido")


def login(email, password):
    """Login por e-mail/senha -> (remix_id, remix_key) ou (None, erro)."""
    out = _curl(["-X", "POST", f"{DOMINIO}/eapi/user/login",
                 "-H", f"User-Agent: {UA}",
                 "--data-urlencode", f"email={email}",
                 "--data-urlencode", f"password={password}"], timeout=40)
    d = _json(out)
    if not d.get("success"):
        return None, None, str(d.get("error") or "login falhou")
    u = d.get("user") or {}
    rid, rkey = u.get("id"), u.get("remix_userkey")
    if not rid or not rkey:
        return None, None, "login ok mas sem remix_id/remix_userkey"
    return str(rid), str(rkey), ""


def gravar_yaml(alias, email, remix_id, remix_key):
    """Atualiza (ou cria) a entrada no YAML de credenciais, preservando as outras."""
    txt = CREDS_YAML.read_text(encoding="utf-8") if CREDS_YAML.exists() else ""
    bloco = (f"- alias: {alias}\n"
             f"  email: '{email}'\n"
             f"  remix_id: '{remix_id}'\n"
             f"  remix_key: '{remix_key}'\n")
    # remove entrada anterior do mesmo alias
    partes = re.split(r"(?m)^(?=- alias: )", txt)
    restantes = [p for p in partes if not re.match(rf"- alias:\s*{re.escape(alias)}\b", p)]
    novo = "\n".join(r for r in restantes if r.strip())
    if not novo.endswith("\n"):
        novo += "\n"
    CREDS_YAML.write_text(novo + bloco, encoding="utf-8")
    CREDS_YAML.chmod(0o600)


# --------------------------------------------------------------------------
def cmd_list(a):
    envs = carregar_cache()
    print("Cache:", CACHE)
    if not envs:
        print("  (vazio)")
    for alias in ALIASES:
        e = envs.get(alias)
        if e:
            print(f"  {alias:6s} id={e.get('ZLIB_REMIX_ID')}  key=...{str(e.get('ZLIB_REMIX_KEY'))[-4:]}")
        else:
            print(f"  {alias:6s} SEM CREDENCIAL")
    return 0


def cmd_verify(a):
    envs = carregar_cache()
    ok_total = 0
    for alias in ALIASES:
        e = envs.get(alias)
        if not e:
            print(f"  {alias:6s} DESCONECTADA  (sem entrada no cache)")
            continue
        ok, hoje, lim, err = profile(e["ZLIB_REMIX_ID"], e["ZLIB_REMIX_KEY"])
        if ok:
            ok_total += 1
            print(f"  {alias:6s} OK  id={e['ZLIB_REMIX_ID']}  "
                  f"hoje={hoje}/{lim}  resta={max(0, lim - hoje)}")
        else:
            print(f"  {alias:6s} DESCONECTADA  (id={e['ZLIB_REMIX_ID']})  erro={err}")
    print(f"\n{ok_total} conta(s) ativa(s) de {len(ALIASES)}")
    return 0


def cmd_reconnect(a):
    password = a.password or os.environ.get("ZLIB_PASSWORD")
    if not password:
        print("ERRO: senha ausente. Use ZLIB_PASSWORD=<senha> no ambiente.",
              file=sys.stderr)
        return 2
    rid, rkey, err = login(a.email, password)
    if not rid:
        print(f"ERRO: login falhou para {a.email}: {err}", file=sys.stderr)
        return 2
    ok, hoje, lim, perr = profile(rid, rkey)
    if not ok:
        print(f"ERRO: login ok, mas o perfil nao respondeu: {perr}", file=sys.stderr)
        return 2
    envs = carregar_cache()
    envs[a.alias] = {"ZLIB_REMIX_ID": rid, "ZLIB_REMIX_KEY": rkey}
    salvar_cache(envs)
    try:
        gravar_yaml(a.alias, a.email, rid, rkey)
    except Exception as ex:  # YAML e' convenience; o cache e' a fonte real
        print(f"AVISO: nao consegui atualizar o YAML: {ex}", file=sys.stderr)
    print(f"RECONECTADA: {a.alias}  id={rid}  key=...{rkey[-4:]}  "
          f"hoje={hoje}/{lim}  resta={max(0, lim - hoje)}")
    return 0


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--verify", action="store_true", help="testa todas as contas")
    ap.add_argument("--list", action="store_true", help="mostra o cache")
    ap.add_argument("--alias", help="alias alvo (zlib, zlib2, zlib3, zlib4)")
    ap.add_argument("--email", help="e-mail da conta")
    ap.add_argument("--password", help="senha (prefira ZLIB_PASSWORD no ambiente)")
    a = ap.parse_args()
    if a.alias and a.email:
        return cmd_reconnect(a)
    if a.verify:
        return cmd_verify(a)
    return cmd_list(a)


if __name__ == "__main__":
    sys.exit(main())
