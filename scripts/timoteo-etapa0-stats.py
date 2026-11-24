#!/usr/bin/env python3
"""Etapa 0 - 1 e 2 Timoteo: extracao medida do texto + lexico do Dicionario Strong.

Regra: NENHUM autor/comentario consultado. Somente:
  - o texto (TR com morfologia + ARC)
  - o Dicionario Biblico Strong (numeros e definicoes)
  - contagens do proprio corpus
"""
import json
import re
from collections import defaultdict, Counter

P = "data/biblioteca/biblias/grc/trparsed.txt"
PT = "data/biblioteca/biblias/pt/almeida_ra.txt"
DIC = "data/biblioteca/referencias-biblicas/Dicionario-Biblico-Strong.md"

lines = open(P, encoding="utf-8").read().split("\n")
ptlines = open(PT, encoding="utf-8").read().split("\n")
diclines = open(DIC, encoding="utf-8").read().split("\n")


def parse(start, end, book):
    verses = []
    ch = None
    cur = None
    for i in range(start - 1, end):
        l = lines[i].strip()
        if l.startswith("Chapter "):
            if cur:
                verses.append(cur)
                cur = None
            ch = int(l.split()[1])
            continue
        if not l or ch is None:
            continue
        m = re.match(r"^(\d+)\s+(.*)$", l)
        if m:
            if cur:
                verses.append(cur)
            cur = [book, ch, int(m.group(1)), m.group(2)]
        elif cur is not None:
            cur[3] += " " + l
    if cur:
        verses.append(cur)
    return verses


def ptvers(a, b):
    out = []
    ch = None
    cur = None
    for i in range(a - 1, b):
        l = ptlines[i].strip()
        if l.startswith("Capítulo"):
            if cur:
                out.append(cur)
                cur = None
            ch = int(l.split()[1])
            continue
        if not l or ch is None:
            continue
        m = re.match(r"^(\d+)\s+(.*)$", l)
        if m:
            if cur:
                out.append(cur)
            cur = [ch, int(m.group(1)), m.group(2)]
        elif cur is not None:
            cur[2] += " " + l
    if cur:
        out.append(cur)
    return out


V1 = parse(39832, 40441, "1Tm")
V2 = parse(40442, 40908, "2Tm")
ALL = V1 + V2
PT1 = ptvers(66124, 66363)
PT2 = ptvers(66364, 66539)
PTALL = PT1 + PT2

TOK = re.compile(r"([α-ωἀ-῿]+)\s+(?:G\d+\s+)*(V-[A-Z0-9]+-[A-Z0-9]*\d[SP])")


def clean(t):
    return re.sub(r"\s+", " ", re.sub(r"\sG\d+", "", t))


def nwords(vs, idx):
    return sum(len(re.findall(r"\S+", v[idx])) for v in vs)


R = {}

R["versiculos"] = {
    "1Tm_por_cap": dict(sorted(Counter(v[1] for v in V1).items())),
    "2Tm_por_cap": dict(sorted(Counter(v[1] for v in V2).items())),
    "1Tm": len(V1),
    "2Tm": len(V2),
    "total": len(ALL),
    "PT_1Tm_por_cap": dict(sorted(Counter(v[0] for v in PT1).items())),
    "PT_2Tm_por_cap": dict(sorted(Counter(v[0] for v in PT2).items())),
    "PT_total": len(PTALL),
    "palavras_grego_1Tm": nwords(V1, 3),
    "palavras_grego_2Tm": nwords(V2, 3),
    "palavras_grego_total": nwords(ALL, 3),
    "palavras_pt_1Tm": nwords(PT1, 2),
    "palavras_pt_2Tm": nwords(PT2, 2),
    "palavras_pt_total": nwords(PTALL, 2),
}

rows = defaultdict(list)
codes = Counter()
for b, c, v, t in ALL:
    for m in TOK.finditer(t):
        code = m.group(2)
        if code.split("-")[1].endswith("M"):
            codes[code] += 1
            rows[(b, c)].append([v, m.group(1), code])
R["imperativos"] = {
    "total": sum(codes.values()),
    "1Tm": sum(len(x) for k, x in rows.items() if k[0] == "1Tm"),
    "2Tm": sum(len(x) for k, x in rows.items() if k[0] == "2Tm"),
    "por_codigo": dict(codes),
    "2p_singular": sum(n for c_, n in codes.items() if c_.endswith("2S")),
    "versiculos_com_imperativo": len(set((b, c, v) for (b, c), it in rows.items() for v, _, _ in it)),
    "1Tm_versiculos": len(set((c, v) for (b, c), it in rows.items() if b == "1Tm" for v, _, _ in it)),
    "2Tm_versiculos": len(set((c, v) for (b, c), it in rows.items() if b == "2Tm" for v, _, _ in it)),
    "por_capitulo": {"%s %d" % k: [":".join(map(str, x[:2])) for x in v] for k, v in sorted(rows.items())},
}

verbforms = Counter()
for b, c, v, t in ALL:
    for m in TOK.finditer(t):
        verbforms[m.group(1)] += 1
R["verbais"] = {"tokens": sum(verbforms.values()), "formas_distintas": len(verbforms)}

g2v = defaultdict(set)
g2f = defaultdict(set)
g2tok = defaultdict(int)
form2g = {}
for b, c, v, t in ALL:
    for m in re.finditer(r"([Ͱ-Ͽἀ-῿]+)\s+(G\d+)", t):
        form2g.setdefault(m.group(1), m.group(2))
        g2v[m.group(2)].add("%s %d:%d" % (b, c, v))
        g2f[m.group(2)].add(m.group(1))
        g2tok[m.group(2)] += 1


def sk(s):
    p = s.split()
    return (p[0], int(p[1].split(":")[0]), int(p[1].split(":")[1]))


dic = {}
cur = None
DICPAT = re.compile(r"^\s*(\d{1,5})\s+((?:[Ͱ-Ͽἀ-῿][Ͱ-Ͽἀ-῿\-]*\s*)+)([A-Za-z][A-Za-z0-9\-]*(?:\s+[A-Za-z][A-Za-z0-9\-]*)*)\s*$")
for i in range(65163, len(diclines)):
    l = diclines[i]
    m = DICPAT.match(l)
    if m:
        num = int(m.group(1))
        if num not in dic:
            dic[num] = {"linha": i + 1, "grep": m.group(2).strip(), "translit": m.group(3), "def": []}
        cur = num
    elif cur is not None:
        dic[cur]["def"].append(l)


def dicdef(num, maxlines=16):
    d = dic.get(num)
    if not d:
        return None
    body = []
    for l in d["def"]:
        if l.strip():
            body.append(l.strip())
        if len(body) >= maxlines:
            break
    return "\n".join(body)


LEX = [
    ("G3852", "παραγγελία", "instrucao/ordem transmitida"),
    ("G3853", "παραγγέλλω", "manda"),
    ("G3056", "λόγος", "palavra"),
    ("G4102", "πίστις", "fe"),
    ("G26", "ἀγάπη", "amor"),
    ("G2150", "εὐσέβεια", "piedade"),
    ("G1108", "γνῶσις", "conhecimento"),
    ("G1922", "ἐπίγνωσις", "conhecimento preciso"),
    ("G225", "ἀλήθεια", "verdade"),
    ("G3454", "μῦθος", "fabula/discurso"),
    ("G1076", "γενεαλογία", "genealogia"),
    ("G1985", "ἐπίσκοπος", "bispo/supervisor"),
    ("G1984", "ἐπισκοπή", "supervisao"),
    ("G1249", "διάκονος", "diacono"),
    ("G1247", "διακονέω", "exercitar o diaconato"),
    ("G1248", "διακονέω", "servir (ministerio)"),
    ("G3623", "οἰκονόμος", "administrador"),
    ("G3624", "οἶκος", "casa"),
    ("G3908", "παρατίθημι", "confiar/depositar"),
    ("G3872", "παρακατάθηκη", "deposito"),
    ("G3866", "παράθηκη", "deposito"),
    ("G652", "ἀπόστολος", "apostolo"),
    ("G4151", "πνεῦμα", "Espirito"),
    ("G3860", "παραδίδωμι", "entregar"),
    ("G2657", "κατανοέω", "perceber"),
    ("G3811", "παιδεύω", "instruir/disciplinar"),
    ("G3809", "παιδεία", "instrucao"),
    ("G2315", "θεόπνευστος", "inspirado por Deus"),
    ("G3306", "μένω", "permanecer"),
    ("G665", "ἀποτρέπουμαι", "afasta-te"),
    ("G5279", "ὑπομιμνήσκω", "lembra-te"),
    ("G1961", "ἐπιμένω", "perseverar"),
    ("G3191", "μελέτω", "aplica-te"),
    ("G1907", "ἐπέχω", "tem cuidado"),
    ("G1128", "γυμνάζω", "exercita-te"),
    ("G4754", "στρατεύομαι", "peleja"),
    ("G5442", "φυλάσσω", "guardar"),
    ("G3870", "παρακαλέω", "exortar"),
    ("G2553", "κακοπαθέω", "sofrer"),
    ("G5343", "φεύγω", "fugir"),
    ("G1377", "διώκω", "perseguir"),
    ("G1321", "διδάσκω", "ensinar"),
    ("G4704", "σπουδάζω", "apressar-se"),
    ("G3868", "παραιτοῦμαι", "afastar-se"),
    ("G831", "αὐθεντέω", "ter dominio"),
    ("G5292", "ὑποταγή", "submissao"),
    ("G3466", "μυστήριον", "misterio"),
    ("G1835", "ἑξήκοντα", "sessenta"),
    ("G435", "ἀνήρ", "homem/marido"),
    ("G1135", "γυνή", "mulher/esposa"),
    ("G1651", "ἐλέγχω", "repreender"),
    ("G3058", "λογομαχέω", "disputar sobre palavras"),
    ("G4153", "πιστός", "fiel"),
    ("G515", "ἄξιος", "digno"),
    ("G1732", "ἀποδοχή", "aceitacao"),
    ("G2316", "θεός", "Deus"),
    ("G2962", "κύριος", "Senhor"),
    ("G5547", "Χριστός", "Cristo"),
    ("G2424", "Ἰησοῦς", "Jesus"),
    ("G1228", "διάβολος", "diabo"),
    ("G4567", "Σατανᾶς", "Satanas"),
    ("G2310", "θεμέλιον", "fundamento"),
    ("G4632", "σκεῦος", "vaso"),
    ("G841", "αὐτάρκεια", "contentamento"),
    ("G5365", "φιλαργυρία", "amor ao dinheiro"),
    ("G4200", "πορισμός", "ganancia"),
    ("G2757", "κενοφωνία", "discussao vazia"),
    ("G5581", "ψευδώνυμος", "chamado falsamente"),
    ("G597", "ἀποθησαυρίζω", "tesourar"),
    ("G4731", "στερεός", "firme"),
    ("G5023", "ταῦτα", "estas coisas"),
    ("G1722", "ἐν", "em"),
    ("G2596", "κατά", "segundo"),
    ("G1519", "εἰς", "para"),
    ("G3361", "μή", "nao"),
    ("G3756", "οὐκ", "nao"),
]
lex = {}
for g, gr, label in LEX:
    L = sorted(g2v.get(g, []), key=sk)
    lex[g] = {
        "grego": gr,
        "label": label,
        "n_versiculos": len(L),
        "n_ocorrencias": g2tok.get(g, 0),
        "formas": sorted(g2f.get(g, [])),
        "versiculos": L,
        "strong_def": dicdef(int(g[1:])),
    }
R["lexico"] = lex

jc = [(b, c, v) for b, c, v, t in ALL if re.search(r"ιησου|χριστ", t.lower())]
kk = [(b, c, v) for b, c, v, t in ALL if re.search(r"κυρι", t.lower())]
sj, skk = set(jc), set(kk)
R["nomes_divinos"] = {
    "jesus_christo_versiculos": len(jc),
    "jesus_christo_pct": round(100.0 * len(jc) / len(ALL), 1),
    "kurios_versiculos": len(kk),
    "kurios_pct": round(100.0 * len(kk) / len(ALL), 1),
    "nenhum_dos_dois": len(ALL) - len(sj | skk),
    "nenhum_pct": round(100.0 * (len(ALL) - len(sj | skk)) / len(ALL), 1),
    "so_jesus_christo": len(sj - skk),
    "so_kurios": len(skk - sj),
    "ambos": len(sj & skk),
    "versiculos_jc": ["%s %d:%d" % x for x in jc],
    "versiculos_kurios": ["%s %d:%d" % x for x in kk],
}

NAMES = [
    ("παυλος", "Paulo"), ("τιμοθεον", "Timoteo"), ("τιμοθεω", "Timoteo"),
    ("ονησιφορου", "Onesiforo"), ("φυγελλος", "Figelo"), ("ερμογενης", "Hermogenes"),
    ("υμεναιος", "Himenéu"), ("φιλητος", "Fileto"), ("αλεξανδρος", "Alexandre"),
    ("δημας", "Demas"), ("λουκας", "Lucas"), ("μαρκον", "Marcos"), ("τυχικον", "Tíquico"),
    ("τροφιμον", "Trofimo"), ("εραστος", "Erasto"), ("ευβουλος", "Eubulo"),
    ("κλαυδια", "Cláudia"), ("πρισκαν", "Priscila"), ("ακυλαν", "Áquila"),
    ("τιτος", "Tito"), ("κηρυξ", "pregador"), ("διδασκαλος", "mestre"),
    ("σωτηρ", "Salvador"), ("επισκοπον", "bispo"), ("ικονιω", "Icônio"),
    ("μωυσει", "Moisés"), ("ιαννης", "Janes"), ("ιαμβρης", "Jambres"),
    ("πιλατου", "Pilatos"), ("καισαρι", "César"), ("λεοντος", "leão"),
]
PLACE = [
    ("εφεσω", "Efeso"), ("μακεδονιαν", "Macedonia"), ("θεσσαλονικην", "Thessalonica"),
    ("γαλατιαν", "Galacia"), ("δαλματιαν", "Dalmacia"), ("αντιοχεια", "Antioquia"),
    ("λυστροις", "Listra"), ("κορινθω", "Corinto"), ("μιλητω", "Mileto"),
    ("τρωαδι", "Troas"), ("λαοδικειας", "Laodiceia"), ("ασια", "Asia"),
    ("ρωμη", "Roma"),
]
nomes = {}
for f, label in NAMES + PLACE:
    g = form2g.get(f)
    L = sorted(g2v.get(g, []), key=sk) if g else []
    nomes[label] = {"forma": f, "strong": g, "n": len(L), "versiculos": L}
R["nomes"] = nomes

R["marcas"] = {
    "pistos_o_logos": ["%s %d:%d" % (b, c, v) for b, c, v, t in ALL
                       if "πιστος" in t.lower() and "λογος" in t.lower()],
    "theopneustos": ["%s %d:%d" % (b, c, v) for b, c, v, t in ALL if "θεοπνευστ" in t.lower()],
    "amem": ["%s %d:%d" % (b, c, v) for b, c, v, t in ALL if re.search(r"αμην", t.lower())],
    "proibicoes_VPNM": ["%s %d:%d" % (b, c, v) for b, c, v, t in ALL if re.search(r"V-PNM", t)],
    "diabolos": ["%s %d:%d" % (b, c, v) for b, c, v, t in ALL if "διαβολ" in t.lower()],
    "satanas": ["%s %d:%d" % (b, c, v) for b, c, v, t in ALL if "σαταν" in t.lower()],
    "numerais": ["%s %d:%d %s" % (b, c, v, re.findall(r"[α-ω]*τρι[α-ω]*", t.lower()))
                 for b, c, v, t in ALL if re.findall(r"[α-ω]*τρι[α-ω]*", t.lower())],
}

met = {}
for pat, label in [(r"στρατιωτ", "soldado"), (r"αθλη", "atleta"), (r"γεωργ", "lavrador"),
                   (r"σκευ", "vaso"), (r"θεμελι", "fundamento"), (r"αγων", "luta"),
                   (r"στρατε", "pelejar"), (r"οικι", "casa"), (r"παγιδ", "laco")]:
    met[label] = ["%s %d:%d" % (b, c, v) for b, c, v, t in ALL if re.search(pat, t.lower())]
R["metaforas"] = met

KEY = [("1Tm", 1, 1), ("1Tm", 1, 3), ("1Tm", 1, 5), ("1Tm", 1, 15), ("1Tm", 1, 18),
       ("1Tm", 2, 2), ("1Tm", 2, 5), ("1Tm", 2, 6), ("1Tm", 2, 11), ("1Tm", 2, 12),
       ("1Tm", 2, 13), ("1Tm", 3, 1), ("1Tm", 3, 2), ("1Tm", 3, 8), ("1Tm", 3, 11),
       ("1Tm", 3, 15), ("1Tm", 3, 16), ("1Tm", 4, 1), ("1Tm", 4, 3), ("1Tm", 4, 4),
       ("1Tm", 4, 13), ("1Tm", 4, 16), ("1Tm", 5, 9), ("1Tm", 5, 19), ("1Tm", 5, 20),
       ("1Tm", 5, 21), ("1Tm", 5, 23), ("1Tm", 6, 4), ("1Tm", 6, 6), ("1Tm", 6, 10),
       ("1Tm", 6, 11), ("1Tm", 6, 12), ("1Tm", 6, 17), ("1Tm", 6, 19), ("1Tm", 6, 20),
       ("2Tm", 1, 6), ("2Tm", 1, 7), ("2Tm", 1, 12), ("2Tm", 1, 14), ("2Tm", 1, 15),
       ("2Tm", 1, 16), ("2Tm", 2, 2), ("2Tm", 2, 3), ("2Tm", 2, 15), ("2Tm", 2, 16),
       ("2Tm", 2, 19), ("2Tm", 2, 20), ("2Tm", 2, 21), ("2Tm", 2, 22), ("2Tm", 2, 24),
       ("2Tm", 2, 25), ("2Tm", 3, 1), ("2Tm", 3, 2), ("2Tm", 3, 3), ("2Tm", 3, 5),
       ("2Tm", 3, 8), ("2Tm", 3, 11), ("2Tm", 3, 12), ("2Tm", 3, 14), ("2Tm", 3, 16),
       ("2Tm", 3, 17), ("2Tm", 4, 1), ("2Tm", 4, 2), ("2Tm", 4, 3), ("2Tm", 4, 6),
       ("2Tm", 4, 7), ("2Tm", 4, 10), ("2Tm", 4, 16), ("2Tm", 4, 17), ("2Tm", 4, 19),
       ("2Tm", 4, 22)]
R["trechos"] = {"%s %d:%d" % (b, c, v): clean(t) for b, c, v, t in ALL if (b, c, v) in KEY}

R["apendice_arc"] = ["%s %d:%d %s" % ("1Tm" if i < len(PT1) else "2Tm", c, v, t) for i, (c, v, t) in enumerate(PTALL)]

json.dump(R, open("/tmp/timoteo-etapa0.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("OK -> /tmp/timoteo-etapa0.json")
print("imperativos total:", R["imperativos"]["total"], "| 1Tm", R["imperativos"]["1Tm"], "| 2Tm", R["imperativos"]["2Tm"])
print("versiculos:", R["versiculos"]["total"])
print("lexico entries com strong_def:", sum(1 for v in lex.values() if v["strong_def"]))
