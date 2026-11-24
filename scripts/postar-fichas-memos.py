#!/usr/bin/env python3
"""Posta fichas de leitura no Memos e grava memo_id no frontmatter.

Workaround: o MagicDNS do Tailscale esta desligado nesta LXC, entao o hostname
memos.ison-duck.ts.net nao resolve. Usa o endereco IPv6 direto do tailnet.

Uso: python3 scripts/postar-fichas-memos.py <arquivo.md> [<arquivo.md> ...] --tags "a,b"
"""
import json
import re
import sys
import urllib.request

ENV = "data/config-backup/memos/memos.env"
# O MagicDNS do Tailscale esta desligado nesta LXC e o IPv4 do tailnet nao
# responde (curl -> timeout). O IPv6 do host memos responde. Ordem de tentativa:
CANDIDATOS = [
    "http://[2804:7f0:6942:a634:e221:6309:fdc:f815]",
    "http://100.103.64.20",
    "http://memos.ison-duck.ts.net",
]


def carrega_env(path=ENV):
    d = {}
    with open(path, encoding="utf-8") as fh:
        for linha in fh:
            linha = linha.strip()
            if not linha or linha.startswith("#") or "=" not in linha:
                continue
            k, v = linha.split("=", 1)
            d[k.strip()] = v.strip().strip('"').strip("'")
    return d


def separa_frontmatter(txt):
    linhas = txt.split("\n")
    if linhas and linhas[0].strip() == "---":
        for i in range(1, len(linhas)):
            if linhas[i].strip() == "---":
                return "\n".join(linhas[1:i]), "\n".join(linhas[i + 1:])
    return None, txt


_BASE = {"url": None}


def _descobre_base(pat):
    """Testa os candidatos e fixa o primeiro que responder a listagem."""
    if _BASE["url"]:
        return _BASE["url"]
    for base in CANDIDATOS:
        req = urllib.request.Request(
            base + "/api/v1/memos?pageSize=1",
            headers={"Authorization": "Bearer " + pat})
        try:
            with urllib.request.urlopen(req, timeout=20) as resp:
                if resp.status == 200:
                    _BASE["url"] = base
                    return base
        except Exception:  # noqa: BLE001
            continue
    raise RuntimeError("nenhum endpoint do Memos respondeu")


def posta(conteudo, pat, vis="PRIVATE"):
    base = _descobre_base(pat)
    corpo = json.dumps({"content": conteudo, "visibility": vis},
                       ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(
        base + "/api/v1/memos", data=corpo, method="POST",
        headers={"Authorization": "Bearer " + pat,
                 "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=90) as resp:
        return json.loads(resp.read().decode("utf-8"))


def main():
    args = sys.argv[1:]
    tags = ""
    if "--tags" in args:
        i = args.index("--tags")
        tags = args[i + 1]
        del args[i:i + 2]
    arquivos = args
    if not arquivos:
        print("uso: postar-fichas-memos.py <arquivo.md> ... --tags 'a,b'", file=sys.stderr)
        return 2

    pat = carrega_env().get("MEMOS_PAT", "")
    if not pat:
        print("ERRO: MEMOS_PAT vazio", file=sys.stderr)
        return 2

    linha_tags = " ".join("#" + t.strip() for t in tags.split(",") if t.strip())

    for arq in arquivos:
        with open(arq, encoding="utf-8") as fh:
            bruto = fh.read()
        front, corpo = separa_frontmatter(bruto)
        if front is None:
            print("PULA (sem frontmatter):", arq)
            continue
        if re.search(r"^memo_id:", front, re.M):
            print("PULA (ja tem memo_id):", arq)
            continue
        if len(corpo.encode("utf-8")) > 108192:
            print("PULA (>106KB):", arq)
            continue
        conteudo = corpo.strip() + "\n\n" + linha_tags + "\n"
        try:
            resp = posta(conteudo, pat)
        except Exception as exc:  # noqa: BLE001
            print("FALHA", arq, "->", exc)
            continue
        nome = resp.get("name", "")
        print("OK", arq, "->", nome)
        novo_front = front.rstrip("\n") + '\nmemo_id: "%s"' % nome
        with open(arq, "w", encoding="utf-8") as fh:
            fh.write("---\n" + novo_front + "\n---\n" + corpo)
    return 0


if __name__ == "__main__":
    sys.exit(main())
