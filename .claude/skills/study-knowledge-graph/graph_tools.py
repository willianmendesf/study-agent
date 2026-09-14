"""
graph_tools.py — núcleo do study-knowledge-graph. Só pyyaml + networkx, sem Neo4j/Prolog/LLM.

Carrega uma ontologia (YAML) e responde 3 perguntas via grafo dirigido real:
  1. caminho_para(conceito)             — ordem topológica de estudo até o conceito
  2. gaps(conceito, aprendidos)         — pré-requisitos (transitivos) ainda faltando
  3. dificuldade_efetiva(conceito, ...) — dificuldade ajustada por conceitos similares já aprendidos
"""
import networkx as nx
import yaml


class OntologiaInvalida(Exception):
    pass


def carregar_ontologia(caminho_yaml):
    """Lê o YAML e devolve um networkx.DiGraph com aresta prerequisito -> conceito."""
    with open(caminho_yaml, "r", encoding="utf-8") as fh:
        dados = yaml.safe_load(fh) or {}

    conceitos = dados.get("conceitos") or {}
    if not conceitos:
        raise OntologiaInvalida("ontologia sem bloco 'conceitos'")

    g = nx.DiGraph()
    for nome, attrs in conceitos.items():
        attrs = attrs or {}
        g.add_node(
            nome,
            dificuldade=attrs.get("dificuldade"),
            tempo_estudo=attrs.get("tempo_estudo"),
            similar_a=list(attrs.get("similar_a") or []),
        )
    for nome, attrs in conceitos.items():
        for prereq in (attrs or {}).get("prerequisitos") or []:
            if prereq not in conceitos:
                raise OntologiaInvalida(
                    "conceito '%s' cita pré-requisito inexistente '%s'" % (nome, prereq)
                )
            g.add_edge(prereq, nome)

    if not nx.is_directed_acyclic_graph(g):
        ciclo = nx.find_cycle(g)
        raise OntologiaInvalida("ciclo de pré-requisitos detectado: %s" % ciclo)

    g.graph["aprendidos"] = set(dados.get("progresso", {}).get("aprendidos") or [])
    g.graph["materia"] = dados.get("materia")
    return g


def _checar_conceito(g, conceito):
    if conceito not in g:
        raise OntologiaInvalida("conceito '%s' não existe na ontologia" % conceito)


def caminho_para(g, conceito):
    """Todos os ancestrais (transitivos) de `conceito` + ele mesmo, em ordem de estudo (topológica)."""
    _checar_conceito(g, conceito)
    ancestrais = nx.ancestors(g, conceito) | {conceito}
    sub = g.subgraph(ancestrais)
    return list(nx.topological_sort(sub))


def gaps(g, conceito, aprendidos=None):
    """Pré-requisitos transitivos de `conceito` que ainda não estão em `aprendidos`."""
    _checar_conceito(g, conceito)
    aprendidos = set(aprendidos) if aprendidos is not None else g.graph.get("aprendidos", set())
    ancestrais = nx.ancestors(g, conceito)
    faltando = ancestrais - aprendidos
    sub = g.subgraph(faltando | {conceito})
    ordem = [c for c in nx.topological_sort(sub) if c != conceito]
    return ordem


def dificuldade_efetiva(g, conceito, aprendidos=None):
    """Dificuldade base do conceito, reduzida 30% por cada conceito 'similar_a' já aprendido."""
    _checar_conceito(g, conceito)
    aprendidos = set(aprendidos) if aprendidos is not None else g.graph.get("aprendidos", set())
    base = g.nodes[conceito].get("dificuldade")
    if base is None:
        return None
    similares_aprendidos = [s for s in g.nodes[conceito].get("similar_a", []) if s in aprendidos]
    efetiva = base
    for _ in similares_aprendidos:
        efetiva *= 0.7
    return max(1, round(efetiva, 1))


def listar_conceitos(g):
    return [
        {
            "conceito": n,
            "dificuldade": g.nodes[n].get("dificuldade"),
            "tempo_estudo": g.nodes[n].get("tempo_estudo"),
            "prerequisitos": list(g.predecessors(n)),
            "aprendido": n in g.graph.get("aprendidos", set()),
        }
        for n in nx.topological_sort(g)
    ]
