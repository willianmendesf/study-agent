#!/usr/bin/env python3
"""
memos-curadoria.py — curadoria do Memos (Bibliotecário)
1. Testa empiricamente como o Memos indexa tags com ':' vs '/'
2. Gera a proposta de re-tag dos memos do study-agent
3. Aplica (--apply) com backup prévio
"""
import json, subprocess, sys, os, re, collections, urllib.parse

ENV = "/home/willian/study-agent/data/config-backup/memos/memos.env"
BASE = PAT = None
for line in open(ENV):
    line = line.strip()
    if line.startswith("MEMOS_URL="):
        BASE = line.split("=", 1)[1].strip().strip('"').strip("'").rstrip("/")
    if line.startswith("MEMOS_PAT="):
        PAT = line.split("=", 1)[1].strip().strip('"').strip("'")

H = [f"Authorization: Bearer {PAT}"]


def api(method, path, body=None):
    cmd = ["curl", "-sS", "--connect-timeout", "8", "--max-time", "90", "-X", method,
           f"{BASE}{path}", "-H", "Authorization: Bearer " + PAT]
    if body is not None:
        cmd += ["-H", "Content-Type: application/json", "--data-binary", json.dumps(body, ensure_ascii=False)]
    p = subprocess.run(cmd, capture_output=True, text=True)
    if p.returncode != 0:
        raise RuntimeError(p.stderr)
    try:
        return json.loads(p.stdout)
    except Exception:
        return {"_raw": p.stdout[:500]}


def dump_all():
    out, token = [], None
    while True:
        path = "/api/v1/memos?pageSize=200"
        if token:
            path += "&pageToken=" + urllib.parse.quote(token)
        d = api("GET", path)
        memos = d.get("memos") or []
        out.extend(memos)
        token = d.get("nextPageToken")
        if not token or not memos:
            break
    return out


# ---------- 1. TESTE DE NAMESPACING ----------
def teste_namespace():
    print("=== TESTE 1: como o Memos indexa tags ===", flush=True)
    probe = ("# teste-namespace\n\nprobe\n\n#tipo:plano #area:teologia "
             "#tipo/planejado #area/teologia #plano_simples")
    d = api("POST", "/api/v1/memos", {"content": probe, "visibility": "PRIVATE"})
    name = d.get("name")
    got = api("GET", f"/api/v1/memos/{name}")
    tags = got.get("tags")
    if tags is None:
        m = api("GET", f"/api/v1/memos/{name}")
        tags = m.get("tags")
    print("  tags retornadas:", tags, flush=True)
    # limpa
    api("PATCH", f"/api/v1/memos/{name}", {"content": "", "visibility": "PRIVATE"})
    api("DELETE", f"/api/v1/memos/{name}")
    print("  probe removido.", flush=True)
    return tags


# ---------- 2. CLASSIFICADOR DE TAGS ----------
AREAS = {"teologia", "curriculo", "portugues", "literatura", "producao", "geral"}
TIPOS = {"plano", "exegese", "devocional", "guia", "mapa", "simulado", "relatorio",
         "nota", "ficha", "indice", "transcricao", "exercicio", "resumo", "esboco",
         "aula", "catalogo", "relatorio-quiz"}


def reclassificar(tags, content, title):
    """tags antigas (Memos) -> (novas tags, motivo). Taxonomia PLANA (sem '/')."""
    old = set(tags or [])
    new = set()
    area = tipo = fonte = livro = serie = persona = None

    for t in old:
        if "/" in t:
            eixo, _, val = t.partition("/")
            val = val.strip()
            if not val:
                continue
            if eixo == "estudo":
                area = area or val
            elif eixo == "tipo":
                tipo = tipo or val
            elif eixo == "fonte":
                fonte = fonte or val
            elif eixo == "livro":
                livro = livro or val
            elif eixo == "serie":
                serie = serie or val
            elif eixo == "persona":
                persona = persona or val
            elif eixo == "aula":
                tipo = tipo or "aula"
            else:
                new.add(val)  # eixo desconhecido -> conserva o valor
        else:
            if t in ("externo", "externo/projeto-terceiro"):
                continue
            if t == "study-agent":
                continue
            if re.fullmatch(r"[0-9][0-9\-]*", t):
                continue  # lixo numérico (ids de bloco/lista)
            if t in AREAS:
                area = area or t
            elif t in TIPOS:
                tipo = tipo or t
            else:
                new.add(t)

    # inferência por título/conteúdo quando faltou
    blob = (title + " " + content[:1200]).lower()
    if area is None:
        for a in ("teologia", "literatura", "portugues", "curriculo", "producao", "geral"):
            if a in blob:
                area = a
                break
    if tipo is None:
        for tp in ("plano", "exegese", "devocional", "guia", "mapa", "simulado",
                   "relatorio", "ficha", "indice", "transcricao", "exercicio", "resumo"):
            if tp in blob:
                tipo = tp
                break
    if area and area not in AREAS:
        area = None
    if tipo and tipo not in TIPOS:
        tipo = None

    out = set(new)
    if area:  out.add(area)
    if tipo:  out.add(tipo)
    if fonte: out.add(fonte)
    if livro: out.add(livro)
    if serie: out.add(serie)
    if persona: out.add(persona)
    return out


# ---------- 3. APLICAÇÃO ----------
def aplicar(memos, dry=True):
    json.dump(memos, open("/tmp/memos-full.json", "w"), ensure_ascii=False)
    own = [m for m in memos if "externo" not in (m.get("tags") or [])]
    # backup local durável
    bak = "/home/willian/study-agent/data/historico/memos/backup-memos.json"
    os.makedirs(os.path.dirname(bak), exist_ok=True)
    json.dump(own, open(bak, "w"), ensure_ascii=False, indent=1)
    print(f"BACKUP: {len(own)} memos do study-agent em {bak}", flush=True)

    # nova lista de tags de cada memo (tags ficam no corpo como hashtags no Memos)
    propuesta = []
    for m in own:
        content = m.get("content") or ""
        old_tags = m.get("tags") or []
        # remove hashtags soltas do corpo que viraram tag (numericos)
        body = content
        limpas = []
        for tag in old_tags:
            if re.fullmatch(r"[0-9][0-9\-]*", tag):
                body = re.sub(r"[ \t]*#" + re.escape(tag) + r"\b", "", body)
        title = content.strip().split("\n")[0].strip()
        novas = reclassificar(old_tags, body, title)
        if not novas:
            novas = {"nota"}
        proposta.append((m["name"], title, sorted(old_tags), sorted(novas), body))

    with open("/tmp/proposta-retag.json", "w") as f:
        json.dump([{"name": p[0], "title": p[1], "old": p[2], "new": p[3]} for p in propuesta],
                  f, ensure_ascii=False, indent=1)

    print(f"\n=== PROPOSTA (dry={dry}) ===", flush=True)
    contagem = collections.Counter()
    for name, title, old, new, _ in propuesta:
        removidas = sorted(set(old) - set(new))
        if removidas:
            print(f"  {name} | {title[:60]}")
            print(f"     - {removidas}")
            print(f"     + {new}")
        for t in new:
            contagem[t] += 1
    print("\n=== NOVA TAXONOMIA (contagem) ===")
    for t, c in contagem.most_common():
        print(f"  {c:4d}  {t}")

    if dry:
        print("\n(dry-run — use --apply)")
        return

    print("\n=== APLICANDO ===", flush=True)
    ok = fail = 0
    for i, (name, title, old, new, body) in enumerate(propuesta, 1):
        # monta corpo: titulo + corpo sem hashtags numericas + hashtags novas no fim
        core = body.rstrip()
        core = re.sub(r"\n{3,}", "\n\n", core)
        core = re.sub(r"(\s*#[\w\-/]+)+\s*$", "\n", core)
        hashtags = " ".join(f"#{t}" for t in new)
        payload = f"{core}\n\n{hashtags}"
        try:
            d = api("PATCH", f"/api/v1/memos/{name}", {"content": payload, "visibility": "PRIVATE"})
            if "name" in d or d.get("content"):
                ok += 1
            else:
                fail += 1
                print(f"  FALHA {name}: {str(d)[:200]}")
        except Exception as e:
            fail += 1
            print(f"  ERRO {name}: {e}")
        if i % 20 == 0:
            print(f"  ... {i}/{len(propposta)} (ok={ok} fail={fail})", flush=True)
    print(f"\nRESULTADO: ok={ok} fail={fail}")


if __name__ == "__main__":
    dry = "--apply" not in sys.argv
    if "--test" in sys.argv:
        teste_namespace()
        sys.exit(0)
    memos = dump_all()
    print(f"memos totais: {len(memos)}", flush=True)
    aplicar(memos, dry=dry)
