---
name: study-knowledge-graph
description: "Grafo real de pré-requisitos entre conceitos (networkx local, sem Neo4j/serviço externo). Calcula ordem de estudo, detecta pré-requisitos faltando (gaps) e ajusta dificuldade por conceitos similares já aprendidos. Use ao planejar o caminho de aprendizado entre tópicos relacionados de uma matéria."
---

# Knowledge Graph — Grafo de Pré-Requisitos (implementação real)

**Tipo:** skill real (invocada via `CLAUDE.md` Regra 1)
**Escopo:** Study-Agent — apoia `study-orquestrador` e `study-setup-orquestrador` no planejamento de trilha
**Runtime:** 100% local — `graph_tools.py`/`query.py` usam só `networkx` + `pyyaml`, sem banco, sem
LLM na consulta (o LLM entra só para **escrever** a ontologia a partir da conversa/biblioteca)

---

## O que é (e o que não é)

- **É** um grafo dirigido real (`networkx.DiGraph`), construído a partir de um YAML simples que a IA
  escreve com o usuário, respondendo 3 perguntas com código de verdade (testado):
  1. **Caminho de estudo** até um conceito (ordem topológica dos pré-requisitos transitivos)
  2. **Gaps** — quais pré-requisitos ainda faltam, dado o que o usuário já aprendeu
  3. **Dificuldade efetiva** — reduz a dificuldade base de um conceito quando o usuário já aprendeu
     algo `similar_a` ele (-30% por similar aprendido)
- **Não é** Neo4j, Protégé/OWL, nem um motor de inferência Prolog — versões anteriores desta skill
  descreviam esse "stack" mas nunca chegaram a implementá-lo. A versão atual é deliberadamente mais
  simples (YAML + grafo em memória via `networkx`) e **funciona de fato**.
- **Não** persiste nada em banco — a ontologia inteira é o próprio arquivo YAML.

---

## Quando ativar

- Usuário pede pra planejar o caminho até um tópico com pré-requisitos claros ("quero aprender
  Cardiologia, o que preciso saber antes?").
- `study-setup-orquestrador` ou `estudo-fluxo-01-descobrir` mapeando uma matéria nova e querendo
  registrar a estrutura de dependências entre os conceitos dela.
- Antes de avançar de estágio (`estudo-fluxo-0X`), pra checar se falta pré-requisito.

## Quando NÃO ativar

- Matéria sem estrutura de pré-requisitos clara (ex.: lista solta de tópicos independentes) — não
  força um grafo onde não existe hierarquia real.
- Já existe `study-spaced-repetition-fsrs` cuidando de *quando revisar*; esta skill cuida só de *em
  que ordem aprender* — não confundir os dois papéis.

---

## Schema da ontologia (YAML)

Um arquivo por matéria, em `data/knowledge-graphs/<materia>.yaml` (dado do usuário — nunca no
template, Regra 7). Exemplo completo e testável em `exemplo-ontologia.yaml` deste skill:

```yaml
materia: "Cardiologia"

conceitos:
  Histologia:
    dificuldade: 3          # 1-10, opcional
    tempo_estudo: 180       # minutos, opcional

  Anatomia Cardiaca:
    dificuldade: 5
    tempo_estudo: 300
    prerequisitos: [Histologia, Embriologia]   # arestas: precisa existir como conceito
    similar_a: [Anatomia Pulmonar]             # opcional — usado no ajuste de dificuldade

progresso:
  aprendidos: [Histologia, Embriologia]         # opcional — default pras consultas
```

Regras: `prerequisitos`/`similar_a` só podem citar conceitos que existem no mesmo arquivo (senão
`query.py` recusa com erro claro); ciclos de pré-requisito são detectados e rejeitados (grafo tem que
ser um DAG).

## Como a IA constrói a ontologia

Não existe editor visual — a IA **escreve o YAML diretamente**, junto com o usuário ou a partir do
material já indexado (`study-rag-local`/biblioteca):
1. Levanta os conceitos-chave da matéria (com o usuário, ou lendo a estrutura de capítulos dos livros).
2. Para cada conceito, pergunta/infere pré-requisitos óbvios (o que precisa saber antes).
3. Escreve/atualiza `data/knowledge-graphs/<materia>.yaml`.
4. Ao usuário reportar que estudou algo, adiciona o conceito em `progresso.aprendidos`.

---

## Uso (`query.py`)

```bash
python3 .claude/skills/study-knowledge-graph/query.py <ontologia.yaml> caminho "Cardiologia"
python3 .claude/skills/study-knowledge-graph/query.py <ontologia.yaml> gaps "Cardiologia"
python3 .claude/skills/study-knowledge-graph/query.py <ontologia.yaml> dificuldade "Fisiologia Cardiovascular"
python3 .claude/skills/study-knowledge-graph/query.py <ontologia.yaml> listar
```

`gaps`/`dificuldade` usam `progresso.aprendidos` do YAML por padrão; `--aprendidos "A,B,C"` sobrescreve
pontualmente (útil pra simular "e se eu já soubesse X?"). Saída sempre em JSON — a IA lê e traduz pra
texto natural na resposta ao usuário.

### Exemplo de saída (testado com `exemplo-ontologia.yaml`)

```
$ python3 query.py exemplo-ontologia.yaml caminho "Cardiologia"
["Histologia", "Embriologia", "Bioquimica", "Anatomia Cardiaca",
 "Eletrofisiologia", "Fisiologia Cardiovascular", "Cardiologia"]

$ python3 query.py exemplo-ontologia.yaml gaps "Cardiologia"
["Anatomia Cardiaca", "Eletrofisiologia", "Fisiologia Cardiovascular"]
```

---

## Integração

- **`study-orquestrador`** — consulta `gaps` antes de deixar o usuário avançar para um conceito
  avançado sem os pré-requisitos; oferece o `caminho` como plano de estudo.
- **`study-spaced-repetition-fsrs`** — usa `dificuldade` efetiva como sinal extra pra calibrar o
  intervalo inicial de revisão de um conceito novo.
- **`study-concept-mapping`** — mesma família de dados (conceitos + relações), mas propósito diferente:
  aquela skill gera a visão de conjunto (Mermaid + clusters), esta responde ordem de estudo/gaps. Sem
  acoplamento de código entre as duas hoje — cada uma lê seu próprio YAML.

## Dependências

- `pyyaml`, `networkx` (`pip install -r requirements.txt`) — sem Neo4j, sem serviço externo.

## Referências

- `graph_tools.py` — núcleo (`carregar_ontologia`, `caminho_para`, `gaps`, `dificuldade_efetiva`, `listar_conceitos`)
- `query.py` — CLI que expõe o núcleo
- `exemplo-ontologia.yaml` — exemplo funcional (fictício, não é dado de usuário) usado nos testes acima
