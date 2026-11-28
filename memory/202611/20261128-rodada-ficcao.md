---
data: 2026-11-28
tipo: nota-tecnica
serie: rodada-ficcao
---

# Rodada de ficção — 2026-11-28

## Resultado

- **40 obras novas** entraram no acervo (todas em PT-BR, todas verificadas).
- Catálogo: **253 → 293 obras** (43 alvos novos acrescentados na fonte
  `scripts/gerar-catalogo-ficcao.py`, cada um com exemplar PT-BR confirmado
  por busca no eAPI — busca não gasta cota).
- Catálogo fechou o dia **293/293 adquirido, 0 pendente**.
- Cota z-library: 8 contas, 62 → ~50 downloads disponíveis.
- **BookOrbit fora do ar o dia inteiro** (`Errno 113 No route to host`, 15:26
  BRT e 04:49 BRT testados). Os EPUBs ficaram em `data/biblioteca/_incoming/`
  e sobem sozinhos pelo `reenvio-orbit-automatico.sh` (cron `*/15 8-23,0-2`).

## As 40 obras

### Brasileira (6)
Água Viva (Clarice) · A Maçã no Escuro (Clarice) · Caetés (Graciliano) ·
O Cemitério dos Vivos (Lima Barreto) · Iaiá Garcia (Machado) · A Carne (Júlio Ribeiro)

### Portuguesa (4)
O Crime do Padre Amaro · A Cidade e as Serras · A Ilustre Casa de Ramires
(todos Eça) · Eurico, o Presbítero (Herculano)

### Russa (3)
O Adolescente (Dostoiévski) · Memórias do Subsolo (Dostoiévski) ·
A Morte de Ivan Ilitch (Tolstói)

### Francesa (3)
Thérèse Raquin (Zola) · O Pai Goriot (Balzac) · Eugénie Grandet (Balzac)

### Anglo-saxã / moderna (24)
Robinson Crusoé · Mansfield Park · Razão e Sensibilidade · Villette ·
Tempos Difíceis · Silas Marner · O Moinho à Beira do Floss · Adam Bede ·
Daniel Deronda · Ao Farol · As Ondas · Ulisses · Por Quem os Sinos Dobram ·
Adeus às Armas · As Aventuras de Augie March · Lolita ·
O Apanhador no Campo de Centeio · Drácula · O Médico e o Monstro ·
A Ilha do Tesouro · O Homem Invisível · A Guerra dos Mundos ·
O Fantasma de Canterville · O Príncipe Feliz e outros contos (Wilde)

## Dois livros com conteúdo ERRADO — corrigidos na causa

1. **"Contos de Fadas" (Oscar Wilde)** — o EPUB que o z-library serve com esse
   título (`id 5729665`/família) é **"Os melhores Contos de Fadas Celtas"**
   (Editora Wish, 2020, vários autores, curadoria de Marina Avila). Medido:
   a palavra "Wilde" aparece **7×** em 5.079 linhas, "celtas" **57×**, e
   "Príncipe Feliz" **0×**. Não é o Wilde.
   **Substituído** pela edição bilíngue real — *O Príncipe Feliz e outros
   contos* (Landmark, 2012), que traz os 15 contos em PT + EN. `bookId` quando
   o Orbit voltar.

2. **"A Casa Assombrada" (Charles Dickens)** — o único EPUB PT com esse título
   (`id 21436397`, "Estrada dos Livros") é a antologia **inglesa**
   *The Haunted House* (Red Wheel/Weiser 2012), coletânea de vários autores
   sobre casas mal-assombradas. Não é a obra do Dickens em português.
   **Saiu do acervo e do catálogo** — Dickens não tem essa obra em PT-BR no
   z-library (medido: 10 resultados, todos de outros autores com o mesmo
   título — John Boyne, Grady Hendrix, James Cudney).

**Regra derivada:** o título no resultado da busca não é prova de identidade.
Antes de fechar o livro, conferir **autor no corpo** (o nome do autor tem de
aparecer) e **título no corpo**. Ambos os casos passariam no gate atual
(≥2.500 palavras, idioma pt, sem traceback) — o gate mede integridade, não
identidade.

## Pendente

- **BookOrbit**: 54 EPUBs em `_incoming/` (os 40 de hoje + 15 do Edersheim de
  03:50 que também não subiram). Sobe só quando o app voltar (janela
  05:00–23:00 BRT).
- **Livro bilíngue do Wilde**: se o William preferir só a parte PT, a metade
  inglesa está da linha ~499.574 em diante (89.168 das 173.896 palavras).
- **Cron do dia**: a rodada de 00:17 UTC rodou com o catálogo já 253/253 e
  reportou "0 baixados" sem ampliar — a ampliação só aconteceu no turno manual
  das 07:15. O `rodada-ficcao.sh` não tem passo de ampliação automática;
  enquanto o catálogo fechar sem alvos novos, toda rodada sai com 0.
