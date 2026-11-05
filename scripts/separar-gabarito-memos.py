#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SEPARA PROVA DE GABARITO NOS SIMULADOS DO MEMOS
=================================================
Problema (medido 2026-11-05, por auditoria da API): 11 dos 12 simulados no
Memos vazam o gabarito por DUAS vias:
  (a) o `<details><summary>Gabarito</summary>` NAO renderiza no app -> vira
      texto puro, com a resposta e o "onde reler";
  (b) 9 dos 11 marcam a alternativa correta com "✅" na LINHA DA OPCAO
      (o `✅` fica na prova, nao dentro do details).

Decisao do William (2026-11-05): "ajuste os simulados"
  -> o memo da SIMULADO vira a PROVA (sem details, sem "✅");
  -> o GABARITO vai para um memo SEPARADO (tag `tipo/gabarito`), que so
     deve ser aberto DEPOIS de fazer a prova.

Regras de seguranca:
  - so toca memo cujo creator == users/willianmendesf;
  - so toca memo com tag `tipo/simulado`;
  - so toca memo que realmente tem bloco de gabarito;
  - backup completo antes de qualquer escrita.

Uso:
  python3 scripts/separar-gabarito-memos.py --auditar            # so relata
  python3 scripts/separar-gabarito-memos.py --aplicar --confirmar # escreve
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import re
import time
from pathlib import Path

ROOT = Path("/home/willian/study-agent")
spec = importlib.util.spec_from_file_location(
    "curador", ROOT / "scripts/curador-memos.py")
cur = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cur)

MEU = "users/willianmendesf"
BACKUP = ROOT / "data/perfil/bibliotecario/backups-memos"
CACHE = Path("/tmp/memos-todos.json")

RE_QHEAD = re.compile(r"^###\s*Q(\d+)", re.M)
RE_OPT_MARCA = re.compile(r"^(\s*-\s*[A-E]\)\s*.*?)\s*✅+\s*$", re.M)
RE_ANY_DETAILS = re.compile(r"<details\b[^>]*>.*?</details>", re.S)

# Tabela-resposta: cabecalho | # | Resposta | ... |  e linhas | n | LETRA | ...
RE_TAB_RESPOSTA_HEAD = re.compile(
    r"^\|\s*#\s*\|\s*(?:Resposta|Gabarito|Correta|Solu[çc][ãa]o)\s*\|", re.I)
RE_TAB_LINHA = re.compile(r"^\|\s*\d+\s*\|\s*[A-E]\s*\|")
# titulo de secao que anuncia a tabela-resposta
RE_SEC_TAB = re.compile(
    r"^#+\s*.*(?:Gabarito\s+(?:Comentado|Resumido)|Resumo de (?:Gabarito|Respostas))",
    re.I)


# ------------------------------------------------------------------ helpers
def carregar_todos(forcar=False):
    """Usa o cache local se existir (a listagem da API leva ~70s no tailnet)."""
    if not forcar and CACHE.exists():
        return json.loads(CACHE.read_text(encoding="utf-8"))
    cur.carregar_env()
    todos = cur.listar()
    CACHE.write_text(json.dumps(todos, ensure_ascii=False), encoding="utf-8")
    return todos


def _titulo_prova(conteudo: str) -> str:
    m = re.search(r"^#\s+(.+)$", conteudo, re.M)
    if m:
        return m.group(1).strip()
    return conteudo.strip().splitlines()[0]


def _num_q_ate(texto: str, headers) -> int:
    n = 0
    for pos, num in headers:
        if pos < len(texto):
            n = num
        else:
            break
    return n


def extrair_tabela_resposta(prova: str):
    """Remove da PROVA a tabela-resposta (| # | Resposta | ...) e devolve
    (prova_sem_tabela, bloco_tabela_md). A tabela so pode ficar no gabarito.
    Medido 2026-11-05: M1 e M5 tinham '## Gabarito Resumido' com as letras."""
    linhas = prova.splitlines()
    # acha o cabecalho da tabela-resposta
    idx_head = None
    for i, l in enumerate(linhas):
        if RE_TAB_RESPOSTA_HEAD.match(l.strip()):
            idx_head = i
            break
    if idx_head is None:
        return prova, ""

    # a partir do cabecalho, anda enquanto forem linhas de tabela
    i = idx_head
    while i < len(linhas) and linhas[i].strip().startswith("|"):
        i += 1
    fim = i
    # recua: a tabela e' a ultima coisa; remove ate o fim ou ate a proxima secao
    # que nao seja tabela nem branco
    j = idx_head
    while j > 0 and (linhas[j - 1].strip().startswith("|")
                     or not linhas[j - 1].strip()):
        j -= 1
    inicio = j

    bloco = "\n".join(linhas[inicio:fim]).strip()
    # remove o titulo da secao (se houver) junto com a tabela
    titulo_secao = ""
    k = inicio - 1
    if k >= 0 and RE_SEC_TAB.match(linhas[k].strip()):
        titulo_secao = linhas[k].strip()
        inicio = k

    novas = linhas[:inicio] + linhas[fim:]
    # limpa linhas em branco duplicadas no ponto da remocao
    saida = "\n".join(novas)
    saida = re.sub(r"\n{3,}", "\n\n", saida).strip() + "\n"

    bloco_md = ""
    if titulo_secao:
        bloco_md += "## " + titulo_secao.lstrip("#").strip() + "\n\n"
    bloco_md += bloco + "\n"
    return saida, bloco_md


def extrair_gabarito(conteudo: str):
    """Separa prova e gabarito. Devolve (prova, gabarito_md, n_blocos)."""
    matches = list(RE_ANY_DETAILS.finditer(conteudo))
    if not matches:
        return conteudo, "", 0

    headers = [(m.start(), int(m.group(1))) for m in RE_QHEAD.finditer(conteudo)]
    usa_header = len(headers) > 0

    prova_parts, gab = [], []
    idx = 0
    seq = 0
    for m in matches:
        prova_parts.append(conteudo[idx:m.start()])
        bloco = m.group(0)
        if "Gabarito" in bloco:
            seq += 1
            inner = re.sub(r"<details\b[^>]*>", "", bloco)
            inner = re.sub(r"</details>", "", inner)
            inner = re.sub(r"<summary>\s*Gabarito\s*</summary>", "", inner)
            num = (_num_q_ate(conteudo[:m.start()], headers)
                   if usa_header else seq)
            gab.append((num, inner.strip()))
        else:
            prova_parts.append(bloco)   # details nao-gabarito: preserva
        idx = m.end()
    prova_parts.append(conteudo[idx:])
    prova = "".join(prova_parts)

    # limpa marcadores ✅ das opções da PROVA
    prova = RE_OPT_MARCA.sub(r"\1", prova)
    prova = re.sub(r"\n{3,}", "\n\n", prova).strip() + "\n"

    if not gab:
        prova, _tab = extrair_tabela_resposta(prova)
        return prova, "", 0

    prova, bloco_tabela = extrair_tabela_resposta(prova)

    L = ["# 🔑 Gabarito — " + _titulo_prova(conteudo), ""]
    for num, inner in gab:
        L.append(f"## Q{num}")
        L.append("")
        L.append(inner.strip())
        L.append("")
    if bloco_tabela:
        L.append("---")
        L.append("")
        L.append(bloco_tabela.strip())
        L.append("")
    return prova, "\n".join(L).strip() + "\n", len(gab)

def tag_area(tags):
    for t in tags:
        if t.startswith("estudo/") and t != "estudo":
            return t
    return "estudo/geral"


def tag_fonte(tags):
    for t in tags:
        if t.startswith("fonte/"):
            return t
    return None


# ------------------------------------------------------------------ main
def vazamentos(prova: str):
    """Detecta qualquer forma de gabarito remanescente na PROVA."""
    achados = []
    n = len(RE_OPT_MARCA.findall(prova))
    if n:
        achados.append(f"{n} opcao(is) marcada(s) com ✅")
    n = len(RE_ANY_DETAILS.findall(prova))
    if n:
        achados.append(f"{n} bloco(s) <details>")
    for l in prova.splitlines():
        if RE_TAB_RESPOSTA_HEAD.match(l.strip()):
            achados.append("tabela-resposta (coluna Resposta)")
            break
    n = len([l for l in prova.splitlines() if RE_TAB_LINHA.match(l.strip())])
    if n:
        achados.append(f"{n} linha(s) de tabela no formato 'num | LETRA'")
    # titulo de secao que anuncia gabarito. O "Simulado Completo" tem uma
    # secao 'Gabarito geral' que NAO e resposta de questao (e' pontuacao) —
    # so conta se a secao tiver uma tabela de respostas ou '✅'.
    for l in prova.splitlines():
        if re.match(r"^#+\s*.*\bGabarito\b", l, re.I):
            ctx = "\n".join(prova.splitlines()[
                prova.splitlines().index(l):prova.splitlines().index(l) + 30])
            tem_resposta = (RE_TAB_LINHA.search(ctx)
                            or RE_OPT_MARCA.search(ctx))
            if tem_resposta:
                achados.append(f"titulo de secao '{l.strip()[:40]}' com respostas")
            break
    return achados


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--auditar", action="store_true")
    ap.add_argument("--aplicar", action="store_true")
    ap.add_argument("--confirmar", action="store_true")
    ap.add_argument("--refresh", action="store_true",
                    help="re-lista da API (ignora o cache)")
    ap.add_argument("--fonte-backup", action="store_true",
                    help="usa o backup pre-gabarito como fonte (idempotente)")
    args = ap.parse_args()
    if not args.auditar and not args.aplicar:
        args.auditar = True

    if args.fonte_backup:
        cur.carregar_env()          # as escritas (PATCH/POST) precisam do PAT
        bkp_path = BACKUP / "memos-2026-11-05-pre-gabarito.json"
        todos = json.loads(bkp_path.read_text(encoding="utf-8"))
        print(f"fonte: backup {bkp_path.name} ({len(todos)} memos)")
    else:
        todos = carregar_todos(forcar=args.refresh)
    sims = [m for m in todos
            if (m.get("creator") or "") == MEU
            and "tipo/simulado" in cur.tags_de(m)]

    # mapa titulo -> memo de gabarito ja existente (idempotencia)
    # precisa do estado ATUAL da API (o backup pre-gabarito nao tem os gabaritos)
    if args.fonte_backup:
        gabs_fonte = carregar_todos(forcar=False)
    else:
        gabs_fonte = todos
    gabs_existentes = {}
    for m in gabs_fonte:
        if (m.get("creator") or "") != MEU:
            continue
        if "tipo/gabarito" not in cur.tags_de(m):
            continue
        t = (m.get("content") or "").splitlines()[0]
        if t.startswith("# 🔑 Gabarito — "):
            gabs_existentes[t[len("# 🔑 Gabarito — "):].strip()] = m
    print(f"gabaritos ja existentes: {len(gabs_existentes)}")

    plano = []
    for m in sims:
        c = m.get("content") or ""
        prova, gab, nq = extrair_gabarito(c)
        tags = cur.tags_de(m)
        vaz = vazamentos(prova)
        plano.append({
            "uid": cur.uid(m),
            "titulo": _titulo_prova(c),
            "n_blocos": nq,
            "prova": prova,
            "gabarito": gab,
            "vazamentos": vaz,
            "checks_fora": len(RE_OPT_MARCA.findall(prova)),
            "details_restantes": len(RE_ANY_DETAILS.findall(prova)),
            "tags": tags,
            "area": tag_area(tags),
            "fonte": tag_fonte(tags),
            "bytes_prova": len(prova),
            "bytes_gabarito": len(gab),
        })

    print(f"simulados Study-Agent: {len(plano)}\n")
    vazao = 0
    for p in plano:
        if p["n_blocos"] or p["vazamentos"]:
            vazao += 1
        marca = "VAZA" if (p["n_blocos"] or p["vazamentos"]) else "ok  "
        print(f"[{marca}] {p['uid']}  {p['titulo'][:44]}")
        print(f"        blocos={p['n_blocos']}  bytes prova={p['bytes_prova']} "
              f"gab={p['bytes_gabarito']}")
        if p["vazamentos"]:
            print(f"        VAZAMENTOS: {'; '.join(p['vazamentos'])}")
    print(f"\n==> {vazao} de {len(plano)} simulados com problema.")

    Path("/tmp/plano-gabarito.json").write_text(
        json.dumps(plano, ensure_ascii=False, indent=1), encoding="utf-8")

    if not args.aplicar:
        print("\n[auditoria] nada foi escrito.")
        return
    if not args.confirmar:
        print("\nUse --confirmar para escrever.")
        return

    # ---- backup antes de escrever
    BACKUP.mkdir(parents=True, exist_ok=True)
    bkp = BACKUP / "memos-2026-11-05-pre-gabarito.json"
    bkp.write_text(json.dumps(todos, ensure_ascii=False, indent=1),
                   encoding="utf-8")
    print(f"\nbackup: {bkp.relative_to(ROOT)}")

    feitos = []
    for p in plano:
        if not p["n_blocos"]:
            print(f"  pulado (sem gabarito): {p['titulo'][:40]}")
            continue

        # 1) PATCH do memo da prova (sem gabarito, sem check)
        r = cur.api("PATCH", f"/api/v1/memos/{p['uid']}",
                    {"content": p["prova"]})
        if "error" in r:
            print(f"  ERRO PATCH {p['uid']}: {str(r)[:160]}")
            continue
        print(f"  PATCH prova {p['uid']} ok")

        # 2) memo do gabarito: cria ou atualiza (idempotente)
        tags_gab = ["tipo/gabarito", p["area"], "study-agent"]
        if p["fonte"]:
            tags_gab.append(p["fonte"])
        aviso = ("\n> ⚠️ **Nao abra antes de fazer a prova.** "
                 "Este e o gabarito com a justificativa e o material para reler.\n")
        titulo_gab = p["gabarito"].split("\n", 1)[0]
        corpo_gab = p["gabarito"].split("\n", 1)[1] if "\n" in p["gabarito"] else ""
        corpo = (titulo_gab + aviso + corpo_gab).rstrip()
        corpo += "\n\n" + " ".join("#" + t for t in tags_gab) + "\n"

        existente = gabs_existentes.get(p["titulo"])
        if existente:
            uid_gab = cur.uid(existente)
            r2 = cur.api("PATCH", f"/api/v1/memos/{uid_gab}", {"content": corpo})
            ok = "error" not in r2
            print(f"  PATCH gabarito {uid_gab} {'ok' if ok else str(r2)[:120]}")
            if not ok:
                continue
        else:
            r2 = cur.api("POST", "/api/v1/memos",
                         {"content": corpo, "visibility": "PRIVATE"})
            if "name" not in r2:
                print(f"  ERRO POST gabarito: {str(r2)[:160]}")
                continue
            uid_gab = cur.uid(r2)
            print(f"  POST gabarito -> {uid_gab}")
        feitos.append({"prova": p["uid"], "gabarito": uid_gab,
                       "titulo": p["titulo"], "blocos": p["n_blocos"]})
        time.sleep(0.4)

    Path("/tmp/gabarito-postados.json").write_text(
        json.dumps(feitos, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"\nconcluido: {len(feitos)} simulados separados "
          f"({len(plano) - len(feitos)} sem gabarito / erro).")


if __name__ == "__main__":
    main()
