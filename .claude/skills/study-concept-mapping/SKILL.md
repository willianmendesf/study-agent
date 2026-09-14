---
name: study-concept-mapping
description: "Gera mapa conceitual visual real (Mermaid + detecção de clusters via networkx, tudo local) a partir de conceitos e relações tipadas (pré-requisito, causa-efeito, similaridade, aplicação). Use ao descobrir um tópico novo ou organizar material complexo com muitos conceitos interligados."
---

# Concept Mapping — Mapa Conceitual (implementação real)

**Tipo:** skill real (invocada via `CLAUDE.md` Regra 1)
**Escopo:** Study-Agent — apoia `estudo-fluxo-01-descobrir` e `estudo-fluxo-02-organizar`
**Runtime:** 100% local — `concept_map.py`/`concept_map_cli.py` usam só `networkx` + `pyyaml`, sem
banco, sem LLM na geração do diagrama (o LLM entra só para **extrair** os conceitos/relações do material)

---

## O que é (e o que não é)

- **É** um grafo tipado real (`networkx.MultiDiGraph`) construído a partir de um YAML que a IA escreve
  a partir da conversa/biblioteca, com 3 saídas testadas:
  1. **Diagrama Mermaid** (texto puro) — renderiza direto na resposta, mesmo mecanismo de
     `mermaid-diagrams`; cores por domínio, seta por tipo de relação
  2. **Comunidades** — clusters reais de conceitos via `networkx.greedy_modularity_communities`
     (algoritmo de modularidade de verdade, não o "Gephi" que a versão anterior citava sem usar)
  3. **Resumo** — nº de conceitos/relações, nó mais conectado ("god node"), nº de comunidades
- **Não é** Neo4j nem Gephi — a versão anterior desta skill descrevia esse stack e nunca o
  implementou. A versão atual é mais simples (grafo em memória) e **funciona de fato**.
- **Não** duplica `study-knowledge-graph`: aquela skill responde "em que ordem estudar" (só
  pré-requisitos, caminho topológico); esta responde "como o material se conecta visualmente" (várias
  relações tipadas, clusters, visão de conjunto). Podem compartilhar os mesmos conceitos, mas servem
  perguntas diferentes.

---

## Quando ativar

- Usuário está descobrindo um tópico novo com muitos conceitos inter-relacionados e quer "ver o
  panorama" antes de mergulhar.
- Material complexo (`estudo-fluxo-02-organizar`) onde a estrutura de relações não é óbvia — o
  diagrama ajuda a decidir por onde começar e o que é central (nó mais conectado).
- Usuário pede explicitamente um mapa mental/conceitual do tema.

## Quando NÃO ativar

- Poucos conceitos (2-3) sem relação complexa — não vale o esforço, basta explicar em texto.
- Se a pergunta é só "em que ordem estudo isso", use `study-knowledge-graph` (mais direto pra esse caso).

---

## Schema do mapa (YAML)

Um arquivo por matéria/tópico, em `data/concept-maps/<materia>.yaml` (dado do usuário, Regra 7 — nunca
no template). Exemplo completo e testável em `exemplo-mapa.yaml` deste skill:

```yaml
topico: "Sistema Cardiovascular"

conceitos:
  Coracao: { dominio: Anatomia, dificuldade: 5 }
  Sistema Circulatorio: { dominio: Anatomia, dificuldade: 4 }
  Cardiologia: { dominio: Clinica, dificuldade: 8 }

relacionamentos:
  - { de: Sistema Circulatorio, para: Coracao, tipo: prerequisito }
  - { de: Coracao, para: Cardiologia, tipo: aplicacao }
```

`tipo` só aceita: `prerequisito`, `aplicacao`, `causa_efeito`, `similaridade` (cada um vira uma seta
diferente no Mermaid). `de`/`para` precisam existir em `conceitos` — senão `concept_map_cli.py` recusa
com erro claro.

## Como a IA constrói o mapa

Sem editor visual — a IA escreve o YAML diretamente:
1. Levanta os conceitos-chave do tópico (com o usuário, ou lendo a estrutura do material indexado).
2. Para cada par de conceitos relacionados, decide o tipo de relação (pré-requisito? aplicação?
   causa-efeito? só parecido?).
3. Escreve `data/concept-maps/<materia>.yaml`.
4. Gera o Mermaid e mostra direto na resposta ao usuário.

---

## Uso (`concept_map_cli.py`)

```bash
python3 .claude/skills/study-concept-mapping/concept_map_cli.py <mapa.yaml> mermaid
python3 .claude/skills/study-concept-mapping/concept_map_cli.py <mapa.yaml> mermaid --saida mapa.md
python3 .claude/skills/study-concept-mapping/concept_map_cli.py <mapa.yaml> comunidades
python3 .claude/skills/study-concept-mapping/concept_map_cli.py <mapa.yaml> resumo
```

`mermaid` imprime o texto do diagrama (a IA cola isso num bloco ` ```mermaid ` na resposta, que
renderiza direto — sem precisar de navegador/servidor). `--saida` grava já formatado em Markdown.

### Exemplo de saída (testado com `exemplo-mapa.yaml`)

```
$ python3 concept_map_cli.py exemplo-mapa.yaml resumo
{
  "topico": "Sistema Cardiovascular (exemplo)",
  "conceitos": 6,
  "relacionamentos": 5,
  "no_mais_conectado": "Coracao",
  "grau_no_mais_conectado": 4,
  "comunidades": 2
}
```

---

## Integração

- **`estudo-fluxo-01-descobrir`** — mapa geral do tópico + nó raiz destacado, pra orientar por onde
  começar.
- **`estudo-fluxo-02-organizar`** — hierarquia/clusters pra decidir a ordem de indexação do material.
- **`study-knowledge-graph`** — mesmos conceitos podem alimentar as duas skills (uma cuida da ordem de
  estudo, outra da visão de conjunto); não há acoplamento de código entre elas hoje.
- **`mermaid-diagrams`** — o texto gerado é Mermaid puro; a skill de renderização é a mesma.

## Dependências

- `pyyaml`, `networkx` (`pip install -r requirements.txt`) — sem Neo4j, sem Gephi, sem serviço externo.

## Referências

- `concept_map.py` — núcleo (`carregar_mapa`, `gerar_mermaid`, `detectar_comunidades`, `resumo`)
- `concept_map_cli.py` — CLI que expõe o núcleo
- `exemplo-mapa.yaml` — exemplo funcional (fictício, não é dado de usuário) usado nos testes acima
