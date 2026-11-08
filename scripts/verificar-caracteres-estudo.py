#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
verificar-caracteres-estudo.py — detector de CORRUPCAO DE GERACAO (v2).

Problema real (7a ocorrencia em 2026-11-07): o gerador de texto insere
caracteres CJK / cirilicos / arabe / palavras inglesas no meio de frases
portuguesas. Nao quebra o YAML, nao quebra o lint, e so aparece quando
alguem LE.

Este script varre e reporta. NAO corrige sozinho (correcao precisa de
contexto) — imprime linha + trecho para o humano/IA corrigir.

v2 (2026-11-07) — 3 correcoes:
  1) GREGO LEGITIMO nao e mais acusado (nota de estudo biblica usa o grego).
     Use --sem-grego para um documento que NAO deveria ter grego.
  2) Detecta COLAGEM de palavra inglesa dentro de palavra portuguesa
     (ex.: "negandoAquele", "osStudents", "comoPermanecer").
  3) Detecta TOKEN com maiuscula no meio (ex.: "SocorreDois", "deDois").

Uso:
  python3 scripts/verificar-caracteres-estudo.py <arquivo.md> [arquivo2.md ...]
  python3 scripts/verificar-caracteres-estudo.py data/estudos/   # varre a arvore
  python3 scripts/verificar-caracteres-estudo.py --sem-grego <arquivo.md>
"""
import re
import sys
import unicodedata
from pathlib import Path

CJK = re.compile(r'[一-鿿぀-ヿ가-힯Ѐ-ӿ؀-ۿ֐-׿]')

# palavras inglesas que NUNCA aparecem em nota de estudo em PT
EN_SOLTAS = re.compile(
    r'\b(designed|actually|really|however|therefore|chapter|paragraph|reading|reader|'
    r'novel|story|plot|character|summary|outline|content|template|example|'
    r'the|and|with|from|that|this|which|would|could|should)\b',
    re.IGNORECASE)

# COLAGEM: palavra inglesa colada dentro de palavra portuguesa (sem espaco).
# Usa apenas radicais longos que NAO existem em portugues.
EN_LONG = (
    "these|those|their|there|would|could|should|about|because|concerned|declared|"
    "testimony|behavior|judgment|worship|church|believer|community|author|comment|"
    "chapter|verse|reading|writing|teaching|spirit|truth|darkness|confession|"
    "promise|anointing|remain|abide|brother|children|everything|question|answer|"
    "number|people|person|things|where|follows|letter|believe|remains|follows"
)
EN_COLADO = re.compile(
    r"[A-Za-zÁÀÂÃÉÈÊÍÌÎÓÒÔÕÚÙÇãõáéíóúâêô]{2}"
    r"(?:" + EN_LONG + r")"
    r"[A-Za-zÁÀÂÃÉÈÊÍÌÎÓÒÔÕÚÙÇãõáéíóúâêô]{2}",
    re.IGNORECASE)

# TOKEN com maiuscula no meio, comprimento >= 8 (ex.: "negandoAquele")
TOKEN_COLADO = re.compile(
    r"\b[a-záéíóúâêôãõç]{2,}[A-ZÁÀÂÃÉÈÊÍÌÎÓÒÔÕÚ][a-záéíóúâêôãõç]{2,}\b")

# grego (basico + politonico) — legitimo em nota de estudo biblica
GREEKO_CH = re.compile(r"[Ͱ-Ͽἀ-῿]")
# alfabetos corrompidos (o grego entra aqui, mas e filtrado depois)
SCRIPTS_CORROMPIDOS = (
    "CJK", "CYRILLIC", "ARABIC", "HEBREW", "GREEK", "HIRAGANA", "KATAKANA",
    "HANGUL", "THAI", "DEVANAGARI", "BENGALI", "TAMIL", "ARMENIAN", "GEORGIAN",
    "ETHIOPIC", "CHEROKEE", "MONGOLIAN", "TIBETAN", "SYRIAC", "THAANA",
    "KHMER", "LAO", "MYANMAR", "YI ", "BRAILLE",
)

# pontuacao tipografica e simbolos legitimos
PERMITIDOS = set(
    "·§°ºª—–…“”‘’«»×÷→←⇒↔≈≤≥≠•‣✓✗⚠★☆①②③④⑤⑥⑦⑧⑨⑩∑∞⚡○"
    "┌┐└┘├┤┬┴┼─│═║╔╗╚╝"
)


def corrompido(ch, sem_grego=False):
    """True se o glifo veio de outro alfabeto (corrupcao de geracao)."""
    if ch in PERMITIDOS:
        return False
    try:
        nm = unicodedata.name(ch)
    except ValueError:
        return True
    if not sem_grego and "GREEK" in nm:
        return False
    return any(k in nm for k in SCRIPTS_CORROMPIDOS)


def dentro_de_aspas(linha, pos):
    """True se a posicao esta dentro de aspas duplas (citacao literal em ingles = legitimo)"""
    return linha.count('"', 0, pos) % 2 == 1


def varrer(path, sem_grego=False):
    p = Path(path)
    if p.is_dir():
        files = sorted(p.rglob('*.md'))
    else:
        files = [p]
    achados = []
    for f in files:
        try:
            txt = f.read_text(encoding='utf-8')
        except Exception as e:
            print(f'  [ERRO] {f}: {e}')
            continue
        for i, l in enumerate(txt.split('\n'), 1):
            if CJK.search(l):
                achados.append((str(f), i, 'CJK/estrangeiro', l.strip()[:150]))
                continue
            for ch in l:
                if corrompido(ch, sem_grego):
                    try:
                        nm = unicodedata.name(ch)
                    except ValueError:
                        nm = '?'
                    achados.append((str(f), i, f'ALFABETO ESTRANHO U+{ord(ch):04X} {nm}',
                                    l.strip()[:150]))
                    break
            else:
                # sem corrupcao de glifo: checar colagem de token
                for m in EN_COLADO.finditer(l):
                    if dentro_de_aspas(l, m.start()):
                        continue
                    achados.append((str(f), i, f'INGLES COLADO "{m.group()}"', l.strip()[:150]))
                for m in TOKEN_COLADO.finditer(l):
                    if dentro_de_aspas(l, m.start()):
                        continue
                    if GREEKO_CH.search(m.group()):
                        continue
                    achados.append((str(f), i, f'TOKEN COLADO "{m.group()}"', l.strip()[:150]))
    return achados


def main():
    args = sys.argv[1:]
    sem_grego = False
    if '--sem-grego' in args:
        sem_grego = True
        args = [a for a in args if a != '--sem-grego']
    if not args:
        print(__doc__)
        return 1
    total = 0
    for alvo in args:
        achados = varrer(alvo, sem_grego)
        total += len(achados)
        print(f'\n=== {alvo}: {len(achados)}suspeita(s) ===')
        for f, i, tipo, trecho in achados[:80]:
            print(f'  {f}:{i}  [{tipo}]  {trecho}')
        if len(achados) > 80:
            print(f'  ... +{len(achados)-80} outras')
    print(f'\nTOTAL: {total} suspeita(s)')
    return 0 if total == 0 else 1


if __name__ == '__main__':
    sys.exit(main())
