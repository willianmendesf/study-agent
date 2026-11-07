#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
verificar-caracteres-estudo.py — detector de CORRUPCAO DE GERACAO.

Problema real (7a ocorrencia em 2026-11-07): o gerador de texto insere
caracteres CJK / cirilicos / arabe / palavras inglesas no meio de frases
portuguesas. Nao quebra o YAML, nao quebra o lint, e so aparece quando
alguem LÊ.

Este script varre e reporta. NAO corrige sozinho (correcao precisa de
contexto) — imprime linha + trecho para o humano/IA corrigir.

Uso:
  python3 scripts/verificar-caracteres-estudo.py <arquivo.md> [arquivo2.md ...]
  python3 scripts/verificar-caracteres-estudo.py data/estudos/   # varre a arvore
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


# CORRUPCAO REAL = glifo de OUTRO IDIOMA vazado no meio de frase portuguesa.
# Detectado pelo NOME do caractere Unicode (que traz o nome do alphabeto/script).
SCRIPTS_CORROMPIDOS = (
    "CJK", "CYRILLIC", "ARABIC", "HEBREW", "GREEK", "HIRAGANA", "KATAKANA",
    "HANGUL", "THAI", "DEVANAGARI", "BENGALI", "TAMIL", "ARMENIAN", "GEORGIAN",
    "ETHIOPIC", "CHEROKEE", "MONGOLIAN", "TIBETAN", "SYRIAC", "THAANA",
    "KHMER", "LAO", "MYANMAR", "YI ", "BRAILLE",
)


def corrompido(ch):
    """True se o glifo veio de outro alfabeto (corrupcao de geracao)."""
    try:
        nm = unicodedata.name(ch)
    except ValueError:
        return True
    return any(k in nm for k in SCRIPTS_CORROMPIDOS)


def varrer(path):
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
                if corrompido(ch):
                    try:
                        nm = unicodedata.name(ch)
                    except ValueError:
                        nm = '?'
                    achados.append((str(f), i, f'ALFABETO ESTRANHO U+{ord(ch):04X} {nm}',
                                    l.strip()[:150]))
                    break
    return achados


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return 1
    total = 0
    for alvo in sys.argv[1:]:
        achados = varrer(alvo)
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
