#!/usr/bin/env python3
"""Reorganizacao do Memos — v5 FINAL (8 trilhas) + gabarito FORA do Memos.

DECISAO DO WILLIAM (2026-11-05):
  "sem gabarito no memos ele e' seu, voce corrige, a prova, e informa se errei e
   como acertar e etc"

TRADUCAO OPERACIONAL:
  - Memos tem a PROVA (sem resposta) — 12 simulados.
  - Os 11 memos de GABARITO sao removidos do Memos.
  - O CONTEUDO deles (resposta + "Por que" + "Onde reler") e' salvo no data/
    em data/estudos/exercicios/gabaritos/<slug>.md — porque esse material rico
    SO EXISTE no Memos (medido: 11 memos, 51 KB, nao ha gabarito no repo).
  - O IAM passa a ser quem corrige: voce faz a prova, eu corrijo e te digo
    o que errou e como acertar.

Etapas:
  1. backup
  2. extrai os 11 gabaritos para o data/ (CONTEUDO RICO — nao se perde)
  3. apaga as 4 notas tecnicas da rampa (P1 = sim, aprovado)
  4. re-tagueia os 131 restantes (1 eixo = trilha)
  5. audita

NUNCA toca em memo de outro creator (o Memos e' compartilhado com a Fabiana).
"""
import importlib.util
import json
import re
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

spec = importlib.util.spec_from_file_location("cur", ROOT / "scripts" / "curador-memos.py")
cur = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cur)

BKPDIR = ROOT / "data" / "perfil" / "bibliotecario" / "backups-memos"
GABDIR = ROOT / "data" / "estudos" / "exercicios" / "gabaritos"
MEU = "users/willianmendesf"

# ---------------------------------------------------------------------------
# AS 8 TRILHAS (medidas em 143/143 — ver scripts/revalidar-taxonomia-memos-v5.py)
# ---------------------------------------------------------------------------
TRILHAS = [
    ("simulados",   re.compile(r"^\s*📝\s*simulad|^\s*#\s*SIMULAD", re.I)),
    ("gabaritos",   re.compile(r"gabarito", re.I)),
    ("estudo-ipb",  re.compile(r"\b(comit[eê]|comiss[aã]o|vocacional|autoavalia|matriz de cobertura|varia[cç][oõ]es de quest|perguntas advers|banco de perguntas|relat[oó]rio de|refer[eê]ncias|catalogo-acervo|acervo-audiovisual|mapa-progressao|fontes externas)\w*", re.I)),
    ("rampa-leitura", re.compile(r"\b(rampa|fic[cç][aã]o)\w*", re.I)),
    ("devocional",  re.compile(r"\b(devocional|devocion|medita|salmo \d|prov[eé]rb \d|adoracao e confissao)\w*", re.I)),
    ("aulas-portugues", re.compile(r"\b(AULA \d|vogal|consoant|alfabet|silab|acentu|ortograf|ditong|tritong|hiato|fonema|fonolog|pontuac|sintaxe|redacao|lexico|mapa-m1|mapa-m2|mapa-m3|m1\.|m2\.|m3\.)\w*", re.I)),
    ("exegese",     re.compile(r"\b(exegese|exeg[eé]tic|leitura pr[oó]pria|di[aá]logo com os autores|etapa 0|etapa 1|hermeneu|pericope|sint[aá]tica textual|conceitual|panor[aâ]mico|contextualiza|divis[aã]o de per[ií]copes|jejum|guia de estudo|guia-bolso)\w*", re.I)),
    ("plano-estudo", re.compile(r"\b(plano|roadmap|grade|roteiro|trajet|sequencia|cronograma|curriculo|ebd\b|ebdi|criancas|adolescente|descoberta|esboco)\w*", re.I)),
]

CORRECOES = {
    "GHnG6XAc7V9cn4kCB5XKpn": "plano-estudo",
    "7UnUtn5ZyJDcYUXHNYFmDL": "plano-estudo",
}

NOTAS_TECNICAS = {
    "PRnbZpL7gZBVva5s4nf5vi",
    "DRPv5QwAGut5wkNu9hRZYL",
    "bsMkqeRZFnmzAWZKWTgnAc",
    "cC3M9AYrY4DEFkBTzLJo9n",
}

TIPO2TRILHA = {
    "plano": "plano-estudo", "aula": "aulas-portugues", "nota": "exegese",
    "resumo": "exegese", "guia": "exegese", "indice": "plano-estudo",
    "mapa": "plano-estudo", "ficha": "exegese", "exegese": "exegese",
    "devocional": "devocional", "simulado": "simulados", "gabarito": "gabaritos",
    "exercicio": "estudo-ipb", "relatorio": "estudo-ipb", "transcricao": "exegese",
}


def classificar_trilha(memo):
    c = memo.get("content") or ""
    ls = [l.strip() for l in c.splitlines() if l.strip()]
    titulo = " ".join(ls[:3])[:600]
    tags = memo.get("tags") or []
    if isinstance(tags, str):
        tags = [t.strip() for t in tags.split(",") if t.strip()]
    tset = set(tags)

    for nome, rx in TRILHAS:
        if rx.search(titulo):
            return nome, "regex-titulo"
    if any(t.startswith("livro/") for t in tset):
        return "exegese", "tag livro/"
    for t in sorted(tset):
        if t.startswith("serie/"):
            if "portugues" in t or re.search(r"m[123]\.", t):
                return "aulas-portugues", "tag serie/"
            if "devocional" in t:
                return "devocional", "tag serie/"
    for t in sorted(tset):
        if t.startswith("tipo/"):
            return TIPO2TRILHA.get(t.split("/", 1)[1], "plano-estudo"), "tag tipo/"
    if any("ipb" in t or "seminario" in t or "ebd" in t for t in tset):
        return "estudo-ipb", "tag fonte/"
    return "plano-estudo", "fallback"


# ---------------------------------------------------------------------------
# EXTRACAO DO GABARITO (o conteudo rico vai pro data/ ANTES de ir pro Memos)
# ---------------------------------------------------------------------------
def extrair_gabarito(conteudo):
    """Extrai (resposta, justificativa, onde reler) de cada questao.

    Formato dos gabaritos do Memos:
        ## Q1
        **B) Mas**
        **Por que:** ...
        **Onde reler:** ...
    """
    texto = conteudo
    # corta o preambulo (titulo + aviso) ANTES do primeiro "## Q"
    m = re.search(r"^##\s*Q\d+\s*$", texto, re.M)
    if m:
        texto = texto[m.start():]
    texto = re.sub(r"^>.*$", "", texto, flags=re.M)

    blocos = re.split(r"^##\s*Q(\d+)\s*$", texto, flags=re.M)
    quests = []
    for i in range(1, len(blocos) - 1, 2):
        num = blocos[i]
        corpo = blocos[i + 1].strip()
        if not corpo:
            continue
        resposta = just = onde = ""
        for ln in corpo.split("\n"):
            s = re.sub(r"^[-*+]\s+", "", ln.strip()).replace("**", "").strip()
            if not s:
                continue
            if not resposta and re.match(r"^[A-Da-d][)\.]\s*\S", s):
                resposta = s
                continue
            if not just and re.match(r"^Por que|^Justificativa|^Explica", s, re.I):
                just = s
                continue
            if not onde and re.match(r"^Onde (reler|estudar|ver)", s, re.I):
                onde = s
                continue
            if resposta and not just and len(s) > 20:
                just = s
                continue
            if just and not onde and len(s) > 20:
                onde = s
                continue
        quests.append({
            "n": int(num),
            "resposta": resposta,
            "por_que": just,
            "onde_reler": onde,
        })
    return quests


def slug(titulo):
    s = re.sub(r"[^0-9A-Za-zÀ-ÿ\s\-]", " ", titulo.lower())
    s = re.sub(r"\s+", "-", s.strip())
    s = s.replace("--", "-")
    return s[:70].strip("-")


def salvar_gabaritos(memos):
    """Salva os gabaritos no data/. Devolve [(uid, caminho, n_quests)]."""
    GABDIR.mkdir(parents=True, exist_ok=True)
    salvos = []
    for m in memos:
        c = m.get("content") or ""
        titulo = (c.strip().splitlines() or ["(sem titulo)"])[0]
        if "gabarito" not in titulo.lower():
            continue
        uid = cur.uid(m)
        qs = extrair_gabarito(c)
        nome = slug(titulo.replace("#", "").replace("🔑", "").strip()) or uid
        caminho = GABDIR / f"{nome}.md"
        titulo_limpo = titulo.replace('"', "'")
        corpo = [
            "---",
            f'titulo: "{titulo_limpo}"',
            "tipo: gabarito",
            'materia: "IPB — Processo de Admissão"',
            f"memo_uid_origem: {uid}",
            f"total_questoes: {len(qs)}",
            "acesso: restrito-ao-iam",
            'obs: "NAO publicar no Memos. O gabarito fica com o IAM, que corrige a prova."',
            "---",
            "",
            f"# {titulo}",
            "",
            "> **Este é o gabarito — não vai para o Memos.**",
            "> Você faz a prova, o IAM corrige e informa o que errou e como acertar.",
            "",
        ]
        if qs:
            for q in qs:
                corpo.append(f"## Q{q['n']}")
                corpo.append("")
                corpo.append(f"**Resposta: {q['resposta'] or '(nao identificada)'}**")
                corpo.append("")
                if q["por_que"]:
                    corpo.append(q["por_que"])
                    corpo.append("")
                if q["onde_reler"]:
                    corpo.append(q["onde_reler"])
                    corpo.append("")
            corpo.append("---")
            corpo.append("")
            corpo.append("## Chave de referencia")
            corpo.append("")
            corpo.append("| Q | Resposta |")
            corpo.append("|---|---|")
            for q in qs:
                letra = (q["resposta"] or "")[:2].strip()
                corpo.append(f"| Q{q['n']} | {letra} |")
            corpo.append("")
        else:
            corpo.append("*(conteudo bruto preservado abaixo)*")
            corpo.append("")
            corpo.append("```")
            corpo.append(c.strip())
            corpo.append("```")
            corpo.append("")
        caminho.write_text("\n".join(corpo), encoding="utf-8")
        salvos.append((uid, caminho, len(qs)))
    return salvos


# ---------------------------------------------------------------------------
# LIMPEZA: so remove gabarito DE PROVA (preserva ✅ decorativo)
# ---------------------------------------------------------------------------
# MEDIDO 2026-11-05: o gabarito real esta TODO nos 11 memos que sao APAGADOS.
# Nos 127 restantes nao ha gabarito de prova — o que existe e':
#   - "✅ No acervo" / "❌ Faltam" (tabela de catalogo)
#   - "✅ Metadados de validacao" (cabecalho de secao)
#   - "1:1-4 ✅" (marcado num comentario biblico)
#   - "## Gabarito resumido - para conferir depois" (QUADRO de conclusoes
#     teologicas, nao gabarito de prova)
# Entao a limpeza destrutiva fica DESLIGADA. A auditoria apenas RELATA.
RX_DETAILS = re.compile(
    r"\n*<details>\s*<summary>\s*Gabarito\s*</summary>.*?</details>\s*", re.S | re.I)


def auditar_gabarito(conteudo):
    """Relata (nao altera) onde ha possivel gabarito de prova."""
    achados = []
    if "<details>" in conteudo and re.search(r"summary>\s*Gabarito", conteudo, re.I):
        achados.append("details-gabarito")
    if re.search(r"^#+\s*🔑\s*Gabarito", conteudo, re.M):
        achados.append("titulo-gabarito")
    # alternativa de prova marcada com ✅
    for i, ln in enumerate(conteudo.split("\n")):
        s = re.sub(r"^[-*+]\s+", "", ln.strip()).replace("**", "").strip()
        if re.match(r"^[A-Da-d][)\.]\s*\S", s) and ("✅" in ln or "✔" in ln):
            achados.append(f"alternativa-ok:L{i+1}")
            break
    return achados


def main():
    cur.carregar_env()
    acao = sys.argv[1] if len(sys.argv) > 1 else "--auditar"

    print("== 1. BACKUP ==")
    todos = cur.listar()
    meios = [m for m in todos if (m.get("creator") or "") == MEU]
    print(f"   total na API: {len(todos)} | do Study-Agent: {len(meios)}")
    BKPDIR.mkdir(parents=True, exist_ok=True)
    stamp = time.strftime("%Y%m%d-%H%M%S")
    bkp = BKPDIR / f"memos-{stamp}-pre-reorg.json"
    bkp.write_text(json.dumps(todos, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"   backup: {bkp.relative_to(ROOT)}")

    uids_gab = {cur.uid(g) for g in meios
                if "gabarito" in (g.get("content") or "").strip().splitlines()[0].lower()}
    gabs = [m for m in meios if cur.uid(m) in uids_gab]

    print()
    print("== 2. PLANO ==")
    plano_delete, plano_update = [], []
    for m in meios:
        uid = cur.uid(m)
        c = m.get("content") or ""
        tags = cur.tags_de(m)
        if uid in NOTAS_TECNICAS:
            plano_delete.append((uid, cur._titulo_limpo(m), "nota-tecnica"))
            continue
        if uid in uids_gab:
            plano_delete.append((uid, cur._titulo_limpo(m), "gabarito"))
            continue
        trilha, regra = classificar_trilha(m)
        if uid in CORRECOES:
            trilha = CORRECOES[uid]
        novas = ["study-agent", trilha]
        achados = auditar_gabarito(c)
        if sorted(set(novas)) != sorted(set(tags)):
            plano_update.append({
                "uid": uid, "titulo": cur._titulo_limpo(m),
                "tags_antigas": tags, "tags_novas": novas,
                "gabarito_suspeito": achados,
                "muda_tags": True,
                "muda_corpo": False,
            })

    print(f"   APAGAR do Memos: {len(plano_delete)}")
    for uid, t, why in plano_delete:
        print(f"      - {uid} [{why}] | {t[:56]}")
    print(f"   RE-TAG: {len(plano_update)}")
    com_susp = [p for p in plano_update if p["gabarito_suspeito"]]
    print(f"   memos com possivel gabarito (RELATADO, nao removido): {len(com_susp)}")
    for p in com_susp:
        print(f"      * {p['uid']} | {p['titulo'][:50]} | {p['gabarito_suspeito']}")

    if acao == "--auditar":
        out = ROOT / "data" / "estudos" / "notas" / "memos-curadoria" / "plano-reorg.json"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps({
            "delete": [{"uid": u, "titulo": t, "motivo": w} for u, t, w in plano_delete],
            "update": plano_update,
            "gabaritos_a_extrair": sorted(uids_gab),
        }, ensure_ascii=False, indent=1), encoding="utf-8")
        print()
        print("   PLANO gravado em:", out.relative_to(ROOT))
        print("   NADA foi alterado no Memos.")
        return

    if acao != "--aplicar":
        print("ERRO: use --auditar ou --aplicar")
        return

    print()
    print("== 3. EXTRAINDO GABARITOS PARA O data/ (conteudo rico nao se perde) ==")
    salvos = salvar_gabaritos(gabs)
    for uid, caminho, nq in salvos:
        print(f"   SALVO {uid} -> {caminho.relative_to(ROOT)} ({nq} quests)")

    print()
    print("== 4. APLICANDO (apagar + re-tag) ==")
    ok_del = 0
    for uid, t, why in plano_delete:
        d = cur.api("DELETE", f"/api/v1/memos/{uid}", timeout=45)
        if isinstance(d, dict) and d.get("name", "").endswith(uid):
            ok_del += 1
            print(f"   APAGADO {uid} [{why}] | {t[:50]}")
        else:
            print(f"   FALHOU  {uid} | {str(d)[:90]}")
        time.sleep(0.3)

    ok_up, falhas = 0, []
    for i, p in enumerate(plano_update, 1):
        memo = next((m for m in meios if cur.uid(m) == p["uid"]), None)
        if memo is None:
            continue
        novo = cur.reescrever(memo.get("content") or "", p["tags_novas"])
        d = cur.api("PATCH", f"/api/v1/memos/{p['uid']}", {"content": novo}, timeout=60)
        if isinstance(d, dict) and d.get("name", "").endswith(p["uid"]):
            ok_up += 1
        else:
            falhas.append((p["uid"], str(d)[:110]))
        if i % 25 == 0:
            print(f"   ... {i}/{len(plano_update)}")
        time.sleep(0.35)

    print(f"   re-tag OK: {ok_up}/{len(plano_update)} | apagados: {ok_del}/{len(plano_delete)}")
    for uid, err in falhas[:10]:
        print(f"      FALHA {uid} | {err}")

    print()
    print("== 5. AUDITORIA FINAL ==")
    todos2 = cur.listar()
    meus2 = [m for m in todos2 if (m.get("creator") or "") == MEU]
    tags_set = set()
    suspeitas = []
    for m in meus2:
        tags_set.update(cur.tags_de(m))
        c = m.get("content") or ""
        if "<details>" in c:
            suspeitas.append((cur.uid(m), cur._titulo_limpo(m), "tem <details>"))
        elif re.search(r"^#+\s*🔑\s*Gabarito", c, re.M):
            suspeitas.append((cur.uid(m), cur._titulo_limpo(m), "titulo de gabarito"))
    print(f"   memos do Study-Agent: {len(meus2)}")
    print(f"   tags distintas: {len(tags_set)}")
    for t in sorted(tags_set):
        print(f"      {t}")
    print(f"   gabaritos remanescentes: {len(suspeitas)}")
    for uid, t, why in suspeitas:
        print(f"      ! {uid} | {t[:56]} ({why})")


if __name__ == "__main__":
    main()
