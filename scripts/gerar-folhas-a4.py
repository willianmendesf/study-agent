#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GERADOR DE FOLHAS A4 — Study-Agent
==================================
Produz folhas imprimíveis (A4) para estudo, em PDF, a partir de um catálogo
de modelos declarado em Python.

Por que script e não markdown?
  O William quer FOLHAS A4 para imprimir e preencher à mão. Markdown não tem
  página, nem régua, nem caixa de check-box. O PDF final precisa ter:
    - A4 real (595 x 842 pt), margens de 15 mm (área de escrita útil);
    - caixas de preenchimento desenhadas (não só linhas de underscore);
    - 2 folhas por página para folhas "de bolso" (fichamento rápido).

Uso:
    python3 scripts/gerar-folhas-a4.py --saida data/estudos/notas/folhas-de-estudo/folhas.pdf
    python3 scripts/gerar-folhas-a4.py --saida ... --so ficha-livro   # só um modelo
    python3 scripts/gerar-folhas-a4.py --listar                       # só lista os modelos

Requer: reportlab (venv em /home/willian/.venvs/folhas).
"""

from __future__ import annotations

import argparse
import os
import sys

try:
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import mm
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    from reportlab.pdfgen import canvas
except ImportError:  # pragma: no cover
    sys.stderr.write(
        "ERRO: reportlab ausente. Instale:\n"
        "  python3 -m venv ~/.venvs/folhas && ~/.venvs/folhas/bin/pip install reportlab\n"
    )
    raise SystemExit(2)


# ---------------------------------------------------------------- fontes
# Helvetica (padrao do reportlab) e' Latin-1: quebra em "—" (em dash) e em
# bullets. DejaVuSans e' Unicode completo — obrigatorio para PT-BR.
_FONTES = {
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf": "Folha",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf": "Folha-Bold",
}
_FONTE_OK = False
for _caminho, _nome in _FONTES.items():
    if os.path.exists(_caminho):
        pdfmetrics.registerFont(TTFont(_nome, _caminho))
_FONTE_OK = all(os.path.exists(c) for c in _FONTES)
FAMILIA = "Folha" if _FONTE_OK else "Helvetica"
FAMILIA_B = "Folha-Bold" if _FONTE_OK else "Helvetica-Bold"


# ---------------------------------------------------------------- paleta
TINTA = "#1a1a1a"
CINZA = "#8a8a8a"
CINZA_CLARO = "#c9c9c9"
AZUL = "#2f4858"
VERMELHO = "#a63a3a"
VERDE = "#3d6b4a"

LARGURA, ALTURA = A4
MARGEM = 15 * mm
LARGURA_UTIL = LARGURA - 2 * MARGEM


# ---------------------------------------------------------------- helpers
def fonte(c, tam=9, negrito=False, cor=TINTA, familia=None):
    if familia is None:
        familia = FAMILIA_B if negrito else FAMILIA
    c.setFont(familia, tam)
    c.setFillColor(cor)


def linha(c, x, y, larg, cor=CINZA_CLARO, esp=0.5):
    c.setStrokeColor(cor)
    c.setLineWidth(esp)
    c.line(x, y, x + larg, y)


def caixa(c, x, y, larg, alt, cor=CINZA, esp=0.6):
    """Caixa de preenchimento (checkbox ou campo)."""
    c.setStrokeColor(cor)
    c.setLineWidth(esp)
    c.rect(x, y, larg, alt, stroke=1, fill=0)


def cabecalho(c, titulo, subtitulo="", codigo=""):
    """Cabecalho padrao: titulo a esquerda, codigo de ficha a direita.

    O subtitulo fica ABAIXO do titulo com folga (bug de 2026-11-05: o
    subtitulo colidia com os rotulos da primeira linha de campos).
    """
    y_titulo = ALTURA - MARGEM - 11
    fonte(c, 12.5, True, AZUL)
    c.drawString(MARGEM, y_titulo, titulo)
    if codigo:
        fonte(c, 7, False, CINZA)
        c.drawRightString(LARGURA - MARGEM, y_titulo, codigo)
    y_linha = y_titulo - 10
    if subtitulo:
        fonte(c, 7.5, False, CINZA)
        c.drawString(MARGEM, y_linha - 9, subtitulo)
        y_linha -= 19
    linha(c, MARGEM, y_linha, LARGURA_UTIL, AZUL, 1.1)
    return y_linha

def campos_iguais(c, y, etiquetas, larg=None, altura=17, gap=6, prefixo=""):
    """Linha de campos com rótulo: [(rótulo, largura_relativa), ...]. Retorna y novo."""
    total = sum(w for _, w in etiquetas)
    larg = larg or (LARGURA_UTIL - gap * (len(etiquetas) - 1))
    x = MARGEM
    for rot, peso in etiquetas:
        w = larg * peso / total
        fonte(c, 6.5, True, CINZA)
        c.drawString(x, y + altura + 5, rot)
        caixa(c, x, y, w, altura)
        if prefixo:
            fonte(c, 7, False, CINZA_CLARO)
            c.drawString(x + 3, y + 5, prefixo)
        x += w + gap
    return y - altura - 12


def regua(c, y, n=18, esp=24):
    """Linhas pautadas (para escrita à mão)."""
    for i in range(n):
        linha(c, MARGEM, y - i * esp, LARGURA_UTIL)
    return y - (n - 1) * esp


def bloco_rotulado(c, x, y, larg, rotulo, altura, cor=CINZA):
    fonte(c, 6.5, True, cor)
    c.drawString(x, y + 3, rotulo)
    caixa(c, x, y - altura, larg, altura, cor, 0.6)
    return y - altura


def rodape(c, texto):
    fonte(c, 6.5, False, CINZA)
    c.drawCentredString(LARGURA / 2, MARGEM / 2 - 2, texto)


def nova_pagina(c):
    c.showPage()


# ================================================================ MODELOS
def m_ficha_livro(c):
    """FICHA DE LIVRO — o fichamento propriamente dito."""
    cabecalho_y = cabecalho(c, "FICHA DE LIVRO", "fichamento de leitura — uma obra, uma ficha",
              "FL-01")
    y = cabecalho_y - 28

    # identificação
    y = campos_iguais(c, y, [
        ("AUTOR", 2), ("TÍTULO", 3), ("EDIÇÃO/ANO", 1.2)], altura=16)
    y = campos_iguais(c, y, [
        ("ÁREA / TEMA", 1.6), ("Nº DE FICHAS", 1), ("DATA", 1.2)], altura=16)

    # --- o que este livro afirma (o núcleo) ---
    fonte(c, 8.5, True, AZUL)
    c.drawString(MARGEM, y - 2, "1 · O QUE ESTE LIVRO AFIRMA (em 3 linhas)")
    y -= 8
    y = regua(c, y, n=4)
    y -= 18

    # --- estrutura ---
    fonte(c, 8.5, True, AZUL)
    c.drawString(MARGEM, y, "2 · ESTRUTURA (partes / capítulos /argumento)")
    y -= 8
    y = regua(c, y, n=6)
    y -= 18

    # --- ideias principais, uma por linha ---
    fonte(c, 8.5, True, AZUL)
    c.drawString(MARGEM, y, "3 · IDEIAS PRINCIPAIS (a IDEA central + apoio)")
    y -= 8
    for i in range(5):
        caixa(c, MARGEM, y - 9, 7, 7)
        linha(c, MARGEM + 12, y - 5, LARGURA_UTIL - 12)
        y -= 16
    y -= 8

    # --- citação ---
    fonte(c, 8.5, True, AZUL)
    c.drawString(MARGEM, y, "4 · CITAÇÃO QUE GUARDEI (com página)")
    y -= 8
    y = bloco_rotulado(c, MARGEM, y, LARGURA_UTIL, "texto", 40)
    y -= 16

    # --- vocabulário / conceitos ---
    fonte(c, 8.5, True, AZUL)
    c.drawString(MARGEM, y, "5 · CONCEITOS / TERMOS QUE NÃO ENTENDI")
    y -= 8
    for i in range(4):
        linha(c, MARGEM, y, LARGURA_UTIL * 0.55)
        linha(c, MARGEM + LARGURA_UTIL * 0.6, y, LARGURA_UTIL * 0.4)
        y -= 15
    y -= 10

    # --- avaliação crítica ---
    fonte(c, 8.5, True, AZUL)
    c.drawString(MARGEM, y, "6 · AVALIAÇÃO: o que é forte, o que é fraco, o que discordo")
    y -= 8
    y = regua(c, y, n=4)

    rodape(c, "IAM · folhas de estudo — ficha de livro")


def m_ficha_livro_reverso(c):
    """Verso da ficha —下半: uso, cruzamentos, retenção."""
    cabecalho_y = cabecalho(c, "FICHA DE LIVRO (verso)", "uso, cruzamentos, retenção",
              "FL-01v")
    y = cabecalho_y - 28

    fonte(c, 8.5, True, AZUL)
    c.drawString(MARGEM, y, "7 · ONDE VOU USAR ISSO (aula / sermão / conversa / pesquisa)")
    y -= 8
    for i in range(3):
        caixa(c, MARGEM, y - 9, 7, 7)
        linha(c, MARGEM + 12, y - 5, LARGURA_UTIL - 12)
        y -= 16
    y -= 10

    fonte(c, 8.5, True, AZUL)
    c.drawString(MARGEM, y, "8 · CRUZAMENTOS (com quais outros livros / autores / passages)")
    y -= 8
    y = regua(c, y, n=4)
    y -= 14

    fonte(c, 8.5, True, AZUL)
    c.drawString(MARGEM, y, "9 · PERGUNTAS QUE AINDA NÃO RESPONDI")
    y -= 8
    for i in range(4):
        linha(c, MARGEM, y, LARGURA_UTIL)
        y -= 15
    y -= 10

    fonte(c, 8.5, True, AZUL)
    c.drawString(MARGEM, y, "10 · O QUE NÃO DEVO RELEMBRAR / O QUE É SECUNDÁRIO")
    y -= 8
    y = regua(c, y, n=3)
    y -= 16

    # retenção
    fonte(c, 8.5, True, VERDE)
    c.drawString(MARGEM, y, "11 · RETENÇÃO — o que NÃO posso esquecer (3 itens, com送 verificação)")
    y -= 8
    for i in range(3):
        linha(c, MARGEM, y, LARGURA_UTIL)
        y -= 15
    y -= 6
    fonte(c, 6.5, False, CINZA)
    c.drawString(MARGEM, y, "quando eu me lembrar disto sem olhar a ficha?  (teste de Buschke / recall)")
    y -= 14

    fonte(c, 6.5, True, CINZA)
    c.drawString(MARGEM, y, "Data da 1ª revisão: ______    2ª: ______    3ª: ______")
    y -= 12
    fonte(c, 6.5, False, CINZA)
    c.drawString(MARGEM, y, "Revisões espaçadas: 1 dia · 3 dias · 1 semana · 1 mês · 3 meses")

    rodape(c, "IAM · folhas de estudo — ficha de livro (verso)")


def m_preparacao_aula(c):
    """PREPARAÇÃO DE AULA — o roteiro do professor."""
    cabecalho_y = cabecalho(c, "PREPARAÇÃO DE AULA", "do texto ao sermão / à aula — o caminho antes de subir",
              "PA-01")
    y = cabecalho_y - 28

    y = campos_iguais(c, y, [
        ("TEMA / TÍTULO", 3), ("DATA", 1.2), ("DURAÇÃO", 1)], altura=16)
    y = campos_iguais(c, y, [
        ("TEXTO BASE (livro/cap./vers.)", 2), ("PÚBLICO", 1.5),
        ("Nº DE PONTOS", 1)], altura=16)

    fonte(c, 8.5, True, AZUL)
    c.drawString(MARGEM, y, "1 · O QUE EU QUERO QUE OUVINHO LEVE (ideia única)")
    y -= 8
    y = regua(c, y, n=3)
    y -= 16

    fonte(c, 8.5, True, AZUL)
    c.drawString(MARGEM, y, "2 · O TEXTO (o que ele diz — leitura própria, antes dos autores)")
    y -= 8
    y = regua(c, y, n=4)
    y -= 16

    fonte(c, 8.5, True, AZUL)
    c.drawString(MARGEM, y, "3 · O CONTEXTO (autor, data,目的是, cultura,“Gosto de quem”?)")
    y -= 8
    y = regua(c, y, n=3)
    y -= 16

    fonte(c, 8.5, True, AZUL)
    c.drawString(MARGEM, y, "4 · OS PONTOS (a estrutura que sustentará a aula)")
    y -= 8
    for i in range(4):
        caixa(c, MARGEM, y - 9, 7, 7)
        linha(c, MARGEM + 12, y - 5, LARGURA_UTIL - 12)
        y -= 16
    y -= 8

    fonte(c, 8.5, True, AZUL)
    c.drawString(MARGEM, y, "5 · APLICAÇÃO (o que isso exige de mim e do ouvinte)")
    y -= 8
    y = regua(c, y, n=3)
    y -= 16

    fonte(c, 8.5, True, AZUL)
    c.drawString(MARGEM, y, "6 · PERGUNTAS PARA A TURMA (para a aula ser diálogo, não palestra)")
    y -= 8
    for i in range(3):
        linha(c, MARGEM, y, LARGURA_UTIL)
        y -= 15
    y -= 10

    fonte(c, 8.5, True, VERDE)
    c.drawString(MARGEM, y, "7 · FICHA DO LIVRO USADA NESTA AULA (qual, o que aproveitei)")
    y -= 8
    y = regua(c, y, n=2)

    rodape(c, "IAM · folhas de estudo — preparação de aula")


def m_resumo(c):
    """RESUMO — de 1 página, com teste deLOGO final."""
    cabecalho_y = cabecalho(c, "RESUMO", "uma página — se não couber, não é resumo, é transcrição",
              "RS-01")
    y = cabecalho_y - 28

    y = campos_iguais(c, y, [
        ("FONTE (livro, cap., pág.)", 3), ("TIPO", 1.2), ("DATA", 1.2)], altura=16)

    fonte(c, 8.5, True, AZUL)
    c.drawString(MARGEM, y, "1 · TEMA EM UMA FRASE")
    y -= 8
    y = regua(c, y, n=2)
    y -= 14

    fonte(c, 8.5, True, AZUL)
    c.drawString(MARGEM, y, "2 · O ARGUMENTO (a sequência das ideias, em ordem)")
    y -= 8
    for i in range(6):
        caixa(c, MARGEM, y - 9, 7, 7)
        linha(c, MARGEM + 12, y - 5, LARGURA_UTIL - 12)
        y -= 16
    y -= 8

    fonte(c, 8.5, True, AZUL)
    c.drawString(MARGEM, y, "3 · CONCEITOS-CHAVE (termo → definição em 3-6 palavras)")
    y -= 8
    for i in range(4):
        linha(c, MARGEM, y, LARGURA_UTIL * 0.4)
        linha(c, MARGEM + LARGURA_UTIL * 0.44, y, LARGURA_UTIL * 0.56)
        y -= 15
    y -= 10

    fonte(c, 8.5, True, VERDE)
    c.drawString(MARGEM, y, "4 · TESTE DE RETENÇÃO (feche o livro e responda)")
    y -= 8
    for i in range(3):
        linha(c, MARGEM, y, LARGURA_UTIL)
        y -= 15
    y -= 8
    fonte(c, 6.5, False, CINZA)
    c.drawString(MARGEM, y, "Se não consegui responder de cabeça, o resumo não funcionou — refaça.")
    y -= 16

    fonte(c, 8.5, True, AZUL)
    c.drawString(MARGEM, y, "5 · PARA ONDE ISSO SERVE (link com outras fichas / aula)")
    y -= 8
    y = regua(c, y, n=2)

    rodape(c, "IAM · folhas de estudo — resumo")


def m_memorizacao(c):
    """MEMORIZAÇÃO — o que fazer com o que foi resumido."""
    cabecalho_y = cabecalho(c, "MEMORIZAÇÃO", "o que entra na cabeça, e como fica lá",
              "MM-01")
    y = cabecalho_y - 28

    y = campos_iguais(c, y, [
        ("FONTE", 2), ("Nº DE ITENS", 1), ("INÍCIO", 1.2)], altura=16)

    fonte(c, 8.5, True, AZUL)
    c.drawString(MARGEM, y, "1 · O QUE PRECISO SABER DE COR (lista fechada)")
    y -= 8
    for i in range(6):
        caixa(c, MARGEM, y - 9, 7, 7)
        linha(c, MARGEM + 12, y - 5, LARGURA_UTIL - 12)
        y -= 16
    y -= 8

    fonte(c, 8.5, True, AZUL)
    c.drawString(MARGEM, y, "2 · POR QUE ISSO PRECISA SER SABIDO (senão, não guardo)")
    y -= 8
    y = regua(c, y, n=2)
    y -= 14

    fonte(c, 8.5, True, AZUL)
    c.drawString(MARGEM, y, "3 · ANCORAGENS (imagens, sons, histórias — o que gruda)")
    y -= 8
    for i in range(3):
        linha(c, MARGEM, y, LARGURA_UTIL)
        y -= 15
    y -= 10

    fonte(c, 8.5, True, VERDE)
    c.drawString(MARGEM, y, "4 · REVISÃO ESPAÇADA (marque a data de cada revisão)")
    y -= 8
    rotulos = ["D0", "D+1", "D+3", "D+7", "D+14", "D+30", "D+90"]
    w = (LARGURA_UTIL - 6 * 4) / len(rotulos)
    x = MARGEM
    for rot in rotulos:
        fonte(c, 6.5, True, CINZA)
        c.drawCentredString(x + w / 2, y + 4, rot)
        caixa(c, x, y - 15, w, 15)
        x += w + 4
    y -= 26

    fonte(c, 8.5, True, AZUL)
    c.drawString(MARGEM, y, "5 · O QUE NÃO ENTROU (o que ficou fora — e por quê)")
    y -= 8
    y = regua(c, y, n=3)
    y -= 14

    fonte(c, 8.5, True, VERDE)
    c.drawString(MARGEM, y, "6 · MEU TESTE (a pergunta que vou me fazer antes da prova)")
    y -= 8
    y = regua(c, y, n=2)

    rodape(c, "IAM · folhas de estudo — memorização")


def m_exegese(c):
    """EXEGESE — a folha de trabalho do texto bíblico (Etapa 0)."""
    cabecalho_y = cabecalho(c, "EXEGESE (folha de trabalho)", "Etapa 0 — leitura própria, antes de consultar autores",
              "EX-01")
    y = cabecalho_y - 28

    y = campos_iguais(c, y, [
        ("REFERÊNCIA", 1.5), ("TÍTULO", 2.5), ("DATA", 1)], altura=16)

    fonte(c, 8.5, True, AZUL)
    c.drawString(MARGEM, y, "1 · O TEXTO (transcrever / paraphrase — semyet, ler o que está escrito)")
    y -= 8
    y = regua(c, y, n=4)
    y -= 14

    fonte(c, 8.5, True, AZUL)
    c.drawString(MARGEM, y, "2 · CONTEXTO LITERAL (anterior / posterior / contexto histórico)")
    y -= 8
    y = regua(c, y, n=3)
    y -= 14

    fonte(c, 8.5, True, AZUL)
    c.drawString(MARGEM, y, "3 · ESTRUTURA DO PASSO (unidades / paralelismo / lógica do argumento)")
    y -= 8
    y = regua(c, y, n=3)
    y -= 14

    fonte(c, 8.5, True, AZUL)
    c.drawString(MARGEM, y, "4 · TERMOS-CHAVE (palavra grega/hebraica + sentido aqui)")
    y -= 8
    for i in range(3):
        linha(c, MARGEM, y, LARGURA_UTIL * 0.35)
        linha(c, MARGEM + LARGURA_UTIL * 0.4, y, LARGURA_UTIL * 0.6)
        y -= 15
    y -= 10

    fonte(c, 8.5, True, AZUL)
    c.drawString(MARGEM, y, "5 · O QUE O TEXTO AFIRMA (a proposição, na minha leitura)")
    y -= 8
    y = regua(c, y, n=3)
    y -= 14

    fonte(c, 8.5, True, VERMELHO)
    c.drawString(MARGEM, y, "6 · DIFICULDADES / PERGUNTAS (ainda sem consultar nenhum autor)")
    y -= 8
    y = regua(c, y, n=3)

    rodape(c, "IAM · folhas de estudo — exegese (Etapa 0)")


def m_arquivo_autor(c):
    """FICHA DE AUTOR / OBRA — o índice do acervo."""
    cabecalho_y = cabecalho(c, "FICHA DE AUTOR / OBRA", "o índice do seu acervo — uma linha por obra",
              "AO-01")
    y = cabecalho_y - 28

    fonte(c, 7, True, CINZA)
    c.drawString(MARGEM, y, "AUTOR")
    linha(c, MARGEM + 40, y, LARGURA_UTIL - 40)
    y -= 16
    fonte(c, 7, True, CINZA)
    c.drawString(MARGEM, y, "ÁREA / TEMA")
    linha(c, MARGEM + 40, y, LARGURA_UTIL * 0.5 - 40)
    fonte(c, 7, True, CINZA)
    c.drawRightString(LARGURA - MARGEM, y, "Nº DE FICHAS")
    linha(c, LARGURA - MARGEM - 60, y, 60)
    y -= 20

    # cabeçalho da tabela
    cols = [(0.00, 0.30, "TÍTULO"), (0.30, 0.16, "AUTOR"), (0.46, 0.14, "ÁREA"),
            (0.60, 0.16, "IDIOMA/ANO"), (0.76, 0.12, "FICHA?"), (0.88, 0.12, "LIDO?")]
    ytop = y
    for frac, larg, rot in cols:
        x = MARGEM + LARGURA_UTIL * frac
        w = LARGURA_UTIL * larg
        fonte(c, 6.5, True, AZUL)
        c.drawString(x + 2, ytop - 8, rot)
        caixa(c, x, ytop - 34, w, 26, CINZA_CLARO, 0.5)
    y = ytop - 34 - 8

    n = 18
    for i in range(n):
        linha(c, MARGEM, y, LARGURA_UTIL, CINZA_CLARO, 0.4)
        y -= 18

    rodape(c, "IAM · folhas de estudo — ficha de autor/obra")


def m_diario_estudo(c):
    """DIÁRIO DE ESTUDO — o registro diário (o que fiz, o que ficou)."""
    cabecalho_y = cabecalho(c, "DIÁRIO DE ESTUDO", "o registro honesto do dia — o que ficou, o que escapou",
              "DE-01")
    y = cabecalho_y - 28

    y = campos_iguais(c, y, [
        ("DATA", 1.2), ("TEMPO (h)", 1), ("MATÉRIA", 2), ("TEXTO BASE", 2)], altura=16)

    fonte(c, 8.5, True, AZUL)
    c.drawString(MARGEM, y, "1 · O QUE FIZ (fatos, nãoFeeling: que livor cap. li)")
    y -= 8
    y = regua(c, y, n=4)
    y -= 14

    fonte(c, 8.5, True, AZUL)
    c.drawString(MARGEM, y, "2 · O QUE ENTENDI (o que mudei na minha cabeça)")
    y -= 8
    y = regua(c, y, n=3)
    y -= 14

    fonte(c, 8.5, True, VERMELHO)
    c.drawString(MARGEM, y, "3 · O QUE NÃO ENTENDI (o que ficou no ar — levar ao especialista)")
    y -= 8
    y = regua(c, y, n=3)
    y -= 14

    fonte(c, 8.5, True, VERDE)
    c.drawString(MARGEM, y, "4 · O QUE VOU FAZER DEPOIS (próxima sessão, tarefa concreta)")
    y -= 8
    for i in range(3):
        caixa(c, MARGEM, y - 9, 7, 7)
        linha(c, MARGEM + 12, y - 5, LARGURA_UTIL - 12)
        y -= 16
    y -= 8

    fonte(c, 8.5, True, AZUL)
    c.drawString(MARGEM, y, "5 · FICHA(S) CRIADA(S) HOJE (código / título)")
    y -= 8
    for i in range(3):
        linha(c, MARGEM, y, LARGURA_UTIL)
        y -= 15

    rodape(c, "IAM · folhas de estudo — diário de estudo")


def m_mapa_mental(c):
    """MAPA CONCEPTUAL — a folha de conexões (uma folha, colada na parede)."""
    cabecalho_y = cabecalho(c, "MAPA CONCEPTUAL", "a folha de colagem — conceitos no centro, linhas entre eles",
              "MC-01")
    y = cabecalho_y - 28

    y = campos_iguais(c, y, [
        ("TEMA / PERGUNTA", 3), ("DATA", 1.2)], altura=16)

    # área de colagem
    fonte(c, 6.5, True, CINZA)
    c.drawString(MARGEM, y, "COLE OS CONCEITOS COM POST-IT OU ESCREVA NOS ESPAÇOS")
    y -= 6
    alt = y - MARGEM - 40
    caixa(c, MARGEM, y - alt, LARGURA_UTIL, alt, CINZA_CLARO, 0.6)
    # círculo central sugerido
    c.setStrokeColor(AZUL)
    c.setLineWidth(1.0)
    c.circle(MARGEM + LARGURA_UTIL / 2, y - alt / 2, 38, stroke=1, fill=0)
    fonte(c, 6, False, CINZA)
    c.drawCentredString(MARGEM + LARGURA_UTIL / 2, y - alt / 2 - 3, "TEMA")
    y = y - alt - 16

    fonte(c, 8.5, True, AZUL)
    c.drawString(MARGEM, y, "CONEXÕES QUE EU NÃO VI ANTES (as linhas estranhas valem mais que as óbvias)")
    y -= 8
    y = regua(c, y, n=4)

    rodape(c, "IAM · folhas de estudo — mapa conceptual")


def m_leitura_ativa(c):
    """LEITURA ATIVA — o marcador de margem, 2 por página."""
    cabecalho_y = cabecalho(c, "LEITURA ATIVA", "marcador de margem — leia e marque",
              "LA-01")
    y = cabecalho_y - 28

    y = campos_iguais(c, y, [
        ("LIVRO", 3), ("CAP.", 1), ("PÁG.", 1)], altura=15)

    fonte(c, 7.5, True, AZUL)
    c.drawString(MARGEM, y, "O QUE REPAREI (uma anotação por linha)")
    y -= 6
    for i in range(10):
        caixa(c, MARGEM, y - 9, 6, 6)
        linha(c, MARGEM + 11, y - 5, LARGURA_UTIL - 11)
        y -= 17
    y -= 8

    fonte(c, 7.5, True, VERDE)
    c.drawString(MARGEM, y, "PERGUNTAS QUE O TRECHO LEVOU")
    y -= 6
    for i in range(4):
        linha(c, MARGEM, y, LARGURA_UTIL)
        y -= 16

    rodape(c, "IAM · folhas de estudo — leitura ativa")


def m_checklist_20(c):
    """CHECKLIST DE REVISÃO — a folha de auditoria do próprio método."""
    cabecalho_y = cabecalho(c, "CHECKLIST DE REVISÃO", "auditoria do meu método de estudo — marque com honestidade",
              "CK-01")
    y = cabecalho_y - 28

    itens = [
        ("Li o texto INTEIRO antes de resumir", "sumário não substitui leitura"),
        ("Escrevi o resumo com o livro FECHADO", "teste real de compreensão"),
        ("Anotei a IDEIA central em uma frase", "não em três parágrafos"),
        ("Guardei só o que é verdadeiro e útil", "descartar é parte do método"),
        ("Registrei onde vou usar o que aprendi", "conhecimento sem uso evapora"),
        ("Criei o item de memorização na hora", "depois eu não crio"),
        ("Revisei no dia seguinte", "o espaçamento é o que fixa"),
        ("Registrei o que NÃO entendi", "a dúvida é o mapa do próximo passo"),
        ("Refiz o resumo de cabeça", "memória de leitura não é saber"),
        ("Conectei com outro assunto que conheço", "isolado, o saber evapora"),
        ("Aplicuei em algo concreto (aula/p sermon)", "sem aplicação, é cultura"),
        ("Não consultei o autor ANTES de ler", "Etapa 0 antes da Etapa 1"),
    ]

    fonte(c, 8.5, True, AZUL)
    c.drawString(MARGEM, y, "A) HÁBITOS DE LEITURA")
    y -= 12
    for i, (t, d) in enumerate(itens):
        col = 0 if i < 6 else 1
        row = i if i < 6 else i - 6
        x = MARGEM + col * (LARGURA_UTIL / 2 + 4)
        w = LARGURA_UTIL / 2 - 12
        yy = y - row * 30
        caixa(c, x, yy - 9, 8, 8)
        fonte(c, 7.5, True)
        c.drawString(x + 13, yy - 2, t)
        fonte(c, 6, False, CINZA)
        c.drawString(x + 13, yy - 11, d)
    y = y - 6 * 30 - 8

    fonte(c, 8.5, True, AZUL)
    c.drawString(MARGEM, y, "B) AVALIAÇÃO")
    y -= 12
    for i in range(5):
        linha(c, MARGEM, y, LARGURA_UTIL)
        y -= 16

    rodape(c, "IAM · folhas de estudo — checklist de revisão")


def m_plano_leitura(c):
    """PLANO DE LEITURA — a folha de rota."""
    cabecalho_y = cabecalho(c, "PLANO DE LEITURA", "a rota: o que vou ler, em que ordem, até quando",
              "PL-01")
    y = cabecalho_y - 28

    y = campos_iguais(c, y, [
        ("PERÍODO", 2), ("META (livros)", 1.2), ("DATA INÍCIO", 1.2)], altura=16)

    fonte(c, 8.5, True, AZUL)
    c.drawString(MARGEM, y, "1 · ORDEM DE LEITURA (a ordem importa mais que a quantidade)")
    y -= 8
    # cabeçalho
    cols = [(0.00, 0.06, "#"), (0.06, 0.34, "TÍTULO"), (0.40, 0.22, "AUTOR"),
            (0.62, 0.14, "PÁGS"), (0.76, 0.12, "INÍCIO"), (0.88, 0.12, "FIM")]
    for frac, larg, rot in cols:
        x = MARGEM + LARGURA_UTIL * frac
        fonte(c, 6, True, AZUL)
        c.drawString(x + 2, y - 6, rot)
    y -= 12
    for i in range(12):
        linha(c, MARGEM, y, LARGURA_UTIL, CINZA_CLARO, 0.4)
        y -= 18

    y -= 12
    fonte(c, 8.5, True, AZUL)
    c.drawString(MARGEM, y, "2 · POR QUE ESTA ORDEM (o critério, não a lista)")
    y -= 8
    y = regua(c, y, n=3)
    y -= 14

    fonte(c, 8.5, True, VERDE)
    c.drawString(MARGEM, y, "3 · O QUE FAZER SE EU PARAR (o plano de retomada)")
    y -= 8
    y = regua(c, y, n=2)

    rodape(c, "IAM · folhas de estudo — plano de leitura")


def m_habitos(c):
    """HÁBITOS E ROTINA — a folha de espaçamento e rotina."""
    cabecalho_y = cabecalho(c, "HÁBITOS E ROTINA", "o que eu repito, e em que ritmo",
              "HB-01")
    y = cabecalho_y - 28

    fonte(c, 8.5, True, AZUL)
    c.drawString(MARGEM, y, "1 · HÁBITOS DE ESTUDO (o que já funciona — não mexer)")
    y -= 8
    for i in range(4):
        linha(c, MARGEM, y, LARGURA_UTIL * 0.55)
        linha(c, MARGEM + LARGURA_UTIL * 0.6, y, LARGURA_UTIL * 0.4)
        y -= 15
    y -= 10

    fonte(c, 8.5, True, AZUL)
    c.drawString(MARGEM, y, "2 · RITMO DIÁRIO (quando, quanto, com que)")
    y -= 8
    for i in range(6):
        caixa(c, MARGEM, y - 9, 7, 7)
        linha(c, MARGEM + 12, y - 5, LARGURA_UTIL * 0.45)
        linha(c, MARGEM + LARGURA_UTIL * 0.55, y, LARGURA_UTIL * 0.45)
        y -= 16
    y -= 8

    fonte(c, 8.5, True, AZUL)
    c.drawString(MARGEM, y, "3 · REVISÃO ESPAÇADA — grade de 8 semanas")
    y -= 8
    semanas = ["S1", "S2", "S3", "S4", "S5", "S6", "S7", "S8"]
    w = (LARGURA_UTIL - 7 * 3) / 8
    x = MARGEM
    for s in semanas:
        fonte(c, 6, True, CINZA)
        c.drawCentredString(x + w / 2, y + 4, s)
        caixa(c, x, y - 13, w, 13)
        x += w + 3
    y -= 24

    fonte(c, 8.5, True, VERMELHO)
    c.drawString(MARGEM, y, "4 · O QUE ME FAZ PARAR (o obstáculo real)")
    y -= 8
    y = regua(c, y, n=3)
    y -= 12

    fonte(c, 8.5, True, VERDE)
    c.drawString(MARGEM, y, "5 · A PROMESSA (o que eu me comprometo a fazer)")
    y -= 8
    y = regua(c, y, n=2)

    rodape(c, "IAM · folhas de estudo — hábitos e rotina")


def m_oito_pastas(c):
    """8 PASTAS — o método de fichamento em 8 caixas (o "index card")."""
    cabecalho_y = cabecalho(c, "FICHA 8 PASTAS (sistema Cornell + index cards)", "o método que estrutura qualquer fichamento",
              "8P-01")
    y = cabecalho_y - 28

    y = campos_iguais(c, y, [
        ("TEMA DA FICHA", 3), ("DATA", 1.2)], altura=16)

    # as 8 categorias do método Cornell
    cats = [
        ("1 · NOTAS DE AULA", "o que foi dito (palavras do autor)"),
        ("2 · RESUMO", "o que isso significa em 1-2 linhas"),
        ("3 · CITAÇÕES", "trechos que valem ser copiados"),
        ("4 · PROBLEMAS", "dúvidas, objeções, pontos em aberto"),
        ("5 · IDÉIAS PRINCIPAIS", "o que o autor quer que eu leve"),
        ("6 · CONEXÕES", "com o que eu já sei (outras obras, outras áreas)"),
        ("7 · APLICAÇÕES", "onde isso entra em uso real"),
        ("8 · AÇÕES", "o que eu faço a partir daqui (tarefa, data)"),
    ]
    h = 62
    for rot, sub in cats:
        caixa(c, MARGEM, y - h, LARGURA_UTIL, h, CINZA_CLARO, 0.5)
        fonte(c, 7, True, AZUL)
        c.drawString(MARGEM + 4, y - 10, rot)
        fonte(c, 5.5, False, CINZA)
        c.drawString(MARGEM + 4, y - 19, sub)
        y -= h + 4

    rodape(c, "IAM · folhas de estudo — ficha 8 pastas")


# ================================================================ catálogo
MODELOS = {
    "ficha-livro": (m_ficha_livro, "Ficha de livro (fichamento de uma obra)"),
    "ficha-livro-verso": (m_ficha_livro_reverso, "Verso da ficha de livro"),
    "preparacao-aula": (m_preparacao_aula, "Preparação de aula (do texto ao sermão)"),
    "resumo": (m_resumo, "Resumo de uma página + teste de retenção"),
    "memorizacao": (m_memorizacao, "Memorização + revisão espaçada"),
    "exegese": (m_exegese, "Exegese — folha de trabalho da Etapa 0"),
    "ficha-autor": (m_arquivo_autor, "Ficha de autor/obra (índice do acervo)"),
    "diario-estudo": (m_diario_estudo, "Diário de estudo (registro diário)"),
    "mapa-conceptual": (m_mapa_mental, "Mapa conceptual (folha de colagem)"),
    "leitura-ativa": (m_leitura_ativa, "Marcador de leitura ativa"),
    "checklist": (m_checklist_20, "Checklist de revisão do método"),
    "plano-leitura": (m_plano_leitura, "Plano de leitura (rota)"),
    "habitos": (m_habitos, "Hábitos e rotina de estudo"),
    "ficha-8-pastas": (m_oito_pastas, "Ficha 8 pastas (Cornell / index cards)"),
}


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--saida", help="caminho do PDF de saída")
    ap.add_argument("--so", help="gerar só um modelo (slug)")
    ap.add_argument("--listar", action="store_true", help="listar modelos e sair")
    ap.add_argument("--folhas-por-pagina", type=int, default=1,
                    help="2 = duas folhas por página (folha de bolso)")
    a = ap.parse_args()

    if a.listar or not a.saida:
        print("Modelos disponíveis:")
        for slug, (_, desc) in MODELOS.items():
            print(f"  {slug:22s} {desc}")
        if not a.saida:
            return 0

    sel = [a.so] if a.so else list(MODELOS)
    if a.so and a.so not in MODELOS:
        sys.stderr.write(f"ERRO: modelo desconhecido '{a.so}'\n")
        return 2

    os.makedirs(os.path.dirname(os.path.abspath(a.saida)), exist_ok=True)
    c = canvas.Canvas(a.saida, pagesize=A4)
    c.setTitle("IAM — Folhas de Estudo A4")
    c.setAuthor("IAM — Study-Agent")

    for slug in sel:
        fn, _ = MODELOS[slug]
        fn(c)
        if a.folhas_por_pagina == 2:
            fn(c)  # segunda folha no verso da mesma página
        c.showPage()

    c.save()
    print(f"OK: {a.saida}  ({len(sel)} modelo(s), {a.folhas_por_pagina} folha(s)/página)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
