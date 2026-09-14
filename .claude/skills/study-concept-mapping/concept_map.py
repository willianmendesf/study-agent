"""
concept_map.py — núcleo do study-concept-mapping. Só pyyaml + networkx, sem Neo4j/Gephi.

Carrega um mapa de conceitos (YAML, relações tipadas) e gera:
  1. gerar_mermaid(g)      — diagrama Mermaid (texto puro, renderiza direto via mermaid-diagrams)
  2. detectar_comunidades(g) — clusters reais via networkx (greedy modularity), não Gephi
  3. resumo(g)             — nó mais conectado ("god node"), contagens, comunidades
"""
import networkx as nx
import yaml
from networkx.algorithms.community import greedy_modularity_communities

TIPOS_ARESTA = {
    "prerequisito": "-->",
    "aplicacao": "==>",
    "causa_efeito": "-.->",
    "similaridade": "-.-",
}


class MapaInvalido(Exception):
    pass


def carregar_mapa(caminho_yaml):
    """Lê o YAML e devolve um networkx.MultiDiGraph com aresta tipada (attr 'tipo')."""
    with open(caminho_yaml, "r", encoding="utf-8") as fh:
        dados = yaml.safe_load(fh) or {}

    conceitos = dados.get("conceitos") or {}
    if not conceitos:
        raise MapaInvalido("mapa sem bloco 'conceitos'")

    g = nx.MultiDiGraph()
    g.graph["topico"] = dados.get("topico")
    for nome, attrs in conceitos.items():
        attrs = attrs or {}
        g.add_node(nome, dominio=attrs.get("dominio"), dificuldade=attrs.get("dificuldade"))

    for rel in dados.get("relacionamentos") or []:
        de, para, tipo = rel.get("de"), rel.get("para"), rel.get("tipo")
        if tipo not in TIPOS_ARESTA:
            raise MapaInvalido(
                "relacionamento com tipo desconhecido '%s' (válidos: %s)"
                % (tipo, ", ".join(TIPOS_ARESTA))
            )
        for conceito in (de, para):
            if conceito not in conceitos:
                raise MapaInvalido(
                    "relacionamento cita conceito inexistente '%s'" % conceito
                )
        g.add_edge(de, para, tipo=tipo)

    return g


def _slug(nome):
    return "".join(c if c.isalnum() else "_" for c in nome)


def gerar_mermaid(g):
    """Gera um flowchart Mermaid (texto puro) a partir do grafo — sem dependência extra."""
    linhas = ["flowchart TD"]
    dominios = sorted({d for _, d in g.nodes(data="dominio") if d})
    cores = ["#e8f0fe", "#fde8e8", "#e8fde9", "#fdf3e8", "#f0e8fd", "#e8fdf9"]
    dominio_para_classe = {d: "dom%d" % i for i, d in enumerate(dominios)}

    for nome in g.nodes:
        linhas.append('    %s["%s"]' % (_slug(nome), nome))

    for de, para, tipo in g.edges(data="tipo"):
        seta = TIPOS_ARESTA[tipo]
        rotulo = "|%s|" % tipo if tipo != "prerequisito" else ""
        linhas.append("    %s %s%s %s" % (_slug(de), seta, rotulo, _slug(para)))

    for dominio, classe in dominio_para_classe.items():
        cor = cores[list(dominio_para_classe).index(dominio) % len(cores)]
        linhas.append("    classDef %s fill:%s" % (classe, cor))
    for nome, dominio in g.nodes(data="dominio"):
        if dominio:
            linhas.append("    class %s %s" % (_slug(nome), dominio_para_classe[dominio]))

    return "\n".join(linhas)


def detectar_comunidades(g):
    """Clusters reais via greedy modularity (networkx) sobre o grafo não-dirigido."""
    if g.number_of_edges() == 0:
        return [[n] for n in g.nodes]
    nao_dirigido = nx.Graph()
    nao_dirigido.add_nodes_from(g.nodes)
    nao_dirigido.add_edges_from((u, v) for u, v, _ in g.edges(data="tipo"))
    comunidades = greedy_modularity_communities(nao_dirigido)
    return [sorted(c) for c in comunidades]


def resumo(g):
    grau = dict(g.degree())
    no_mais_conectado = max(grau, key=grau.get) if grau else None
    return {
        "topico": g.graph.get("topico"),
        "conceitos": g.number_of_nodes(),
        "relacionamentos": g.number_of_edges(),
        "no_mais_conectado": no_mais_conectado,
        "grau_no_mais_conectado": grau.get(no_mais_conectado),
        "comunidades": len(detectar_comunidades(g)),
    }
