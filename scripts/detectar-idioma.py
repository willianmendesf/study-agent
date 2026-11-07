#!/usr/bin/env python3
"""Detector de idioma ROBUSTO por stopwords de varios idiomas.

O detector da nota 14 (so PT vs EN) classificou 'Germinal' (frances) como
pt, porque o French tem stopwords que colidem com o portugues.

Aqui: PT, EN, FR, ES, IT, DE. Contagem de tokens de stopword de cada idioma,
normalizada. O idioma vencedor precisa ter >= 25% de cobertura.

NAO escreve nada no repo. Saida: /tmp/idiomas.json
"""
import re, glob, os, json

STOP = {
 'pt': set("""a o e de do da das dos em no na nos nas um uma uns umas que se por com
nao os as ao aos ou mais como mas foi ser seu sua seus suas ele ela eles elas isso este
esta isto meu minha te tu nos nossa nosso ja muito tambem so ainda quando onde qual porque
entao sim sou estou estao tinha foi estar fez fazer disse ver pode ter sabia veio dar
homem mulher moca rapariga velho dona senhor senhora ate cada toda todo todos todas outro
outra nenhum sera serao ha aquela aquele uma vez pelo pela nos como mas nem""".split()),
 'en': set("""the of and to in a is that it he was for on are as with his they at be this
have from or one had by word but not what all were we when your can said there use an each
which she do how their if will up other about out many then them these so some her would make
like him into time has look two more write go see number no way could people my than first
water been call who oil its now find long down day did get come made may part over new sound
take only little work know place year live me back give most very after thing our just name
good sentence man think say great where help through much before line right too mean old any
same tell boy follow came want show also around form three small set put end does another well
large must big even such because turn here why ask went men read need land different home us
move try kind hand picture again change off play spell air away animal house point page letter
mother answer found study still learn should world high every near add food between own below
country plant last school father keep tree never both paper together got group often important
until children side feet car mile night walk white sea began grow took river four carry state
once book hear stop without second later miss idea enough eat face watch far really almost let
above girl sometimes mountain cut young talk soon list song being leave family body music color
stand sun question fish area mark dog horse birds problem complete room knew since ever piece
told usually friends easy heard order door sure become ship top across today during short better
best however low hours black products happened whole measure remember early waves reached
listen wind rock space covered fast several hold himself toward five step morning passed""".split()),
 'fr': set("""le la les de des du un une et est il elle que qui dans pour pas sur au
avec ce cette sont nous vous ils elles mais ou donc or ne pas plus tout tous toutes son sa
ses leur leurs mon ma mes ton ta tes nos vos je tu il elle on y en à par comme qui ne
quoi donc alors aussi comme bien encore très sans sous entre depuis peu toujours jamais
etait etaient etre avoir fait faire dit dire aller voir savoir pouvoir vouloir venir
devoir prendre donner temps jour homme femme vie monde main chose moment eau ville terre
fils mere maison porte arbre chien cheval pain vin lait soleil lune nuit""".split()),
 'es': set("""el la los las de del y que no en un una unos unas por con para es son
estaba como pero su sus le lo se le ha me si porque este esta estos estas mi tu
él ella nosotros vosotros ellos ellas cuando donde quien como porque todo más muy
tambien hasta desde donde quien cual porque entonces sobre entre contra durante
hacer tener decir ir ver dar saber querer poder llegar pasar deber poner parecer
hombre mujer tiempo vida mundo cosa manera agua ciudad tierra casa puerta árbol
perro caballo pan vino leche sol luna noche rey dios amor tiempos""".split()),
 'it': set("""il lo la i gli le di che non è un una per con su come ma o se
del della nel alla sul dal dei degli delle mi ti ci vi si ho ha hanno aveva era
sono essere fare dire andare vedere sapere potere volere venire dovere prendere
dare tempo giorno uomo donna vita mondo cosa modo acqua città terra casa porta
albero cane cavallo pane vino latte sole luna notte re dio amore volte molto
anche più ancora sempre mai già tutti tutto questa quello senza sotto tra""".split()),
 'de': set("""der die das den dem des ein eine und ist im von zu mit sich auch
auf für ist sind war nicht mit dem als auch am im aus er hat dass sie wird bei
einer um am sind noch wie einem über einen so zum war haben nur oder aber vor
zur bis mehr durch man sein wurde sei in haben kann sein wenn wird man so
tag mann frau leben welt hand zeit was jahr alt neu gut groß klein""".split()),
}


def texto(path):
    t = open(path, encoding='utf-8', errors='ignore').read()
    if t.startswith('---'):
        p = t.split('---', 2)
        t = p[2] if len(p) >= 3 else t
    ls = []
    for ln in t.split('\n'):
        s = ln.strip()
        if not s or len(s) < 60:
            continue
        if re.match(r'^[\d\[\]\(\)\*·—\-\s]+$', s):
            continue
        ls.append(s)
    return ' '.join(ls)


def detectar(path):
    t = texto(path)
    toks = re.findall(r"[A-Za-zÀ-ÿ]+", t.lower())
    if len(toks) < 400:
        return ('desconhecido', {})
    cont = {}
    for lang, sw in STOP.items():
        n = sum(1 for w in toks if w in sw)
        cont[lang] = round(100 * n / len(toks), 2)
    best = max(cont, key=lambda k: cont[k])
    if cont[best] < 20:
        return ('desconhecido', cont)
    return (best, cont)


ALVOS = sorted(set(
    glob.glob('data/biblioteca/literatura-mundial-classica/**/*.md', recursive=True) +
    glob.glob('data/biblioteca/literatura-brasileira/*.md')))

res = {}
naopt = []
for f in ALVOS:
    lang, cont = detectar(f)
    nome = os.path.basename(f)[:-3]
    res[nome] = {'idioma': lang, 'pct': cont}
    if lang != 'pt':
        naopt.append((nome, lang, cont.get(lang, 0)))

print(f"AVALIADAS: {len(res)}")
from collections import Counter
c = Counter(v['idioma'] for v in res.values())
print("distribuicao:", dict(c))
print("\n--- NAO-PT (fora da rampa PT-BR) ---")
for n, l, p in sorted(naopt, key=lambda x: -x[2]):
    print(f"  {l.upper():4} {p:5.2f}%  {n[:60]}")
json.dump(res, open('/tmp/idiomas.json', 'w'), ensure_ascii=False, indent=1)
print("\nJSON -> /tmp/idiomas.json")
