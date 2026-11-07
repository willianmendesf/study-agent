#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
catalogo-compras-md.py — renderiza o catalogo de compras em Markdown legivel.

Entrada: data/perfil/bibliotecario/catalogo-compras.yaml (gerado por
         scripts/catalogo-compras.py)
Saida:  data/biblioteca/catalogo-compras.md

O catalogo NAO compra. Ele cataloga o link e o status. Status validos:
  a_comprar | em_compra | comprado | recebido | sem_link | descartado
"""
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
YAML_IN = ROOT / "data/perfil/bibliotecario/catalogo-compras.yaml"
MD_OUT = ROOT / "data/biblioteca/catalogo-compras.md"

ORDEM_STATUS = ["a_comprar", "em_compra", "comprado", "recebido", "sem_link", "descartado"]
ICO = {
    "a_comprar": "🟡",
    "em_compra": "🟠",
    "comprado": "🔵",
    "recebido": "🟢",
    "sem_link": "⚪",
    "descartado": "⚫",
}


def esc(t):
    return (t or "").replace("|", "/")


def main():
    if not YAML_IN.exists():
        raise SystemExit(f"fonte ausente: {YAML_IN}")
    doc = yaml.safe_load(YAML_IN.read_text(encoding="utf-8")) or {}
    obras = doc.get("obras", []) or []

    L = []
    L.append("# Catálogo de compras — livros que o z-library não devolve")
    L.append("")
    L.append("> **O que isto é:** a fila de obras necessárias que o acervo não tem **e** que a")
    L.append("> busca no z-library não achou em PT-BR. Para cada uma, o catálogo aponta")
    L.append("> **onde comprar** (prioridade: **Amazon** — físico ou digital/Kindle — depois")
    L.append("> Mercado Livre, Shopee, Saraiva, Cultura, Estantica).")
    L.append(">")
    L.append("> **O que isto NÃO é:** o agente **não compra**. Nenhum pedido, nenhum clique em")
    L.append("> \"comprar\", nenhuma confirmação de pagamento. Comprar é ação do William,")
    L.append("> turno a turno, com aprovação explícita.")
    L.append(">")
    L.append(f"> Gerado em: {doc.get('data')} · por `{doc.get('gerado_por')}`")
    L.append("")

    L.append("## Status possíveis")
    L.append("")
    L.append("| marca | status | o que significa |")
    L.append("|---|---|---|")
    L.append("| 🟡 | `a_comprar` | link no catálogo, esperando decisão |")
    L.append("| 🟠 | `em_compra` | pedido feito, aguardando entrega |")
    L.append("| 🔵 | `comprado` | comprado, ainda não chegou |")
    L.append("| 🟢 | `recebido` | chegou — então entra no acervo (`data/biblioteca/`) e no BookOrbit |")
    L.append("| ⚪ | `sem_link` | busca feita, nenhuma loja achou — precisa de busca manual |")
    L.append("| ⚫ | `descartado` | descartado de propósito |")
    L.append("")

    cont = {}
    for o in obras:
        cont[o.get("status", "sem_link")] = cont.get(o.get("status", "sem_link"), 0) + 1
    L.append("## Panorama")
    L.append("")
    L.append(f"**Total no gap:** {len(obras)} obras")
    L.append("")
    L.append("| status | nº |")
    L.append("|---|---|")
    for s in ORDEM_STATUS:
        if cont.get(s):
            L.append(f"| {ICO[s]} `{s}` | {cont[s]} |")
    L.append("")

    com = [o for o in obras if o.get("lojas")]
    sem = [o for o in obras if not o.get("lojas")]

    L.append(f"## 1. Onde comprar agora ({len(com)} obras com link)")
    L.append("")
    if com:
        L.append("Prioridade de loja: **Amazon** primeiro (tem físico e Kindle).")
        L.append("")
        for o in com:
            tit = esc(o.get("titulo"))
            aut = esc(o.get("autor")) or "—"
            L.append(f"### {o.get('titulo')} — {o.get('autor') or '(autor não informado)'}")
            L.append("")
            L.append(f"- **Gênero:** {o.get('genero')} · **Listas que citam:** {o.get('n_listas')} · "
                     f"**Prioridade:** {o.get('prioridade')}")
            L.append(f"- **Status:** {ICO.get(o.get('status'), '⚪')} `{o.get('status')}`")
            for l in o["lojas"]:
                marca = "⭐ " if l.get("loja") == "amazon" else ""
                L.append(f"- {marca}[{l.get('loja_nome')}]({l.get('url')}) — "
                         f"{esc(l.get('titulo_anuncio'))} _(aderência {l.get('score_aderencia')})_")
            L.append("")
    else:
        L.append("_Nenhuma obra com link ainda._")
        L.append("")

    L.append(f"## 2. Pendentes sem link ({len(sem)} obras)")
    L.append("")
    L.append("A busca pública não achou anúncio em loja para estes títulos. Os casos")
    L.append("comuns são: edição antiga esgotada, título em catálogoEditor com outro nome,")
    L.append("ou a obra só existe em formato digital fora de loja.")
    L.append("")
    L.append("| obra | autor | gênero | listas |")
    L.append("|---|---|---|---|")
    for o in sem:
        L.append(f"| {esc(o.get('titulo'))} | {esc(o.get('autor')) or '—'} | "
                 f"{o.get('genero')} | {o.get('n_listas')} |")
    L.append("")

    L.append("## 3. Como usar (fluxo do William)")
    L.append("")
    L.append("1. **Escolha** a obra no catálogo acima (ou peça uma lista por prioridade).")
    L.append("2. **Compre** você mesmo, no link, na loja que preferir.")
    L.append("3. **Diga-me** o que comprou (e se é físico ou Kindle).")
    L.append("4. **Eu** recebo o arquivo (Kindle → descompactar; físico → foto do ISBN para")
    L.append("   busca), converto para `.md`, catalogo na KB e subo no BookOrbit.")
    L.append("5. **O status** da obra muda para `recebido` e ela entra na rampa.")
    L.append("")
    L.append("## 4. Sobre o Amazon (a parte que precisa do navegador)")
    L.append("")
    L.append("O agente **não** consegue ler as páginas de produto do Amazon por `fetch` direto:")
    L.append("a Amazon bloqueia requisição sem navegador e devolve uma página de \"continuar")
    L.append("comprando\". Os links do catálogo vêm do **SearXNG** (busca real, com URL verificada),")
    L.append("e a **preço/formato** só pode ser confirmado abrindo o link no navegador logado")
    L.append("(Flambo/PhreshOS) ou no seu próprio celular.")
    L.append("")
    L.append("O PhreshOS estava **offline** na data deste catálogo (última presença no")
    L.append("tailnet: 6 dias atrás). Assim que voltar, dá para conferir preço e formato")
    L.append("de cada link automaticamente.")
    L.append("")

    MD_OUT.parent.mkdir(parents=True, exist_ok=True)
    MD_OUT.write_text("\n".join(L) + "\n", encoding="utf-8")
    print(f"[catalogo-compras-md] gravado: {MD_OUT} ({len(com)} com link / {len(sem)} sem)")


if __name__ == "__main__":
    sys.exit(main())
