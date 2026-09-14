# Bibliotecário (study-gerenciar-bibliotecas)

**Utility skill** — cuida do pool único de biblioteca (`data/biblioteca/`) do início ao fim: converte
e cataloga material novo, tagueia, localiza/recomenda livros por tema, detecta lacunas (lista de
aquisição). **Nunca cria especialista** — isso é papel do Orquestrador (`study-setup-orquestrador`); o
Bibliotecário só informa quais tags existem quando consultado. Ver `SKILL.md` para o fluxo completo —
este arquivo é só um resumo de leitura rápida.

## Modelo (Regra 8 do CLAUDE.md)

- **Uma origem só de livros:** `data/biblioteca/`. Sem catálogo, sem IDs, sem registro em `config.yaml`.
- Cada arquivo declara `tags: [...]`; cada especialista declara `tags_do_dominio: [...]`. O cruzamento
  entre as duas é o que define o que cada especialista enxerga — sem edição manual de nada.

## O que o Bibliotecário faz

| Pedido do usuário | Ação |
|---|---|
| "adiciona esse PDF na biblioteca" | Converte (Regra 2), tagueia, salva em `data/biblioteca/` |
| "temos livro sobre X?" | Busca no pool, responde com caminho + trecho relevante, nunca inventa |
| "o que ler sobre X?" | Recomenda por relevância, com ordem de leitura sugerida |
| "o que falta na biblioteca?" | Lista lacunas e propõe itens pra `data/biblioteca/lista-aquisicao.md` |
| "cria um especialista de Y" | **Não é aqui** — encaminhe pro Orquestrador (`study-setup-orquestrador`); o Bibliotecário só responde quando consultado sobre quais tags existem |
| Pergunta de **conteúdo** (não sobre livros) | Redireciona pro especialista do domínio — o Bibliotecário não responde sobre teologia/medicina/etc., só sobre os livros em si |

## O que NÃO faz

- **Não cria especialista** — nunca escreve `data/perfil/especialistas/*.yaml`, nunca decide nome/domínio/tipo. Isso é sempre com o usuário e o Orquestrador.
- Não mantém catálogo, ID ou whitelist de biblioteca por especialista.
- Não assume nenhum provedor de aquisição automática (ex.: um MCP de biblioteca digital) — se o usuário
  tiver um configurado, o Bibliotecário pode usar, mas isso é sempre opcional e configurado pelo próprio
  usuário em `data/perfil/`, nunca hardcoded no template.

## Referências

- `SKILL.md` — fluxo completo
- `BIBLIOTECARIO.md` — o papel do Bibliotecário em detalhe (o que é, o que nunca faz, limites)
- `../../CLAUDE.md` Regra 8 — modelo de pool único, tipos de especialista, relacionamentos
- `config.yaml → especialistas` — schema do arquivo de especialista
