#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Motor de rodadas continuas de avaliacao vocacional (especialista Dokimia).

POR QUE ISTO EXISTE (pedido do William, 2026-11-05):
    "eu estava fazendo um processo com uma banca avaliadora... como podemos
     retomar e ter esses exercicios, de perguntas avaliacao retomados e continuos?"

O material de TREINO ja existe (data/estudos/notas/vocacao-ministerial/,
9 documentos; 52 perguntas do comite; 22 perguntas de simulacao em rounds; a
matriz de 27 itens da Ficha de Avaliacao). O que faltava era a MAQUINA que
transforma esse material em um ciclo que se repete sozinho:

    1. sorteia um ROUND (a partir do que esta mais fraco na matriz, nao do
       que e divertido)
    2. sorteia as PERGUNTAS desse round (do banco + das variacoes)
    3. sorteia a ORDEM e o PESO (o comite real nao pergunta em ordem logica)
    4. emite o TEMPO de cada pergunta (o comite tem 60-90 minutos)
    5. mede a COERENCIA contra as respostas ja dadas
    6. ao fim, devolve o PARECER e atualiza a MATRIZ

O gabarito NUNCA entra no material de treino: este script emite a PERGUNTA e o
CRITERIO DE RESPOSTA (o que o conselho escuta), nunca a resposta-modelo antes
de o candidato responder. A resposta-modelo so vem no parecer, depois.

ESTADO (JSON, gitignored):
    data/perfil/bibliotecario/dokimia-estado.json

USO:
    python3 scripts/dokimia-motor.py --rodada          # sorteia e imprime a rodada
    python3 scripts/dokimia-motor.py --rodada --json   # mesma coisa, em JSON
    python3 scripts/dokimia-motor.py --status          # estado das rodadas
    python3 scripts/dokimia-motor.py --relatorio       # matriz de cobertura resumida
"""
from __future__ import annotations

import argparse
import json
import random
import re
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
NOTAS = ROOT / "data" / "estudos" / "notas" / "vocacao-ministerial"
MATRIZ = NOTAS / "08-matriz-cobertura-e-qualidade.md"
ESTADO = ROOT / "data" / "perfil" / "bibliotecario" / "dokimia-estado.json"
BANCO = NOTAS / "04-banco-de-perguntas-comite-vocacao.md"
VARIACOES = NOTAS / "09-variacoes-de-questoes.md"

# --------------------------------------------------------------------------
# OS 6 ROUNDS (mesma estrutura da simulacao de 2026-10-26, ja respondidos R1-R3)
# --------------------------------------------------------------------------
ROUNDS = [
    {
        "id": 1,
        "nome": "Abertura",
        "tempo_total_seg": 600,
        "foco": "rapport, coerencia entre discurso e vida",
        "bloco": "I.1 integridade / I.2 espiritualidade",
        "criterio": (
            "O comite escuta se voce e alguem confiavel e se aguenta uma conversa franca. "
            "Resposta generica ('quero servir a Deus') denuncia que voce nao pensou no que vai fazer."
        ),
    },
    {
        "id": 2,
        "nome": "A evidencia",
        "tempo_total_seg": 900,
        "foco": "prova de ministerio: evangelizacao, discipulado, lideranca, estudo",
        "bloco": "III.2 evangelizacao / III.3 discipulado / III.6 lideranca",
        "criterio": (
            "Cada resposta de pratica exige evento verificavel: quando, quem, o que voce fez, "
            "o que mudou. Numero exato > numero grande. 'Nao estou' e resposta valida; "
            "'tenho algumas' e resposta vazia."
        ),
    },
    {
        "id": 3,
        "nome": "O chamado",
        "tempo_total_seg": 900,
        "foco": "vocacao, identidade, cônjuge, seguranca de saldao",
        "bloco": "I.3 vocacao / IV.1-6 cônjuge",
        "criterio": (
            "A regua do IPB: 'Declaracao que nao possa ser comprovada e inidonea'. "
            "Nao ofereca resposta-modelo antes de voce responder. O comite escuta se o "
            "chamado esta ancorado em Deus ou em outra coisa (status, tedio, crise)."
        ),
    },
    {
        "id": 4,
        "nome": "Teologia",
        "tempo_total_seg": 1200,
        "foco": "exame de doutrina sob cadencia rapida",
        "bloco": "I.4 competencia / III.1 comunicacao da Palavra",
        "criterio": (
            "A pergunta que mais reprova: 'quais questoes de reflexao teologica tem exigido seu "
            "estudo e seu pensamento recentemente?'. O comite quer saber o que esta OCUPANDO sua "
            "mente, nao o que voce estudou. Tensao teologica viva, nao resposta de manual."
        ),
    },
    {
        "id": 5,
        "nome": "As perigosas",
        "tempo_total_seg": 900,
        "foco": "as 12 que um elder veterano faz de surpresa",
        "bloco": "I.6 estilo de vida / II.7 disciplina / II.4 coerencia",
        "criterio": (
            "Aqui o comite inclina para frente. Nada de elogio antes. Se voce disser 'nunca me "
            "aconteceu', o conselho sabe que voce nao conta a verdade. O que importa nao e a "
            "fraqueza: e O QUE VOCE FEZ com ela."
        ),
    },
    {
        "id": 6,
        "nome": "O encerramento",
        "tempo_total_seg": 600,
        "foco": "saldo, maturidade, fracasso",
        "bloco": "II.1 amabilidade / III.4 visao de ministerio",
        "criterio": (
            "A pergunta que reprova candidato: 'se o presbiterio disser nao, o que voce faz?'. "
            "A resposta que passa mostra vida, chamado e valor FORA do pulpitio. A que reprova "
            "trata o ministry como identidade total. Voce vai deixar a sala bem?"
        ),
    },
]

# --------------------------------------------------------------------------
# AS PERGUNTAS DO COMITE (do banco 04 + variacoes 09)
# nivel: 1..5 ; tags: tema ; fonte: onde veio
# --------------------------------------------------------------------------
PERGUNTAS = [
    # ---------------- NIVEL 1 — ABERTURA ----------------
    (1, "O que nesta posicao te excita e interessa?", "vocacao", "PCUSA/Denver"),
    (1, "Quais sao suas mais fortes habilidades, experiencias e competencias que vao te tornar eficaz nesta posicao?", "competencia", "PCUSA/Denver"),
    (1, "Quais sao as principais qualidades que voce busca nas suas relacoes com os membros da congregacao e/ou colegas?", "relacionamento", "PCUSA/Denver"),
    (1, "Como voce prefere trabalhar com os outros para atingir seu objetivo?", "relacionamento", "PCUSA/Denver"),
    (1, "Fale de voce: saude, maturidade e juizo pratico, senso de humor, iniciativa.", "integridade", "PCUSA/Denver"),
    (1, "O que te motiva e te mantem firme?", "identidade", "PCUSA/Denver"),
    (1, "Qual e o seu entendimento de fe?", "teologia", "Lehigh"),
    (1, "Onde voce esta na sua peregrinacao de fe?", "identidade", "Lehigh"),
    (1, "Conte sobre sua fe em Jesus Cristo e sua vida religiosa pessoal (ou: como voce cuida da sua alma?).", "espiritualidade", "Lehigh"),
    (1, "Quais praticas espirituais regulares voce segue, e por que essas?", "espiritualidade", "Lehigh"),
    (1, "O que te energiza na sua Confissao de Fe e centraliza sua jornada de fe?", "confissao", "Lehigh"),
    (1, "Voce se deleita com a noiva de Cristo?", "espiritualidade", "Whitney/EPC"),
    (1, "Voce esta sendo cada vez mais governado pela Palavra de Deus?", "espiritualidade", "Whitney/EPC"),
    (1, "Voce esta mais amoroso?", "espiritualidade", "Whitney/EPC"),
    (1, "As disciplinas espirituais estao se tornando cada vez mais importantes para voce?", "disciplina", "Whitney/EPC"),

    # ---------------- NIVEL 2 — TEOLOGIA ----------------
    (2, "Quais questoes de reflexao teologica tem exigido seu estudo e seu pensamento recentemente? Explique duas.", "teologia", "PCUSA/National Capital"),
    (2, "O que significa, na pratica, confiar em Jesus Cristo como seu Salvador, reconhecê-lo Senhor de todos e Cabeca da Igreja, e por Ele crer num so Deus, Pai, Filho e Espirito Santo?", "confissao", "Lehigh"),
    (2, "De que modo, especificamente e de modo geral, a graca de Deus impactou sua vida?", "graca", "Lehigh"),
    (2, "Quais elementos distintivos da fe reformada voce descreveria como essenciais, e como eles impactam sua vida e seu ministerio?", "reforma", "Lehigh"),
    (2, "O que a descricao das Escrituras como pelo Espirito Santo, a testemunha unica e autoritativa de Jesus Cristo e da Palavra de Deus significa para voce?", "escritura", "Lehigh"),
    (2, "Quem e Jesus Cristo para voce?", "cristologia", "Lehigh"),
    (2, "O que e o pecado? Como ele impacta os crentes, individualmente e como comunidade?", "pecado", "Lehigh"),
    (2, "Como voce entende a responsabilidade perante o presbiterio?", "polity", "PCUSA"),
    (2, "Como voce define as doutrinas essenciais da fe reformada?", "reforma", "PCUSA"),
    (2, "Apresente seu entendimento sobre a importancia dos sacramentos na igreja de hoje.", "sacramentos", "PCUSA"),
    (2, "Qual e a missao da igreja no mundo?", "missao", "PCUSA"),
    (2, "Como voce entende os relatos de criacao em Genesis 1-3?", "genesis", "PCUSA"),
    (2, "O que significa afirmar que so Deus e Senhor da consciencia?", "consciencia", "PCUSA"),
    (2, "Quais sao os temas favoritos aos quais voce volta com mais frequencia na sua pregacao?", "pregacao", "PCUSA"),

    # ---------------- NIVEL 3 — VOCACAO, IDENTIDADE, VIDA ----------------
    (3, "Acredita que Deus o chamou para o Ministerio da Palavra?", "vocacao", "Anexo I.16"),
    (3, "Que circunstancias causaram o seu convencimento ao chamado?", "vocacao", "Anexo I.16"),
    (3, "Seu cônjuge esta convencido do seu chamado?", "conjuge", "Anexo I.16"),
    (3, "De que maneira seu cônjuge se envolve no seu ministerio?", "conjuge", "Anexo I.17"),
    (3, "Voce sente a direcao de Deus para um lugar, regiao ou comunidade etnica?", "chamado", "Anexo I.18"),
    (3, "Qual e a evidencia mais clara da bencao de Deus na sua vida?", "graca", "Anexo I.10.A"),
    (3, "Descreva sua pratica de evangelizacao pessoal.", "evangelizacao", "Anexo I.10.B"),
    (3, "Voce ja levou alguem a Cristo? De um exemplo recente.", "evangelizacao", "Anexo I.10.C"),
    (3, "Quantas pessoas voce levou ao Senhor no ultimo ano?", "evangelizacao", "Anexo I.10.D"),
    (3, "Descreva sucintamente sua vida devocional.", "devocional", "Anexo I.11.A"),
    (3, "Descreva sucintamente seus habitos de estudo.", "estudo", "Anexo I.11.B"),
    (3, "A que conferencia de estudos, institutos, seminarios compareceu nos ultimos 5 anos?", "estudo", "Anexo I.11.C"),
    (3, "Descreva sua atuacao e estilo como lider.", "lideranca", "Anexo I.14.A"),
    (3, "Quantas pessoas voce esta disciplinando no momento? Descreva seus metodos.", "discipulado", "Anexo I.14.B"),
    (3, "Que pastor voce admira, cujos dons gostaria de ter?", "identidade", "Anexo I.14.C"),
    (3, "Qual e sua relacao com dinheiro? Quanto voce ganha, quanto gasta, quanto da?", "estilo-de-vida", "Anexo I.10.E"),
    (3, "Qual e a sua sensacao sobre os objetivos e a visao da igreja ou obra para a qual esta sendo chamado?", "visao", "Lehigh"),
    (3, "Como voce equilibra a vida pessoal/familiar com o ministerio?", "familia", "Lehigh"),
    (3, "Como voce recarrega a bateria, revitaliza seu nivel de energia?", "equilibrio", "Lehigh"),
    (3, "Qual e a diferenca entre uma igreja conexional e uma congregacional?", "polity", "Lehigh"),
    (3, "Qual e o seu versiculo favorito e por que?", "escritura", "Lehigh"),
    (3, "Qual foi sua experiencia no ministerio mais frutifera e pessoalmente gratificante? Por que?", "fruto", "Anexo I.23.8"),

    # ---------------- NIVEL 4 — SAUDE ESPIRITUAL ----------------
    (4, "Voce tem uma sede saudavel de Deus?", "espiritualidade", "Whitney/EPC"),
    (4, "Como e a sua relacao com a presenca de Deus no dia a dia?", "espiritualidade", "Whitney/EPC"),
    (4, "Voce tem um vicio ou habito que controla voce?", "vicio", "Whitney/EPC"),
    (4, "Seu dinheiro esta sob seu controle?", "dinheiro", "Whitney/EPC"),
    (4, "Seu casamento esta no estado que voce esperaria encontrar num ano?", "casamento", "Whitney/EPC"),
    (4, "Voce tem uma missao que assume pessoalmente?", "missao", "Whitney/EPC"),

    # ---------------- NIVEL 5 — AS PERIGOSAS ----------------
    (5, "Qual e o seu maior defeito — e o que voce fez com ele?", "integridade", "Tripp"),
    (5, "Conte uma situacao em que voce esteve errado e alguem te confrontou. Como voce respondeu?", "integridade", "Tripp"),
    (5, "Em que area da sua vida voce e mais dependente do que deveria?", "vicio", "Tripp"),
    (5, "Por que voce, e nao outro da sua igreja?", "identidade", "N5"),
    (5, "Se o conselho disser que sua vocacao nao se confirmou, o que voce faz?", "maturidade", "N5"),
    (5, "Voce se considera apto a pregar para pessoas mais velhas, mais educadas e mais experientes que voce?", "pregaçao", "N5"),
    (5, "O que voce faria se, no seminario, descobrisse que nao tem o dom para pregar?", "maturidade", "N5"),
    (5, "Como voce lida com a possibilidade de fracassar publicamente?", "fracasso", "Tripp"),
    (5, "Quem e a pessoa mais proxima de voce que voce NAO ouve? Por que?", "relaçao", "Tripp"),
    (5, "Voce esta se candidatando porque Deus te chamou, ou porque esta insatisfeito com outra coisa?", "motivacao", "N5"),
    (5, "Se o presbiterio dissesse: nao va para o seminario; sirva no mundo secular e seu trabalho na igreja sera maior assim — o que voce faria?", "maturidade", "Bloco 5.7"),
    (5, "Ele ignorou a evidencia clara de problemas. (Voce nega, minimiza ou racionaliza evidencias sobre si?)", "auto-conhecimento", "Tripp"),
    (5, "O pecado cega. Quando alguem te confronta, o que acontece em voce nos primeiros 30 segundos?", "auto-conhecimento", "Tripp"),
    (5, "Faltava devocao em seu ministerio.", "devocao", "Tripp"),
]


def _limpa(s: str) -> str:
    """Normaliza acentos e caracteres de OCR para casar no texto."""
    import unicodedata
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9]+", " ", s.lower()).strip()


# --------------------------------------------------------------------------
# EXTRAÇÃO: perguntas a partir do banco (04) e das variacoes (09)
# --------------------------------------------------------------------------
def extrair_banco():
    """Le o banco 04 e extrai as perguntas com numero de item."""
    if not BANCO.exists():
        return []
    txt = BANCO.read_text(encoding="utf-8")
    out = []
    # padrao:  "N. **"pergunta"** — (fonte)   ou  N. "pergunta" — (fonte)
    for m in re.finditer(r"^\s*(\d+)\.\s+\*\*\"(.+?)\"\*\*(.*)$", txt, flags=re.M):
        num, perg, resto = int(m.group(1)), m.group(2), m.group(3)
        fonte = ""
        fm = re.search(r"\(([^()]*)\)\s*$", resto.strip())
        if fm:
            fonte = fm.group(1)
        out.append((num, perg, fonte))
    return out


def extrair_variacoes():
    """Le o doc 09 e extrai as variacoes por tema."""
    if not VARIACOES.exists():
        return {}
    txt = VARIACOES.read_text(encoding="utf-8")
    temas = {}
    atual = None
    for ln in txt.splitlines():
        h = re.match(r"^##\s+(\d+)\.\s+(.+)$", ln)
        if h:
            atual = h.group(2).strip()
            temas.setdefault(atual, [])
            continue
        b = re.match(r"^-\s+\*\*\[(\w)\]\*\*\s+(.+)$", ln)
        if b and atual:
            temas[atual].append((b.group(1), b.group(2).strip()))
    return temas


# --------------------------------------------------------------------------
# ESTADO
# --------------------------------------------------------------------------
def carregar_estado():
    if ESTADO.exists():
        try:
            return json.loads(ESTADO.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"rodadas": [], "respostas": {}, "criado_em": None}


def salvar_estado(est):
    ESTADO.parent.mkdir(parents=True, exist_ok=True)
    ESTADO.write_text(json.dumps(est, ensure_ascii=False, indent=2), encoding="utf-8")


# --------------------------------------------------------------------------
# LEITURA DA MATRIZ (27 itens da Ficha de Avaliacao)
# --------------------------------------------------------------------------
NOTAS_MAPA = {"🟢": "forte", "🟡": "parcial", "🔴": "ausente", "⚪": "nao-aplica"}


def ler_matriz():
    """Le a matriz 08 e devolve [(id_item, bloco, nota)].

    A coluna da NOTA e a 5a do quadro ('Sua nota'); a 3a e a COBERTURA do banco
    (o quanto o material cobre o item), que nao e a nota do candidato.
    """
    if not MATRIZ.exists():
        return []
    txt = MATRIZ.read_text(encoding="utf-8")
    out = []
    for ln in txt.splitlines():
        if not ln.strip().startswith("|"):
            continue
        col = [c.strip() for c in ln.strip().strip("|").split("|")]
        if len(col) < 5:
            continue
        m = re.match(r"^\*\*([IVX]+\.\d+(?:-\d+)?)\*\*", col[0])
        if not m:
            continue
        item = m.group(1)
        nota = ""
        for c in col[4:6]:          # 'Sua nota' e, as vezes, a coluna seguinte
            for sym, nome in NOTAS_MAPA.items():
                if sym in c:
                    nota = nome
                    break
            if nota:
                break
        if nota:
            out.append((item, col[1][:60], nota))
    return out


def itens_fracos():
    """Itens da matriz que ainda precisam de evidencia (ausente -> parcial)."""
    m = ler_matriz()
    return [x for x in m if x[2] in ("ausente", "parcial")]


def prioridade_rodada():
    """Escolhe o round pelo que esta mais fraco (nao pelo que e divertido)."""
    est = carregar_estado()
    feitos = {r["round"] for r in est.get("rodadas", [])}
    fracos = {x[1].lower() for x in itens_fracos()}

    # mapa item->round (bloco da Ficha -> round que mais o exercita)
    item_para_round = {
        "evangelizacao": 2, "comunica": 4, "estilo de vida": 5,
        "amabilidade": 5, "disciplina": 5, "lideranca": 2,
        "discipulado": 2, "estudo": 2, "competencia": 4,
    }
    voto = {r["id"]: 0 for r in ROUNDS}
    for _item, bloco, nota in itens_fracos():
        for chave, rid in item_para_round.items():
            if chave in bloco.lower():
                voto[rid] += 2 if nota == "ausente" else 1
    # rounds nunca feitos tem prioridade
    for r in ROUNDS:
        if r["id"] not in feitos:
            voto[r["id"]] += 3
    # round 1 (abertura) sempre e a primeira a ser feita
    if 1 not in feitos:
        voto[1] += 10
    melhor = max(voto.items(), key=lambda kv: kv[1])
    return melhor[0], voto


# --------------------------------------------------------------------------
# SORTEIO DA RODADA
# --------------------------------------------------------------------------
def sortear_rodada(seed=None, n_perguntas=None):
    rng = random.Random(seed)
    rid, voto = prioridade_rodada()
    rnd = next(r for r in ROUNDS if r["id"] == rid)

    # perguntas do nivel correspondente + pool adjacente
    nivel_do_round = {1: 1, 2: 4, 3: 3, 4: 2, 5: 5, 6: 5}[rid]
    pool = [p for p in PERGUNTAS if p[0] in (nivel_do_round,) or (rid == 6 and p[0] in (5, 3))]
    if rid == 4:
        pool = [p for p in PERGUNTAS if p[0] in (2, 4)]
    if rid == 6:
        pool = [p for p in PERGUNTAS if p[0] in (5, 3)]

    n = n_perguntas or (6 if rid in (1, 6) else 8)
    escolhidas = rng.sample(pool, min(n, len(pool)))

    # variacoes do tema (doc 09) para quebrar a decoracao
    temas = extrair_variacoes()
    itens = []
    for nivel, perg, tema, fonte in escolhidas:
        var = []
        for nome_tema, lst in temas.items():
            if _limpa(nome_tema) in _limpa(perg) or _limpa(perg) in _limpa(nome_tema):
                var = lst
                break
        itens.append({
            "nivel": nivel,
            "pergunta": perg,
            "tema": tema,
            "fonte": fonte,
            "variacoes": [{"tipo": t, "texto": txt} for t, txt in var[:3]],
        })

    # tempo: o comite distribui o tempo total entre as perguntas
    base = rnd["tempo_total_seg"] // max(len(itens), 1)
    tempos = []
    restante = rnd["tempo_total_seg"]
    for i, it in enumerate(itens):
        t = base if i < len(itens) - 1 else restante
        tempos.append(t)
        restante -= t

    return {
        "round": rid,
        "nome": rnd["nome"],
        "foco": rnd["foco"],
        "bloco_ficha": rnd["bloco"],
        "criterio_do_comite": rnd["criterio"],
        "tempo_total_seg": rnd["tempo_total_seg"],
        "tempo_total_min": round(rnd["tempo_total_seg"] / 60),
        "sorteado_em": datetime.now().isoformat(timespec="minutes"),
        "prioridade_votos": voto,
        "itens": [
            {**it, "tempo_seg": tempos[i], "tempo_min": round(tempos[i] / 60)}
            for i, it in enumerate(itens)
        ],
    }


def registrar_respostas(rodada_id, respostas):
    """Grava as respostas do candidato (para checar coerencia depois)."""
    est = carregar_estado()
    est.setdefault("respostas", {})[str(rodada_id)] = {
        "quando": datetime.now().isoformat(timespec="minutes"),
        "itens": respostas,
    }
    salvar_estado(est)


def checar_coerencia(rodada_id=None):
    """Compara respostas de mesmo tema entre rodadas — a Ficha avalia coerencia (II.4)."""
    est = carregar_estado()
    resp = est.get("respostas", {})
    por_tema = {}
    for rid, bloco in resp.items():
        for item in bloco.get("itens", []):
            tema = str(item.get("tema", "")).lower()
            txt = str(item.get("resposta", "")).lower()
            if not tema or not txt:
                continue
            por_tema.setdefault(tema, []).append((rid, txt))
    conflitos = []
    for tema, occ in por_tema.items():
        if len(occ) < 2:
            continue
        # heuristica: numeros divergentes no mesmo tema = incoerencia provavel
        nums = []
        for rid, txt in occ:
            ns = re.findall(r"\b(\d{1,4})\b", txt)
            if ns:
                nums.append((rid, ns))
        if len(nums) >= 2:
            conjuntos = [set(n for _, n in ns) for _, ns in nums]
            if any(c1 != c2 and (c1 & c2) == set() for c1 in conjuntos):
                conflitos.append({"tema": tema, "rodadas": [r for r, _ in nums],
                                  "numeros": [n for _, n in nums]})
    return conflitos


# --------------------------------------------------------------------------
# RELATORIO
# --------------------------------------------------------------------------
def relatorio():
    est = carregar_estado()
    m = ler_matriz()
    cont = {}
    for _i, _b, nota in m:
        cont[nota] = cont.get(nota, 0) + 1
    return {
        "itens_matriz": len(m),
        "por_nota": cont,
        "rodadas_feitas": [r["round"] for r in est.get("rodadas", [])],
        "respostas_registradas": list(est.get("respostas", {}).keys()),
        "coerencias_em_risco": checar_coerencia(),
        "itens_fracos": [{"item": i, "bloco": b, "nota": n} for i, b, n in itens_fracos()],
    }


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------
def imprimir_rodada(r):
    print(f"ROUND {r['round']} — {r['nome']}")
    print(f"foco: {r['foco']}")
    print(f"bloco da Ficha: {r['bloco_ficha']}")
    print(f"tempo: {r['tempo_total_min']} min para {len(r['itens'])} perguntas")
    print(f"criterio do comite: {r['criterio_do_comite']}")
    print("=" * 72)
    for i, it in enumerate(r["itens"], 1):
        print(f"\n{i}. [CONSELHO] {it['pergunta']}")
        print(f"   tema: {it['tema']} | fonte: {it['fonte']} | tempo: ~{it['tempo_min']} min")
        if it.get("variacoes"):
            print("   variações que o comite pode usar:")
            for v in it["variacoes"]:
                print(f"     [{v['tipo']}] {v['texto']}")
    print("\n" + "=" * 72)
    print("Responda em voz alta, como se fosse março. Sem consultar os arquivos.")
    print("O gabarito nao aparece aqui — ele so vem no parecer, depois.")


def main():
    ap = argparse.ArgumentParser(description="Motor de rodadas continuas (Dokimia)")
    ap.add_argument("--rodada", action="store_true", help="sorteia e imprime a rodada")
    ap.add_argument("--json", action="store_true", help="saida em JSON")
    ap.add_argument("--status", action="store_true", help="estado das rodadas")
    ap.add_argument("--relatorio", action="store_true", help="matriz de cobertura resumida")
    ap.add_argument("--seed", type=int, default=None)
    ap.add_argument("--n", type=int, default=None, help="numero de perguntas")
    ap.add_argument("--registrar", help="arquivo JSON com as respostas para registrar")
    args = ap.parse_args()

    if args.status:
        est = carregar_estado()
        print(json.dumps({"rodadas": est.get("rodadas", []),
                          "respostas": list(est.get("respostas", {}).keys())},
                         ensure_ascii=False, indent=2))
        return
    if args.relatorio:
        print(json.dumps(relatorio(), ensure_ascii=False, indent=2))
        return
    if args.registrar:
        dados = json.loads(Path(args.registrar).read_text(encoding="utf-8"))
        registrar_respostas(dados.get("round"), dados.get("respostas", []))
        print(f"registrado: round {dados.get('round')} ({len(dados.get('respostas', []))} respostas)")
        return

    r = sortear_rodada(seed=args.seed, n_perguntas=args.n)
    if args.json:
        print(json.dumps(r, ensure_ascii=False, indent=2))
    else:
        imprimir_rodada(r)


if __name__ == "__main__":
    main()
