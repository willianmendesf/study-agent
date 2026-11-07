#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
triagem-aquisicao-v2.py — VIA DE AQUISICAO de cada obra necessaria (v2).

Pedido literal do William (2026-11-07):
  "antes de recomendar comprar livro, se eu tiver ele fisico, valide antes de
   existe digital dele, se nao existir nem para comprar ou para baixar, me
   recomende, se eu tiver fisico, escanear ele o livro, assim voce consegue
   raspar o livro e ter ele catalogado."

Traduzido em ORDEM DE PREFERENCIA (a ordem e o que importa):
  VIA 1 — ja existe digital no acervo  -> USAR. nao comprar, nao escanear.
  VIA 2 — nao existe digital, mas o William tem FISICO -> ESCANEAR. nao comprar.
  VIA 3 — nem digital nem fisico -> AI SIM vale COMPRAR (ou baixar no z-library).

O que muda da v1 (por que a v1 nao bastava):
  1. INVENTARIO FISICO PERSISTIDO no repo
     (data/perfil/bibliotecario/estante-fisica.yaml). A v1 lia
     /tmp/librarium_fisico.json — arquivo TEMPORARIO: some no reboot e a
     triagem inteira caia para "comprar" sem conferir o fisico.
  2. O inventario junta 3 fontes: (a) snapshot do Librarium (118 exemplares),
     (b) a lista de 58 titulos que o William enviou, (c) declaracoes avulsas
     (data/perfil/bibliotecario/fisicos-declarados.yaml).
  3. MATCHER melhorado:
       - containment: a obra inteira pode estar dentro de um volume composto
         ("Fausto / Werther" contem "Fausto");
       - genericos removidos ("aventuras", "viagens", "contos", "obras"...) e
         plural normalizado ("livro"/"livros") — assim "Aventuras de Gulliver"
         casa com "Viagens de Gulliver";
       - autor por SOBRENOME (obrigatorio quando a obra tem autor).
  4. catalogo-compras.yaml recebe status novo ("nao_comprar") para o que ja
     existe em digital ou em fisico — nunca recomendar comprar o que ele tem.

Saidas:
  data/perfil/bibliotecario/estante-fisica.yaml   (inventario persistido)
  data/perfil/bibliotecario/triagem-aquisicao.yaml (estado estruturado)
  data/biblioteca/triagem-aquisicao.md             (relatorio legivel)

NAO compra. NAO escaneia sozinho. NAO escreve em sistema externo.
"""
import difflib
import json
import re
import sys
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
BIB = DATA / "biblioteca"
PERFIL = DATA / "perfil/bibliotecario"

LIBRARIUM_JSON = PERFIL / "librarium-fisico.json"
GAP = PERFIL / "gap-canonicos.json"
# fallback: snapshots antigos em /tmp (o repo e a fonte duravel)
ESTANTE_WILLIAM = PERFIL / "estante-william.yaml"
DECLARADOS = PERFIL / "fisicos-declarados.yaml"
INVENTARIO = PERFIL / "estante-fisica.yaml"
CATALOGO_COMPRAS = PERFIL / "catalogo-compras.yaml"
OUT_YAML = PERFIL / "triagem-aquisicao.yaml"
OUT_MD = BIB / "triagem-aquisicao.md"

PARADA = {
    "de", "da", "do", "das", "dos", "a", "o", "e", "em", "para", "com", "the",
    "of", "and", "um", "uma", "os", "as", "ao", "na", "no", "se", "por",
}

# Tokens genericos que nao identificam a obra (titulo de volume/traducao).
GENERICOS = {
    "aventura", "aventuras", "viagem", "viagens", "historia", "historias",
    "obra", "obras", "dialogo", "dialogos", "conversa", "conversas",
    "novela", "novelas", "carta", "cartas", "poema", "poemas", "conto",
    "contos", "memoria", "memorias", "cronica", "cronicas", "romance",
    "romances", "drama", "dramas", "coleta", "coletanea", "volume", "parte",
    "completo", "completa", "obra", "traducao", "edicao", "classico",
    "classicos", "antologia", "selecao", "melhor", "obra",
}


def _hoje():
    import datetime
    return datetime.date.today().isoformat()


def norm(s):
    s = unicodedata.normalize("NFD", s or "")
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    s = re.sub(r"[^a-z0-9 ]", " ", s.lower())
    return " ".join(w for w in s.split() if w and w not in PARADA)


def _stem(t):
    """Plural simples: 'livros' -> 'livro' (>=4 letras, termina em s)."""
    if len(t) > 4 and t.endswith("s") and not t.endswith("ss"):
        return t[:-1]
    return t


def core_tokens(titulo):
    """Tokens que IDENTIFICAM a obra (sem genericos, sem numero de parte).

    'Fausto (Primeiro)' -> {'fausto'}
    'Aventuras de Gulliver' -> {'gulliver'}
    'Viagens de Gulliver' -> {'gulliver'}
    """
    t = re.sub(r"\(([^)]*)\)", " ", titulo or "")
    t = re.sub(r"\b(parte|vol|volume|part|book|parte)\s*[\dIVXLC]+\b", " ", t, flags=re.I)
    t = re.sub(r"[\d]+", " ", t)
    toks = [_stem(w) for w in norm(t).split()]
    d = [w for w in toks if w not in GENERICOS and len(w) > 2]
    if not d:
        d = [w for w in toks if len(w) > 2]
    return set(d)


def sobrenome(autor):
    ts = [w for w in (autor or "").split() if w]
    for w in reversed(ts):
        if norm(w):
            return norm(w)
    return ""


def mesmo_autor(a1, a2):
    """0.0 = autores diferentes; 1.0 = mesmo autor (por sobrenome)."""
    s1, s2 = sobrenome(a1), sobrenome(a2)
    if not s1 or not s2:
        return 0.0
    if s1 == s2:
        return 1.0
    return round(difflib.SequenceMatcher(None, s1, s2).ratio(), 3)


# ---------------------------------------------------------------- acervo digital

def _frontmatter(caminho: Path):
    try:
        txt = caminho.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return "", ""
    if not txt.startswith("---"):
        return "", ""
    fim = txt.find("\n---", 3)
    if fim < 0:
        return "", ""
    fm = txt[3:fim]
    out = {}
    for chave in ("titulo", "title", "autor", "author"):
        m = re.search(r"^" + chave + r"\s*:\s*(.+?)\s*$", fm, re.M | re.I)
        if m:
            out[chave] = m.group(1).strip().strip('"').strip("'")
    return (out.get("titulo") or out.get("title") or "",
            out.get("autor") or out.get("author") or "")


def indexar_acervo():
    """titulo normalizado -> {caminho, autor} do acervo digital.

    O AUTOR vem do FRONTMATTER, nao do nome do arquivo (bug real de 2026-11-07:
    casando pelo nome do arquivo, 'O Capital' (Marx) casava com 'A Capital'
    (Eca) e 'Contos' (Andersen) com 'Contos' (Tchekhov)).
    """
    idx = {}
    for p in BIB.rglob("*.md"):
        if "/_incoming/" in str(p):
            continue
        tit_fm, aut_fm = _frontmatter(p)
        bases = set()
        if tit_fm:
            bases.add(norm(tit_fm))
        bases.add(norm(p.stem.replace("-", " ")))
        bases = {b for b in bases if b}
        reg = {"caminho": str(p.relative_to(DATA)), "autor": aut_fm,
               "titulo": tit_fm or p.stem, "core": core_tokens(tit_fm or p.stem)}
        for b in bases:
            if b not in idx or (not idx[b]["autor"] and reg["autor"]):
                idx[b] = reg
    return idx


def casar_acervo(obra, autor, idx):
    """(caminho, score) do melhor casamento no acervo digital.

    Autor e OBRIGATORIO quando a obra tem autor; obra sem autor exige
    casamento exato do titulo.
    """
    c_alvo = core_tokens(obra)
    if not c_alvo:
        return None, 0.0
    melhor = (None, 0.0)
    for chave, reg in idx.items():
        c_reg = reg.get("core") or set(chave.split())
        if not c_reg:
            continue
        cov = len(c_alvo & c_reg) / len(c_alvo)
        if cov < 1.0:
            continue
        if autor:
            ca = mesmo_autor(autor, reg.get("autor") or "")
            if ca < 0.75:
                continue
            score = round(min(1.0, 0.75 * cov + 0.25 * ca), 3)
        else:
            score = round(cov, 3)
        if score > melhor[1]:
            melhor = (reg["caminho"], score)
    return melhor


# ---------------------------------------------------------------- inventario fisico

def _livros_librarium():
    for p in (LIBRARIUM_JSON, Path("/tmp/librarium_fisico.json")):
        if p.exists():
            try:
                return json.loads(p.read_text(encoding="utf-8"))
            except Exception:
                continue
    return []


def montar_inventario():
    """Junta as 3 fontes de exemplares fisicos e PERSISTE no repo."""
    exemplares = []
    vistos = set()

    for b in _livros_librarium():
        titulo = b.get("title") or ""
        autores = ", ".join(c.get("name", "") for c in (b.get("contributors") or []))
        chave = (norm(titulo).lower(), norm(autores).lower())
        if chave in vistos:
            continue
        vistos.add(chave)
        exemplares.append({
            "id": f"librarium:{b.get('id')}",
            "titulo": titulo,
            "autor": autores,
            "biblioteca": b.get("_lib"),
            "descricao": b.get("description") or "",
            "isbn": b.get("isbn") or "",
            "fonte": "librarium",
        })

    if ESTANTE_WILLIAM.exists():
        import yaml
        d = yaml.safe_load(ESTANTE_WILLIAM.read_text(encoding="utf-8")) or {}
        for l in (d.get("livros") or []):
            titulo = l.get("titulo") or ""
            autores = l.get("autor") or ""
            chave = (norm(titulo).lower(), norm(autores).lower())
            if chave in vistos:
                continue
            vistos.add(chave)
            exemplares.append({
                "id": f"lista-william:{l.get('id')}",
                "titulo": titulo,
                "autor": autores,
                "biblioteca": "casa (lista enviada pelo William)",
                "descricao": l.get("detalhes") or "",
                "isbn": "",
                "fonte": "lista-william",
            })

    if DECLARADOS.exists():
        import yaml
        d = yaml.safe_load(DECLARADOS.read_text(encoding="utf-8")) or {}
        for l in (d.get("exemplares") or []):
            titulo = l.get("titulo") or ""
            autores = l.get("autor") or ""
            chave = (norm(titulo).lower(), norm(autores).lower())
            if chave in vistos:
                continue
            vistos.add(chave)
            exemplares.append({
                "id": f"declarado:{l.get('titulo')}",
                "titulo": titulo,
                "autor": autores,
                "biblioteca": l.get("onde") or "casa",
                "descricao": l.get("obs") or "",
                "isbn": l.get("isbn") or "",
                "fonte": "declarado",
            })

    doc = {
        "tipo": "estante-fisica",
        "descricao": ("Inventario persistente dos exemplares FISICOS do William. "
                      "E a fonte da VIA 2 (escanear) da triagem de aquisicao. "
                      "Gerado por scripts/triagem-aquisicao-v2.py a partir de: "
                      "snapshot do Librarium, lista de 58 titulos enviada pelo "
                      "William e declaracoes avulsas."),
        "data": _hoje(),
        "gerado_por": "scripts/triagem-aquisicao-v2.py",
        "total": len(exemplares),
        "fontes": {
            "librarium": len(_livros_librarium()),
            "lista-william": sum(1 for e in exemplares if e["fonte"] == "lista-william"),
            "declarados": sum(1 for e in exemplares if e["fonte"] == "declarado"),
        },
        "exemplares": exemplares,
    }
    import yaml
    INVENTARIO.parent.mkdir(parents=True, exist_ok=True)
    INVENTARIO.write_text(
        "# estante-fisica.yaml — GERADO por scripts/triagem-aquisicao-v2.py\n"
        + yaml.safe_dump(doc, allow_unicode=True, sort_keys=False, width=4096),
        encoding="utf-8")
    return exemplares


def indexar_fisico(exemplares):
    idx = []
    for e in exemplares:
        idx.append({
            "titulo": e["titulo"],
            "autor": e["autor"],
            "id": e["id"],
            "biblioteca": e["biblioteca"],
            "descricao": e.get("descricao") or "",
            "fonte": e.get("fonte"),
            "core": core_tokens(e["titulo"]),
            "tokens": set(norm((e["titulo"] or "") + " " + (e.get("descricao") or "")).split()),
        })
    return idx


def casar_fisico(obra, autor, idx):
    """Containment: a obra inteira esta dentro do exemplar (volume composto).

    Devolve (registro, score, confianca) ou (None, 0.0, None).
    confianca: 'exata' | 'contida' (obra esta dentro de volume composto)
    """
    c_alvo = core_tokens(obra)
    if not c_alvo:
        return None, 0.0, None
    melhor = (None, 0.0, None)
    for f in idx:
        c_reg = f["core"]
        if not c_reg:
            continue
        cov = len(c_alvo & c_reg) / len(c_alvo)
        if cov < 1.0:
            continue
        ca = mesmo_autor(autor, f["autor"]) if autor else None
        if autor and f["autor"]:
            if ca < 0.75:
                continue
            score = round(0.75 * cov + 0.25 * ca, 3)
            conf = "exata"
        elif autor and not f["autor"]:
            # Exemplar SEM autor e obra COM autor: so aceita se o titulo for
            # essentially o mesmo (senao "Catecismo" (Trento) casaria com
            # "Meu Catecismo de Doutrina Cristana" — obra diferente).
            if c_alvo != c_reg:
                continue
            score = round(0.6 * cov, 3)
            conf = "contida"
        else:
            score = round(cov, 3)
            conf = "exata"
        if score > melhor[1]:
            melhor = (f, score, conf)
    return melhor


# ---------------------------------------------------------------- main

def slug_de(titulo):
    return re.sub(r"[^a-z0-9]+", "-", norm(titulo)).strip("-")


def main():
    import yaml
    gap = None
    for p in (GAP, Path("/tmp/gap-canonicos.json")):
        if p.exists():
            gap = json.loads(p.read_text(encoding="utf-8"))
            break
    if gap is None:
        raise SystemExit("gap ausente (rode scripts/gap-canonicos.py)")

    idx_dig = indexar_acervo()
    exemplares = montar_inventario()
    idx_fis = indexar_fisico(exemplares)

    cat = {}
    if CATALOGO_COMPRAS.exists():
        c = yaml.safe_load(CATALOGO_COMPRAS.read_text(encoding="utf-8")) or {}
        for o in c.get("obras", []) or []:
            cat[(o.get("titulo"), o.get("autor"))] = o

    vias = {"via_1_digital": [], "via_2_escanear": [], "via_3_comprar": []}
    for item in gap:
        obra = item.get("titulo")
        autor = item.get("autor")
        d_caminho, d_score = casar_acervo(obra, autor, idx_dig)
        f_reg, f_score, f_conf = casar_fisico(obra, autor, idx_fis)
        entrada = {
            "titulo": obra,
            "autor": autor or None,
            "genero": item.get("genero"),
            "n_listas": item.get("n_listas"),
            "prioridade": item.get("prioridade"),
        }
        if d_caminho:
            entrada.update({
                "via": "via_1_digital",
                "acao": "usar_o_que_ja_existe",
                "acervo": d_caminho,
                "score": d_score,
                "nota": "nao comprar, nao escanear",
            })
            vias["via_1_digital"].append(entrada)
        elif f_reg:
            slug = slug_de(obra)
            entrada.update({
                "via": "via_2_escanear",
                "acao": "escanear_o_exemplar_fisico",
                "exemplar_fisico": {
                    "titulo": f_reg["titulo"],
                    "autor": f_reg["autor"],
                    "id": f_reg["id"],
                    "biblioteca": f_reg["biblioteca"],
                    "fonte": f_reg["fonte"],
                },
                "score": f_score,
                "confianca": f_conf,
                "nota": ("NAO comprar: o exemplar ja esta em casa. Escanear."
                         + ("" if f_conf == "exata" else
                            " (obra esta dentro de um volume composto — confirmar a parte).")),
                "como": (f"python3 scripts/digitalizar-fisico.py --preparar {slug} "
                         f"&& python3 scripts/digitalizar-fisico.py --slug {slug} "
                         f"--titulo \"{obra}\" --autor \"{f_reg['autor']}\""),
            })
            vias["via_2_escanear"].append(entrada)
        else:
            c = cat.get((obra, autor)) or {}
            entrada.update({
                "via": "via_3_comprar",
                "acao": "avaliar_compra_ou_download",
                "status": c.get("status", "sem_link"),
                "lojas": c.get("lojas", []),
                "nota": "nem digital nem fisico — aqui compra/baixar se resolve",
            })
            vias["via_3_comprar"].append(entrada)

    for v in vias.values():
        v.sort(key=lambda e: (-(e.get("n_listas") or 0), -(e.get("prioridade") or 0)))

    # ---- VIA 2B: fisicos declarados que NAO estao em nenhuma lista-canon
    # (ex.: o livro do Carpeaux). Nao entram no gap, mas o William pediu para
    # escanear o que ele tem em casa -> entao viram fila de digitalizacao.
    via_2b = []
    ja_vistos = set()
    for e in vias["via_1_digital"] + vias["via_2_escanear"]:
        ja_vistos.add(norm(e["titulo"]).lower())
    for ex in exemplares:
        nt = norm(ex["titulo"]).lower()
        if not nt or nt in ja_vistos:
            continue
        d_caminho, d_score = casar_acervo(ex["titulo"], ex["autor"], idx_dig)
        if d_caminho:
            continue
        slug = slug_de(ex["titulo"])
        via_2b.append({
            "titulo": ex["titulo"],
            "autor": ex["autor"] or None,
            "origem": ex["fonte"],
            "onde": ex["biblioteca"],
            "via": "via_2b_escanear_fora_do_canon",
            "acao": "escanear_o_exemplar_fisico",
            "slug": slug,
            "nota": ("nao esta em digital no acervo e nao consta de nenhuma lista-canon "
                     "— escanear para catalogar"),
            "como": (f"python3 scripts/digitalizar-fisico.py --preparar {slug} "
                     f"&& python3 scripts/digitalizar-fisico.py --slug {slug} "
                     f"--titulo \"{ex['titulo']}\" --autor \"{ex['autor']}\""),
        })

    doc = {
        "tipo": "triagem-aquisicao",
        "descricao": (
            "Decide a via de aquisicao de cada obra necessaria: "
            "VIA 1 digital (usar), VIA 2 escanear o fisico que o William ja tem, "
            "VIA 3 comprar/baixar (so quando nao ha digital nem fisico). "
            "A ordem importa: nunca recomendar comprar o que ele ja tem em casa."),
        "data": _hoje(),
        "gerado_por": "scripts/triagem-aquisicao-v2.py",
        "regra_ordem": [
            "1. se existe digital no acervo -> USAR (nao comprar)",
            "2. se nao existe digital MAS existe fisico -> ESCANEAR (nao comprar)",
            "3. se nao tem digital nem fisico -> AI SIM vale comprar ou baixar",
        ],
        "regra_escrita_externa": (
            "Comprar e escanear sao acoes do William (ou com aprovacao explicita). "
            "O agente cataloga, prioriza e prepara; nao compra e nao envia nada a "
            "sistema externo sem aprovacao."),
        "totais": {k: len(v) for k, v in vias.items()},
        "via_2b_escanear_fora_do_canon": len(via_2b),
        "exemplares_fisicos_conhecidos": len(exemplares),
        "fontes_inventario": {
            "librarium": sum(1 for e in exemplares if e["fonte"] == "librarium"),
            "lista-william": sum(1 for e in exemplares if e["fonte"] == "lista-william"),
            "declarados": sum(1 for e in exemplares if e["fonte"] == "declarado"),
        },
        "vias": vias,
        "via_2b_escanear_fora_do_canon": via_2b,
    }
    OUT_YAML.write_text(
        "# triagem-aquisicao.yaml — GERADO por scripts/triagem-aquisicao-v2.py\n"
        + yaml.safe_dump(doc, allow_unicode=True, sort_keys=False, width=4096),
        encoding="utf-8")

    # ---- catalogo de compras: marcar o que NAO deve ser comprado
    cat_alterado = 0
    if CATALOGO_COMPRAS.exists():
        doc_cat = yaml.safe_load(CATALOGO_COMPRAS.read_text(encoding="utf-8")) or {}
        mudancas = {}
        for via, acao in (("via_1_digital", "usar_o_que_ja_existe"),
                          ("via_2_escanear", "escanear_o_exemplar_fisico")):
            for e in vias[via]:
                mudancas[(e["titulo"], e.get("autor"))] = (via, acao)
        # 1) limpa marcacoes anteriores (podem estar obsoletas: a triagem
        #    anterior classify "Catecismo" como escanear por um falso positivo)
        for o in doc_cat.get("obras", []) or []:
            if o.get("status") == "nao_comprar":
                o.pop("via", None)
                o.pop("acao", None)
                o["status"] = "a_comprar" if o.get("lojas") else "sem_link"
        # 2) reaplica a triagem de hoje
        for o in doc_cat.get("obras", []) or []:
            chave = (o.get("titulo"), o.get("autor"))
            if chave in mudancas and o.get("status") in ("a_comprar", "sem_link"):
                via, acao = mudancas[chave]
                o["status"] = "nao_comprar"
                o["via"] = via
                o["acao"] = acao
                cat_alterado += 1
        # 3) header coerente (o gerador original continua sendo o dono do arquivo)
        com_link = sum(1 for o in doc_cat.get("obras", []) or [] if o.get("lojas"))
        doc_cat["total"] = len(doc_cat.get("obras", []) or [])
        doc_cat["com_link"] = com_link
        doc_cat["sem_link"] = doc_cat["total"] - com_link
        doc_cat["triagem"] = {
            "data": _hoje(),
            "gerado_por": "scripts/triagem-aquisicao-v2.py",
            "marcado_nao_comprar": cat_alterado,
            "regra": ("status nao_comprar = ja existe em digital no acervo OU o William "
                      "tem o exemplar fisico (nesse caso o caminho e escanear)"),
        }
        CATALOGO_COMPRAS.write_text(
            "# catalogo-compras.yaml — GERADO por scripts/catalogo-compras.py — nao editar a mao\n"
            + yaml.safe_dump(doc_cat, allow_unicode=True, sort_keys=False, width=4096),
            encoding="utf-8")

    # ---- relatorio markdown
    L = []
    L.append("# Triagem de aquisição — a via certa para cada obra")
    L.append("")
    L.append("> **A regra que organiza isto:** antes de recomendar comprar qualquer")
    L.append("> coisa, a gente pergunta nesta ordem:")
    L.append(">")
    L.append("> 1. **Já existe digital no acervo?** → usa. Não compra.")
    L.append("> 2. **Não existe digital, mas você tem em casa?** → **escaneia.** Não compra.")
    L.append("> 3. **Nem digital nem físico?** → aí sim vale comprar ou baixar.")
    L.append("")
    L.append(f"Exemplares físicos conhecidos: **{len(exemplares)}** "
             f"(Librarium {doc['fontes_inventario']['librarium']} · "
             f"lista de casa {doc['fontes_inventario']['lista-william']} · "
             f"declarados {doc['fontes_inventario']['declarados']})")
    L.append("")
    L.append("## Panorama")
    L.append("")
    L.append("| via | ação | nº |")
    L.append("|---|---|---|")
    L.append(f"| 1 | usar o digital que já existe | {len(vias['via_1_digital'])} |")
    L.append(f"| 2 | **escanear o físico que você tem** | {len(vias['via_2_escanear'])} |")
    L.append(f"| 3 | comprar ou baixar | {len(vias['via_3_comprar'])} |")
    L.append("")

    if via_2b:
        L.append("## 2b. Escaneáveis que estão fora de qualquer lista-cânone")
        L.append("")
        L.append("Estes exemplares você tem em casa, **não existem em digital no acervo** "
                 "e **não constam em nenhuma lista de leitura** — mas são material seu "
                 "que vale catalogar. O primeiro da fila é o do Carpeaux.")
        L.append("")
        L.append("| obra | autor | origem | onde |")
        L.append("|---|---|---|---|")
        for e in via_2b:
            L.append(f"| {e['titulo']} | {e.get('autor') or '—'} | {e['origem']} | {e['onde']} |")
        L.append("")
        L.append("```bash")
        L.append("# 1) prepara a pasta de envio")
        L.append("python3 scripts/digitalizar-fisico.py --preparar <slug>")
        L.append("# 2) você manda as fotos (ou um PDF) para data/biblioteca/_incoming/<slug>/")
        L.append("# 3) eu rodo o OCR e catalogo")
        L.append("python3 scripts/digitalizar-fisico.py --slug <slug> --titulo \"...\" --autor \"...\"")
        L.append("```")
        L.append("")

    for chave, titulo_secao, sub in [
        ("via_2_escanear", "2. Escanear o que você já tem em casa",
         "Estas obras **não existem em digital no acervo**, mas você **já tem o livro físico**. "
         "Não há por que comprar: o caminho é escanear."),
        ("via_1_digital", "1. Já existe em digital — usar",
         "O acervo já tem. Não há por que comprar nem escanear."),
        ("via_3_comprar", "3. Nem digital nem físico — aí sim comprar",
         "Só estas entram na fila de compra."),
    ]:
        L.append(f"## {titulo_secao}")
        L.append("")
        L.append(sub)
        L.append("")
        itens = vias[chave]
        if not itens:
            L.append("_nenhum item_")
            L.append("")
            continue
        if chave == "via_2_escanear":
            L.append("| obra | autor | seu exemplar | onde | confiança |")
            L.append("|---|---|---|---|---|")
            for e in itens:
                ef = e["exemplar_fisico"]
                L.append(f"| {e['titulo']} | {e.get('autor') or '—'} | {ef['titulo']} | "
                         f"{ef['biblioteca']} | {e.get('confianca')} |")
            L.append("")
            L.append("### Como escanear uma")
            L.append("")
            L.append("```bash")
            L.append("# 1) prepara a pasta de envio")
            L.append("python3 scripts/digitalizar-fisico.py --preparar <slug>")
            L.append("# 2) você manda as fotos (ou um PDF) para data/biblioteca/_incoming/<slug>/")
            L.append("# 3) eu rodo o OCR e catalogo")
            L.append("python3 scripts/digitalizar-fisico.py --slug <slug> --titulo \"...\" --autor \"...\"")
            L.append("```")
            L.append("")
            L.append("**O que o scan precisa:** 200 dpi no mínimo (300 ideal), luz uniforme, "
                     "página reta, sem flash. O pipeline faz OCR em português, gera o `.md` "
                     "do acervo, normaliza e cataloga na KB.")
            L.append("")
        elif chave == "via_1_digital":
            L.append("| obra | autor | onde está |")
            L.append("|---|---|---|")
            for e in itens:
                L.append(f"| {e['titulo']} | {e.get('autor') or '—'} | `{e['acervo']}` |")
            L.append("")
        else:
            L.append("| obra | autor | listas | status | link |")
            L.append("|---|---|---|---|---|")
            for e in itens:
                lojas = e.get("lojas") or []
                link = "—"
                if lojas:
                    l0 = lojas[0]
                    link = f"[{l0.get('loja_nome') or l0.get('loja')}]({l0.get('url')})"
                L.append(f"| {e['titulo']} | {e.get('autor') or '—'} | {e.get('n_listas')} | "
                         f"`{e.get('status')}` | {link} |")
            L.append("")
    OUT_MD.write_text("\n".join(L) + "\n", encoding="utf-8")

    print(f"[triagem v2] via1={len(vias['via_1_digital'])} "
          f"via2={len(vias['via_2_escanear'])} via3={len(vias['via_3_comprar'])}")
    print(f"[triagem v2] exemplares fisicos: {len(exemplares)} -> {INVENTARIO.relative_to(ROOT)}")
    print(f"[triagem v2] catalogo de compras: {cat_alterado} obra(s) marcada(s) nao_comprar")
    print(f"[triagem v2] relatorio -> {OUT_MD.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
