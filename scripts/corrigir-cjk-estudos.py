#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CORRIGE A CORRUPCAO DE CARACTERES ESTRANGEIROS INJETADOS NOS ARQUIVOS DE ESTUDO
===============================================================================
Descoberta 2026-11-05 (ao auditar o Memos a pedido do William):

15 memos publicados + 16 arquivos locais tem caracteres CHINESES e PALAVRAS EM
INGLES vazados no meio do portugues. Exemplos medidos:

  - "O segundo grande. Tradição romântica封闭 — narradora em 1ª pessoa"
  - "Socorro não é um补丁 colado na sua vida"
  - "Para o大多是 cristão reformado"
  - "O jejum é練習 de dependência (oDaily-manutenção)"
  - "fica 2 anos noEssentially de Casa"
  - "OsLucas de Éfeso"
  - "reverte em Wisdom" / "não com[newspaper]" / "o hungry ir"
  - "### 4.5survey de autoras"
  - "**B. Natureza daHalucinação da prática**"

Nao e conteudo estrangeiro de verdade: e corrupcao de geracao — o token
estrangeiro saiu no meio da frase portuguesa. Ja estava no git quando os
arquivos foram commitados (verificado no historico), nao foi edicao posterior.

REGRA DE ESCOPO:
  - data/biblioteca/** NAO e tocado. Ali CJK/ingles e conteudo legitimo
    (livros em chines, dicionarios, e as citacoes literais de Whitney).
  - So data/estudos/**, e so onde o contexto prova que e corrupcao.

Uso:
  python3 scripts/corrigir-cjk-estudos.py --auditar     # so relata
  python3 scripts/corrigir-cjk-estudos.py --aplicar      # corrige arquivos
  python3 scripts/corrigir-cjk-estudos.py --republicar   # re-posta no Memos
"""
from __future__ import annotations

import argparse
import importlib.util
import re
from pathlib import Path

ROOT = Path("/home/willian/study-agent")
PAD_CJK = re.compile(r"[\u4e00-\u9fff]+")

# --------------------------------------------------------------------------
# MAPA DE CORRECAO — (trecho_corrompido, substituicao_correta).
# Cada contexto foi lido antes de montar esta lista.
# --------------------------------------------------------------------------
CORRECOES: list[tuple[str, str]] = [
    # --- ebdi-efesios / roteiro ---
    ("O顺势: o que resolve", "O decisivo: o que resolve"),
    # --- devocional-02 ---
    ("Socorro não é um补丁 colado", "Socorro não é um remendo colado"),
    # --- devocional-16 ---
    ("construir a脚的conditions para a sabedoria", "construir as condições para a sabedoria"),
    ("A播放器 muda: a correção", "A postura muda: a correção"),
    ("A Sabiedade准备了 a mesa; o que falta é o hungry ir.",
     "A Sabiedade preparou a mesa; o que falta é o ir até lá."),
    ("não com[newspaper]", "não com descaso"),
    ("reverte em Wisdom", "reverte em sabedoria"),
    ("princípio da wisdom", "princípio da sabedoria"),
    ("O escarnecedor não éutralizado", "O escarnecedor não é neutralizado"),
    # --- efesios ---
    ('em forma de“是”', 'em forma de “é”'),
    ("Duas hipóteses有很多:", "Duas hipóteses possíveis:"),
    ("**negócio de臭氧**", "**negócio de incenso**"),
    ("amor\n 基督iano aqui é", "amor\n cristão aqui é"),
    ("fica 2 anos noEssentially de Casa", "fica 2 anos na escola de Tiranho"),
    ("OsLucas de Éfeso queimam os livros de magia | At 19:11-12",
     "Os praticantes de magia de Éfeso queimam os livros de magia | At 19:13-14"),
    ("|reduction de 3:1-13", "| **redução** de 3:1-13"),
    ("|é o trecho mais difícil isolado", "| **é o trecho mais difícil isolado**"),
    ("|aplicação anacrônica", "| **aplicação anacrônica**"),
    # --- ficcao 02 ---
    ("convém、性izar o", "convém priorizar o"),
    ("### 4.5survey de autoras", "### 4.5 Survey de autoras"),
    # --- ficcao 06 ---
    ("Tradição romântica封闭", "Tradição romântica"),
    # --- filemon ---
    ("vem坏事 da dívida infinita", "vem antes da dívida infinita"),
    ("Não por fraqueza: por策略.", "Não por fraqueza: por estratégia."),
    ("tendo-se门口的 no senhor", "tendo-se acercando do senhor"),
    ("não invoca汝 um decreto", "não invoca um decreto"),
    ("e que青少年 vão amar", "e que os adolescentes vão amar"),
    ("sobre以外の estruturas", "sobre outras estruturas"),
    ("é人文mente mais forte", "é humanamente mais forte"),
    # --- hermeneutica ---
    ("para ver como学者 fiéis pregaram", "para ver como estudiosos fiéis pregaram"),
    # --- jejum ---
    ("vaidade ou por，目的是 provocar Deus", "vaidade ou por proveito, para provocar Deus"),
    ("Para o大多是 cristão reformado", "Para a maioria cristã reformada"),
    ("está embaixo da一樣", "está embaixo da mesma lei"),
    ("O jejum é練習 de dependência (oDaily-manutenção)",
     "O jejum é prática de dependência (manutenção diária)"),
    ("jejuns de灾后 (Jr 36.6-9; Zc 8.19)",
     "jejuns de crise e de pós-exílio (Jr 36.6-9; Zc 8:19)"),
    ("**D. Modo de胺 em relação à lei**", "**D. Modo de jejum em relação à lei**"),
    ("não项目建设 biblical", "não construção bíblica"),
    ("Ocasional: em，我说各的情况 específicas.", "Ocasional: em todas as circunstâncias específicas."),
    ("(o mais、采购 por longe)", "(o mais citado por longe)"),
    ("### 4.4 O jejum como集團 tool de discernimento", "### 4.4 O jejum como ferramenta de discernimento"),
    ("### 4.5 O jejum como集團 tool de libertação", "### 4.5 O jejum como ferramenta de libertação"),
    ("**Jejum como魔术**", "**Jejum como magia**"),
    ("em dia de trabalho normal, sem前世远超", "em dia de trabalho normal, sem exageros"),
    ("no lugar da comida, e。余下的 em segredo", "no lugar da comida, e o restante em segredo"),
    ("notas de背景 cultural", "notas de contexto cultural"),
    ("**B. Natureza daHalucinação da prática**", "**B. Natureza da prática**"),
    # --- oseias ---
    ("todos死于 ou em ~15 anos", "todos morreram ou em ~15 anos"),
    ('**Aserá** (女神, "símbolo de madeira")', '**Aserá** (deusa, "símbolo de madeira")'),
    # --- portugues aulas ---
    ("com专职 fonoaudiólogos", "com fonoaudiólogos"),
    ("é欢呼, exaltação", "é aplauso, exaltação"),
    ("(que foi省略ido, isto é, omitido)", "(que foi omitido, isto é, suprimido)"),
    ("a gente aceita como外来", "a gente aceita como estrangeirismo"),
    ("em极少数 palavras", "em pouquíssimas palavras"),
    ("foram às ruas exigir教育改革", "foram às ruas exigir reformas educacionais"),
    # --- devocional-13 / 10 / 11 / 05 (versoes publicadas divergentes do local) ---
    ("e a这话 é para você", "e a mensagem é para você"),
    ("como **adorno**, não como罚", "como **adorno**, não como castigo"),
    ("a的形成 é awesome", "a formação é saudável"),
    ("não a primeira来说 do dia", "não a primeira refeição do dia"),
    ("uma高度重视, um hábito", "uma atenção, um hábito"),
    ("Peça今天: que Ele cuide", "Peça hoje: que Ele cuide"),
    ("dá sabedoria aos が施", "dá sabedoria aos símplices"),
    ("### 1.2 Uma推測 antiga e minoritária", "### 1.2 Uma hipótese antiga e minoritária"),
    ("A **questão do场合\"adverbial\"**", "A **questão do caso \"adverbial\"**"),
]


def arquivos() -> list[Path]:
    return sorted((ROOT / "data/estudos").rglob("*.md"))


def corrigir_texto(texto: str) -> tuple[str, int]:
    n = 0
    for alvo, sub in CORRECOES:
        if alvo in texto:
            cnt = texto.count(alvo)
            texto = texto.replace(alvo, sub)
            n += cnt
    return texto, n


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--auditar", action="store_true")
    ap.add_argument("--aplicar", action="store_true")
    ap.add_argument("--republicar", action="store_true")
    args = ap.parse_args()

    if args.auditar:
        total = 0
        for p in arquivos():
            t = p.read_text(encoding="utf-8")
            ms = PAD_CJK.findall(t)
            if ms:
                total += len(ms)
                print(f"{len(ms):4d}  {p.relative_to(ROOT)}")
                for m in PAD_CJK.finditer(t):
                    a = max(0, m.start() - 50)
                    b = min(len(t), m.end() + 50)
                    print(f"        [{m.group(0)}]  ...{t[a:b]}...")
        print(f"\nTOTAL: {total} corrupcoes CJK")
        return 0

    if args.aplicar:
        total = 0
        for p in arquivos():
            t = p.read_text(encoding="utf-8")
            novo, n = corrigir_texto(t)
            if novo == t:
                continue
            ainda = PAD_CJK.findall(novo)
            if ainda:
                print(f"!! {p.relative_to(ROOT)} restaram: {sorted(set(ainda))}")
            p.write_text(novo, encoding="utf-8")
            total += n
            print(f"OK {p.relative_to(ROOT)}  ({n})")
        print(f"\nTOTAL corrigido: {total}")
        return 0

    if args.republicar:
        spec = importlib.util.spec_from_file_location(
            "cur", ROOT / "scripts/curador-memos.py")
        cur = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cur)
        cur.carregar_env()
        feitos = 0
        for m in cur.listar():
            if (m.get("creator") or "") != "users/willianmendesf":
                continue
            c = m.get("content") or ""
            if not PAD_CJK.search(c):
                continue
            uid = cur.uid(m)
            novo, n = corrigir_texto(c)
            if novo == c:
                print(f"!! {uid}: sem regra aplicavel")
                continue
            r = cur.api("PATCH", f"/api/v1/memos/{uid}", {"content": novo})
            ok = isinstance(r, dict) and r.get("code") is None
            print(f"{'OK ' if ok else 'ERRO'} {uid}  ({n})")
            feitos += 1
        print(f"\nrepublicados: {feitos}")
        return 0

    ap.print_help()
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
