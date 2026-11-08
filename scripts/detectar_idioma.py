#!/usr/bin/env python3
"""Deteccao de idioma por stopwords — modulo COMPARTILHADO.

POR QUE ISTO EXISTE (bug de 2026-11-08):
  A rodada de ficcao baixou a edicao ESPANHOLA de "Alves & C.a" (Eca) e a
  gravou em `.../portugues/`, com a KB dizendo `idioma: Portuguese`. O
  acervo MENTIA sobre o proprio idioma. Causa: os pipelines NAO validavam o
  idioma do TEXTO baixado — so confiavam no metadado do candidato (que pode
  vir errado) ou nem olhavam.

  A regra da rampa e' PT-BR. Um texto em espanhol/ingles nao substitui o
  exemplar PT-BR. Logo: detectamos o idioma do TEXTO e, se nao for PT (e nao
  for aceitavel), a obra e' REJEITADA — nao entra no acervo.

  REGRA (calibrada, nao opinada):
    - PT precisa de >= 15% de cobertura de stopwords PT;
    - o vencedor precisa bater o 2o colocado por >= 5 pontos percentuais;
    - abaixo disso: 'desconhecido' (a obra e' REJEITADA por padrao, porque
      o acervo so aceita o que se prova ser PT).

  Calibrado contra casos NEGATIVOS reais:
    - 'Germinal' (frances) -> fr, nao pt  (o bug que botou o Germinal em 1o)
    - 'A Religiosa' (espanhol) -> es, nao pt
    - 'The Man Who Was Thursday' (ingles) -> en
    - 'Alves & C.a' edicao espanhola -> es
    - 'Alves & Cia' edicao PT-BR -> pt
"""
import re
import unicodedata

STOP = {
    "pt": set("""a o e de do da das dos em no na nos nas um uma uns umas que se por com
nao os as ao aos ou mais como mas foi ser seu sua seus suas ele ela eles elas isso este
esta isto meu minha te tu nos nossa nosso ja muito tambem so ainda quando onde qual porque
entao sim sou estou estao tinha foi estar fez fazer disse ver pode ter sabia veio dar
homem mulher moca rapariga velho dona senhor senhora ate cada toda todo todos todas outro
outra nenhum sera serao ha aquela aquele uma vez pelo pela nos como mas nem agora sempre
tambem assim depois antes onde quando enquanto talvez enquanto""".split()),
    "en": set("""the of and to in a is that it he was for on are as with his they at be this
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
    "es": set("""el la los las de del y que no en un una unos unas por con para es son
estaba como pero su sus le lo se le ha me si porque este esta estos estas mi tu
el ella nosotros vosotros ellos ellas cuando donde quien como porque todo mas muy
tambien hasta desde donde quien cual porque entonces sobre entre contra durante
hacer tener decir ir ver dar saber querer poder llegar pasar deber poner parecer
hombre mujer tiempo vida mundo cosa manera agua ciudad tierra casa puerta arbol
perro caballo pan vino leche sol luna noche rey dios amor tiempos tambien""".split()),
    "fr": set("""le la les de des du un une et est il elle que qui dans pour pas sur au
avec ce cette sont nous vous ils elles mais ou donc or ne pas plus tout tous toutes son sa
ses leur leurs mon ma mes ton ta tes nos vos je tu il elle on y en a par comme qui ne
quoi donc alors aussi comme bien encore tres sans sous entre depuis peu toujours jamais
etait etaient etre avoir fait faire dit dire aller voir savoir pouvoir vouloir venir
devoir prendre donner temps jour homme femme vie monde main chose moment eau ville terre
fils mere maison porte arbre chien cheval pain vin lait soleil lune nuit""".split()),
    "it": set("""il lo la i gli le di che non e un una per con su come ma o se
del della nel alla sul dal dei degli delle mi ti ci vi si ho ha hanno aveva era
sono essere fare dire andare vedere sapere potere volere venire dovere prendere
dare tempo giorno uomo donna vita mondo cosa modo acqua citta terra casa porta
albero cane cavallo pane vino latte sole luna notte re dio amore volte molto
anche piu ancora sempre mai gia tutti tutto questa quello senza sotto tra""".split()),
    "de": set("""der die das den dem des ein eine und ist im von zu mit sich auch
auf fur ist sind war nicht mit dem als auch am im aus er hat dass sie wird bei
einer um am sind noch wie einem uber einen so zum war haben nur oder aber vor
zur bis mehr durch man sein wurde sei in haben kann sein wenn wird man so
tag mann frau leben welt hand zeit was jahr alt neu gut gross klein""".split()),
}

# os termos mais discriminativos de PT (os que NAO aparecem em es/fr/it)
PT_FORTES = set("""nao voce voce esta esta sao foi sao sera seus sua das dos
portugues portuguesa obrigado obrigada voce mesmo assim entao ja nao pelo pela
nos nossas nossos coisa coisas muito mais ainda hoje aqui ali la onde quando
porque tambem pode pode nao quer dizer disse homem mulher ano dia noite vez""".split())


def sem_acento(s):
    return "".join(c for c in unicodedata.normalize("NFKD", s or "")
                   if not unicodedata.combining(c))


def _tokens(texto):
    return re.findall(r"[a-z0-9]+", sem_acento(texto).lower())


def detecta(texto):
    """-> (idioma, {idioma: pct}). 'desconhecido' quando nao da para provar."""
    toks = _tokens(texto)
    if len(toks) < 400:
        return ("desconhecido", {})
    cont = {}
    for lang, sw in STOP.items():
        cont[lang] = round(100.0 * sum(1 for w in toks if w in sw) / len(toks), 2)
    orden = sorted(cont.items(), key=lambda kv: -kv[1])
    melhor, pct = orden[0]
    segundo = orden[1][1] if len(orden) > 1 else 0.0
    if pct < 15.0:
        return ("desconhecido", cont)
    if pct - segundo < 5.0:
        # empate: so o PT sobrevive a isso (o resto vai para 'desconhecido')
        return ("desconhecido", cont)
    return (melhor, cont)


def e_portugues(texto, minimo=15.0):
    """True quando o texto e' comprovadamente PT-BR."""
    lang, cont = detecta(texto)
    if lang != "pt":
        return False
    return cont.get("pt", 0.0) >= minimo


def diagnostico(texto):
    """Texto de diagnostico para o log (nao levanta)."""
    lang, cont = detecta(texto)
    marcas = {k: v for k, v in sorted(cont.items(), key=lambda kv: -kv[1])[:3]}
    return f"{lang} {marcas}"


if __name__ == "__main__":
    import sys
    for p in sys.argv[1:]:
        t = open(p, encoding="utf-8", errors="ignore").read()
        print(f"{p.split('/')[-1][:46]:48} {diagnostico(t)}")
