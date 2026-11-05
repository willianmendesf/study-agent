#!/usr/bin/env python3
"""Envia ebooks ao BookOrbit (LXC 26) via API HTTP — caminho sem SSH.

CONTEXTO (2026-11-05): o `biblioteca-push.sh` usa rsync por SSH para
`biblioteca@192.168.15.26`, mas nesta LXC a chave `~/.ssh/biblioteca_orbit`
NAO EXISTE → `Permission denied (publickey,password)`. O caminho por HTTP
funciona: o app BookOrbit (Vue) expoe `POST /api/v1/libraries/{id}/upload`.

PROTOCOLO (extraido do bundle `BookUploadModal-CkXA99kz.js` do app):
  POST /api/v1/libraries/{libraryId}/upload[?folderId={id}]
  Headers: Authorization: Bearer <accessToken>
  Body: multipart/form-data, campo `file`
  Resposta 201: {"bookId": ...}

AUTENTICACAO:
  POST /api/v1/auth/login  {"username":..., "password":...} → {"accessToken":...}
  O token dura 15 min (accessTokenExpiresAt).

PERMISSAO NECESSARIA: `library_upload` na conta. Sem ela → 403
"Missing permission: library_upload". A conta `study-agent` foi criada
(2026-11-05) mas esta como VIEWER na biblioteca 1 — precisa ser promovida a
EDITOR/OWNER por um admin do app (ou via `manage_libraries`).

O ebook original NUNCA fica versionado em data/: este script faz o upload e
so entao apaga o local. Se o upload falhar, o arquivo permanece em _incoming/.

Uso:
  python3 scripts/orbit-upload.py --file X.epub [--autor "Jane Austen"]
  python3 scripts/orbit-upload.py --file X.epub --dry
  python3 scripts/orbit-upload.py --check          # só testa permissões
"""
import argparse
import json
import os
import sys
import urllib.error
import urllib.request
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ORBIT_URL = os.environ.get("ORBIT_URL", "http://192.168.15.26")
USER = os.environ.get("ORBIT_USER", "study-agent")
PASS = os.environ.get("ORBIT_PASS", "AgenteEstante2026!")
LIB_ID = os.environ.get("ORBIT_LIBRARY_ID", "1")

CREDS = ROOT / "data" / "perfil" / "bibliotecario" / "orbit-creds.json"


def _cred():
    """Credenciais: env > arquivo local (gitignored) > default."""
    if os.environ.get("ORBIT_USER") and os.environ.get("ORBIT_PASS"):
        return USER, PASS
    if CREDS.exists():
        d = json.loads(CREDS.read_text(encoding="utf-8"))
        return d.get("username", USER), d.get("password", PASS)
    return USER, PASS


def _post_json(url, payload, token=None, timeout=30):
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, method="POST")
    req.add_header("Content-Type", "application/json")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", "ignore")
        try:
            return e.code, json.loads(body)
        except Exception:
            return e.code, {"message": body[:300]}


def _get_json(url, token, timeout=30):
    req = urllib.request.Request(url, method="GET")
    req.add_header("Authorization", f"Bearer {token}")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", "ignore")
        try:
            return e.code, json.loads(body)
        except Exception:
            return e.code, {"message": body[:300]}


def login():
    u, p = _cred()
    st, d = _post_json(f"{ORBIT_URL}/api/v1/auth/login",
                       {"username": u, "password": p})
    if st != 200 or "accessToken" not in d:
        raise SystemExit(f"ERRO: login falhou ({st}): {str(d)[:200]}")
    return d["accessToken"], d.get("user", {})


def upload(ebook: Path, token: str, folder_id=None, autor=""):
    """Upload multipart/form-data SEM dependencia externa (stdlib only)."""
    boundary = "----studyagent" + uuid.uuid4().hex
    nome = autor or ebook.stem
    filename = f"{nome}{ebook.suffix}"
    body = bytearray()
    body += f"--{boundary}\r\n".encode()
    body += (f'Content-Disposition: form-data; name="file"; '
             f'filename="{filename}"\r\n').encode()
    body += b"Content-Type: application/octet-stream\r\n\r\n"
    body += ebook.read_bytes()
    body += f"\r\n--{boundary}--\r\n".encode()

    url = f"{ORBIT_URL}/api/v1/libraries/{LIB_ID}/upload"
    if folder_id:
        url += f"?folderId={folder_id}"
    req = urllib.request.Request(url, data=bytes(body), method="POST")
    req.add_header("Content-Type", f"multipart/form-data; boundary={boundary}")
    req.add_header("Authorization", f"Bearer {token}")
    try:
        with urllib.request.urlopen(req, timeout=600) as r:
            return r.status, json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        b = e.read().decode("utf-8", "ignore")
        try:
            return e.code, json.loads(b)
        except Exception:
            return e.code, {"message": b[:300]}
    except Exception as e:
        return 0, {"message": f"{type(e).__name__}: {str(e)[:200]}"}


def _probe_upload_sem_arquivo(token: str):
    """POST de upload SEM o campo 'file' — nao grava nada no BookOrbit.

    Serve para distinguir "sem permissao" (403) de "com permissao" (400 por
    arquivo ausente). Antes (2026-11-05) o probe subia um arquivo de 1 byte e
    deixava um livro-lixo na biblioteca quando a permissao era concedida.
    """
    boundary = "----studyagent-probe" + uuid.uuid4().hex
    body = (f"--{boundary}\r\n"
            f'Content-Disposition: form-data; name="semarquivo"\r\n\r\n'
            f"probe\r\n--{boundary}--\r\n").encode("utf-8")
    req = urllib.request.Request(
        f"{ORBIT_URL}/api/v1/libraries/{LIB_ID}/upload", data=body, method="POST")
    req.add_header("Content-Type", f"multipart/form-data; boundary={boundary}")
    req.add_header("Authorization", f"Bearer {token}")
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return r.status, json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        b = e.read().decode("utf-8", "ignore")
        try:
            return e.code, json.loads(b)
        except Exception:
            return e.code, {"message": b[:300]}
    except Exception as e:
        return 0, {"message": f"{type(e).__name__}: {str(e)[:200]}"}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--file")
    ap.add_argument("--autor", default="")
    ap.add_argument("--dry", action="store_true")
    ap.add_argument("--check", action="store_true",
                    help="testa login + permissao de upload sem enviar arquivo")
    args = ap.parse_args()

    try:
        token, user = login()
    except SystemExit as e:
        print(str(e))
        return 2
    print(f"login OK: {user.get('username')} (id {user.get('id')})")

    st, libs = _get_json(f"{ORBIT_URL}/api/v1/libraries", token)
    if st == 200 and isinstance(libs, list):
        for l in libs:
            print(f"  biblioteca {l['id']}: {l['name']} | acesso={l['accessLevel']} "
                  f"| {l.get('bookCount')} livros | "
                  f"pastas={[f['path'] for f in l.get('folders', [])]}")

    if args.check:
        # CHECAGEM SOMENTE LEITURA (2026-11-05).
        # Antes: subia um arquivo de 1 byte ("probe") na pasta /books para
        # testar a permissao -> quando a permissao fosse concedida, esse
        # probe virava um livro-lixo permanente na biblioteca (931 -> 932).
        # Agora o teste e' um POST de upload SEM o campo "file": o servidor
        # rejeita por FALTA DE PERMISSAO (403) antes de qualquer gravacao,
        # e se a permissao existir responde 400 (arquivo ausente) sem criar
        # livro. NADA e' gravado em nenhum dos dois casos.
        st_me, me = _get_json(f"{ORBIT_URL}/api/v1/auth/me", token, timeout=20)
        perms = (me.get("permissions") or []) if isinstance(me, dict) else []
        print(f"  permissoes da conta: {perms if perms else '(nenhuma global)'}")

        nivel = None
        if st == 200 and isinstance(libs, list):
            for l in libs:
                if str(l.get("id")) == str(LIB_ID):
                    nivel = (l.get("accessLevel") or "").lower()
        print(f"  biblioteca alvo {LIB_ID}: acesso={nivel}")

        st_probe, d_probe = _probe_upload_sem_arquivo(token)
        print(f"  probe de escrita (sem arquivo) -> HTTP {st_probe}: "
              f"{str(d_probe)[:160]}")

        if st_probe == 403:
            print("  >> FALTA a permissao 'library_upload' nesta conta.")
            return 3
        if st_probe in (400, 422):
            # Chegou na validacao do arquivo => a permissao de escrita EXISTE.
            print("  >> permissao de escrita LIBERADA (upload pode seguir).")
            return 0
        if st_probe in (200, 201):
            print("  >> permissao de escrita LIBERADA.")
            return 0
        print("  >> nao foi possivel determinar o acesso; upload bloqueado.")
        return 3

    if not args.file:
        ap.error("--file e obrigatorio (ou use --check)")
    p = Path(args.file)
    if not p.exists():
        ap.error(f"arquivo nao existe: {p}")

    if args.dry:
        print(f"[dry] enviaria {p.name} ({p.stat().st_size//1024} KB) "
              f"como autor='{args.autor}'")
        return 0

    st, d = upload(p, token, folder_id=1, autor=args.autor)
    print(f"upload -> HTTP {st}: {json.dumps(d, ensure_ascii=False)[:300]}")
    if st in (200, 201):
        print("OK: enviado ao BookOrbit (disponivel no app de leitura)")
        return 0
    if st == 403:
        print(">> FALTA a permissao 'library_upload' nesta conta. "
              "O arquivo local foi PRESERVADO.")
        return 3
    print(">> upload falhou; o arquivo local foi PRESERVADO.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
