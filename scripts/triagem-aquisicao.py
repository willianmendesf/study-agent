#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
triagem-aquisicao.py — decide, PARA CADA obra necessaria, qual das 3 vias usar.

O pedido do William (2026-11-07):
  "antes de recomendar comprar livro, se eu tiver ele fisico, valide antes de
   existe digital dele, se nao existir nem para comprar ou para baixar, me
   recomende, se eu tiver fisico, escanear ele o livro"

Traduzido em ORDEM DE PREFERENCIA:
  VIA 1 — ja existe digital no acervo  -> USAR. nao comprar, nao escanear.
  VIA 2 — nao existe digital, mas o William tem FISICO -> ESCANEAR. nao comprar.
  VIA 3 — nem digital nem fisico -> AI sim vale COMPRAR (ou baixar no z-library).

Saidas:
  data/perfil/bibliotecario/triagem-aquisicao.yaml   (estado estruturado)
  data/biblioteca/triagem-aquisicao.md               (relatorio legivel)

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
FISICO_JSON = Path("/tmp/librarium_fisico.json")
GAP = Path("/tmp/gap-canonicos.json")
CATALOGO_COMPRAS = DATA / "perfil/bibliotecario/catalogo-compras.yaml"
OUT_YAML = DATA / "perfil/bibliotecario/triagem-aquisicao.yaml"
OUT_MD = DATA / "biblioteca/triagem-aquisicao.md"

PARADA = {
    "de", "da", "do", "das", "dos", "a", "o", "e", "em", "para", "com", "the",
    "of", "and", "um", "uma", "os", "as", "ao", "na", "no", "se", "por",
}


def norm(s: str) -> str:
    s = unicodedata.normalize("NFD", s or "")
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    s = re.sub(r"[^a-z0-9 ]", " ", s.lower())
    return " ".join(w for w in s.split() if w and w not in PARADA)


def tokens(s: str):
    return set(norm(s).split())


# ---------------------------------------------------------------- acervo

def sobrenome(autor: str) -> str:
    """Ultimo token significativo do nome — e o que identifica o autor.

    'Jean Baptiste Moliere' -> 'moliere';  'Molière' -> 'moliere';
    'Fedor Dostoievsky' -> 'dostoievsky'.
    """
    ts = [w for w in (autor or "").split() if w]
    if not ts:
        return ""
    for w in reversed(ts):
        if norm(w):
            return norm(w)
    return ""


def mesmo_autor(a1: str, a2: str) -> float:
    """0.0 = autores diferentes; 1.0 = mesmo autor.

    Usa o SOBRENOME (ultimo token) com similaridade, porque:
      - 'Jean Baptiste Moliere' vs 'Molière'  -> sobrenome igual (0.82)
      - 'Fedor Dostoievsky' vs 'Fiodor Dostoievski' -> sobrenome parecido (0.82)
      - 'Os Doze' (Blok) vs 'Doze Passos' (Walton) -> sobrenomes diferentes (0.0)
      - 'O Capital' (Marx) vs 'A Capital' (Eça) -> sobrenomes diferentes (0.0)
    """
    s1, s2 = sobrenome(a1), sobrenome(a2)
    if not s1 or not s2:
        return 0.0
    if s1 == s2:
        return 1.0
    r = difflib.SequenceMatcher(None, s1, s2).ratio()
    return round(r, 3)


def _frontmatter(caminho: Path):
    """(titulo, autor) do frontmatter do .md do acervo.

    BUG FIX 2026-11-07: o regex antigo exigia DOIS ":" (porque a chave ja
    terminava com ":" e o padrao exigia mais um) — o autor nunca era lido e
    TODA a triagem via 1 caia em falso positivo.
    """
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
            v = m.group(1).strip().strip('"').strip("'")
            out[chave] = v
    return out.get("titulo") or out.get("title") or "", out.get("autor") or out.get("author") or ""


def indexar_acervo():
    """Titulo normalizado -> {caminho, autor} do acervo digital.

    O AUTOR vem do FRONTMATTER, nao do nome do arquivo. Bug real (2026-11-07):
    casando pelo nome do arquivo, "O Capital" (Marx) casava com "A Capital"
    (Eca) e "Contos" (Andersen) casava com "Contos" (Tchekhov) — e a triagem
    dizia "voce ja tem isso" para obras que voce nao tem.
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
               "titulo": tit_fm or p.stem}
        for b in bases:
            if b not in idx or (not idx[b]["autor"] and reg["autor"]):
                idx[b] = reg
    return idx


def casar_acervo(obra, autor, idx):
    """Retorna (caminho, score) do melhor casamento no acervo digital.

    REGRA (2026-11-07): quando a obra tem AUTOR, o autor e OBRIGATORIO no
    casamento, comparado por SOBRENOME com similaridade. So obras SEM autor
    (ex.: "Machado de Assis") usam casamento por titulo exato.
    """
    t_alvo = tokens(obra)
    if not t_alvo:
        return None, 0.0
    melhor = (None, 0.0)
    for chave, reg in idx.items():
        tk = set(chave.split())
        if not tk:
            continue
        cov = len(t_alvo & tk) / len(t_alvo)
        if cov < 0.6:
            continue
        if autor:
            cov_autor = mesmo_autor(autor, reg.get("autor") or "")
            if cov_autor < 0.75:
                continue
            score = round(min(1.0, 0.75 * cov + 0.25 * cov_autor), 3)
        else:
            if cov < 0.95:
                continue
            score = round(cov, 3)
        if score > melhor[1]:
            melhor = (reg["caminho"], score)
    return melhor



# ---------------------------------------------------------------- fisico
def indexar_fisico():
    """Titulo normalizado -> registro do exemplar fisico (Librarium)."""
    if not FISICO_JSON.exists():
        return {}, []
    books = json.loads(FISICO_JSON.read_text(encoding="utf-8"))
    idx = {}
    for b in books:
        titulo = b.get("title") or ""
        autores = ", ".join(c.get("name", "") for c in (b.get("contributors") or []))
        idx.setdefault(norm(titulo), {
            "titulo": titulo,
            "autor": autores,
            "id": b.get("id"),
            "biblioteca": b.get("_lib"),
            "generos": [g.get("name") for g in (b.get("genres") or [])],
            "isbn": b.get("isbn") or b.get("isbn_13"),
            "media_type": b.get("media_type"),
        })
    return idx, books


def casar_fisico(obra, autor, idx):
    """Mesmo principio do acervo: autor obrigatorio quando existe.

    Sem isso, "Os Doze" (Blok) casou com "Doze Passos da Exegese"
    (Walton) — e a triagem mandava escanear um livro de teologia.
    """
    t_alvo = tokens(obra)
    a_alvo = tokens(autor)
    if not t_alvo:
        return None, 0.0
    melhor = (None, 0.0)
    for chave, reg in idx.items():
        tk = set(chave.split())
        if not tk:
            continue
        cov = len(t_alvo & tk) / len(t_alvo)
        if cov < 0.6:
            continue
        if autor:
            cov_autor = mesmo_autor(autor, reg.get("autor") or "")
            if cov_autor < 0.75:
                continue
            score = round(min(1.0, 0.75 * cov + 0.25 * cov_autor), 3)
        else:
            if cov < 0.95:
                continue
            score = round(cov, 3)
        if score > melhor[1]:
            melhor = (reg, score)
    return melhor


def main():
    if not GAP.exists():
        raise SystemExit(f"gap ausente: {GAP} ( rode scripts/gap-canonicos.py )")
    gap = json.loads(GAP.read_text(encoding="utf-8"))
    idx_dig = indexar_acervo()
    idx_fis, fisicos = indexar_fisico()

    import yaml
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
        f_reg, f_score = casar_fisico(obra, autor, idx_fis)
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
            entrada.update({
                "via": "via_2_escanear",
                "acao": "escanear_o_exemplar_fisico",
                "exemplar_fisico": {
                    "titulo": f_reg["titulo"],
                    "autor": f_reg["autor"],
                    "id": f_reg["id"],
                    "biblioteca": f_reg["biblioteca"],
                    "isbn": f_reg["isbn"],
                },
                "score": f_score,
                "nota": "NAO comprar: o exemplar ja esta em casa. Escanear.",
                "como": (f"python3 scripts/digitalizar-fisico.py --preparar "
                         f"{re.sub(r'[^a-z0-9]+','-', norm(obra)).strip('-')}  "
                         f"&& python3 scripts/digitalizar-fisico.py --slug "
                         f"{re.sub(r'[^a-z0-9]+','-', norm(obra)).strip('-')} "
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

    # ordem dentro de cada via: prioridade (n_listas, prioridade)
    for v in vias.values():
        v.sort(key=lambda e: (-(e.get("n_listas") or 0), -(e.get("prioridade") or 0)))

    doc = {
        "tipo": "triagem-aquisicao",
        "descricao": (
            "Decide a via de aquisicao de cada obra necessaria: "
            "VIA 1 digital (usar), VIA 2 escanear o fisico que o William ja tem, "
            "VIA 3 comprar/baixar (so quando nao ha digital nem fisico). "
            "A ordem importa: nunca recomendar comprar o que ele ja tem em casa."
        ),
        "data": "2026-11-07",
        "gerado_por": "scripts/triagem-aquisicao.py",
        "regra_ordem": [
            "1. se existe digital no acervo -> USAR (nao comprar)",
            "2. se nao existe digital MAS existe fisico -> ESCANEAR (nao comprar)",
            "3. se nao tem digital nem fisico -> AI SIM vale comprar ou baixar",
        ],
        "regra_escrita_externa": (
            "Comprar e escanear sao acoes do William (ou com aprovacao explicita). "
            "O agente cataloga, prioriza e prepara; nao compra e nao envia nada a "
            "sistema externo sem aprovacao."
        ),
        "totais": {k: len(v) for k, v in vias.items()},
        "exemplares_fisicos_conhecidos": len(fisicos),
        "vias": vias,
    }
    OUT_YAML.parent.mkdir(parents=True, exist_ok=True)
    OUT_YAML.write_text(
        "# triagem-aquisicao.yaml — GERADO por scripts/triagem-aquisicao.py — nao editar a mao\n"
        + yaml.safe_dump(doc, allow_unicode=True, sort_keys=False, width=4096),
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
    L.append(f"Exemplares físicos conhecidos: **{len(fisicos)}** (Librarium, leitura)")
    L.append("")
    L.append("## Panorama")
    L.append("")
    L.append("| via | ação | nº |")
    L.append("|---|---|---|")
    L.append(f"| 1 | usar o digital que já existe | {len(vias['via_1_digital'])} |")
    L.append(f"| 2 | **escanear o físico que você tem** | {len(vias['via_2_escanear'])} |")
    L.append(f"| 3 | comprar ou baixar | {len(vias['via_3_comprar'])} |")
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
            L.append("| obra | autor | seu exemplar | onde |")
            L.append("|---|---|---|---|")
            for e in itens:
                ef = e["exemplar_fisico"]
                L.append(f"| {e['titulo']} | {e.get('autor') or '—'} | {ef['titulo']} | "
                         f"{ef['biblioteca']} |")
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
                loja = e["lojas"][0] if e.get("lojas") else None
                link = f"[{loja['loja_nome']}]({loja['url']})" if loja else "—"
                L.append(f"| {e['titulo']} | {e.get('autor') or '—'} | {e.get('n_listas')} | "
                         f"`{e.get('status')}` | {link} |")
            L.append("")
    L.append("---")
    L.append("")
    L.append("**Regra de escrita externa:** comprar e enviar para sistema externo são")
    L.append("ações suas, com aprovação explícita, turno a turno. Eu catalogo, priorizo e")
    L.append("preparo — não executo a compra.")
    L.append("")

    OUT_MD.write_text("\n".join(L) + "\n", encoding="utf-8")
    print(f"[triagem] {OUT_YAML}")
    print(f"[triagem] {OUT_MD}")
    print(f"[triagem] via1={len(vias['via_1_digital'])} via2={len(vias['via_2_escanear'])} "
          f"via3={len(vias['via_3_comprar'])}")


if __name__ == "__main__":
    sys.exit(main())
