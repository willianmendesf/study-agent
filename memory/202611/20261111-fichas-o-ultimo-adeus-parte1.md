# 2026-11-11 (tarde) — Fichas de leitura de "O Último Adeus": parte 1 (contos 1–2)

## O que foi pedido

O pedido original (turno anterior, mesma sessão) do William:
**"Faça a ficha de todos eles, já que estou lendo o livro, assim eu consigo ler
o que eu for ler no livro, por enquanto estou seguindo a ordem do livro mesmo.
Fica mais fácil de ler, do que ficar pulando para o início, meio ou fim do
livro. Pode fazer a ficha de leitura, como eu faço fichamento do que já li?"**

→ 7 fichas de leitura, **na ordem do livro**, no padrão do fichamento dele
(FL-01 frente/verso + 8P-01 as 8 pastas), com a quebra § 1–3 (antes da
leitura) / § 4+ (depois).

## O spawn falhou — e o que se fez

O `spawn` dos 7 subagentes (um por conto) morreu com
`LLM call failed after retries: context deadline exceeded` (MiniMax-M2.5,
timeout de contexto). **Os insumos já estavam prontos** quando o spawn morreu:

- `/tmp/fichas/conto-N.txt` (7 recortes do acervo, linhas exatas)
- `/tmp/briefs/N.md` (7 briefings com nomes próprios e hapax MEDIDOS)
- `/tmp/fichas/meta.json` (palavras, rampa, hapax por conto)
- `/tmp/template-ficha-conto.md` (modelo canônico de 13 seções)

→ **Decisão:** refazer as fichas **nesta conversa**, sem subagente. Menos
contexto, mais controle, e o `write_file` tem menos risco de corromper
texto longo. Custo: ~1 turno por 2 fichas.

## O que foi entregue (parte 1 de 3)

| Ficha | Arquivo | Memo |
|---|---|---|
| Conto 1 — "Vila Glicínia" | `data/estudos/notas/ficcao-rampa-leitura/17-ficha-conto-vila-glicinia.md` | `memos/gxoUuEBPyFwcCALLHVqnoHV` |
| Conto 2 — "O Círculo Vermelho" | `data/estudos/notas/ficcao-rampa-leitura/18-ficha-conto-circulo-vermelho.md` | `memos/ENBXqyz3HCMhDyjakb9kkj` |

Cada uma com: 13 seções do modelo, frontmatter Regra 3, 8 pontos de
observação **antes** da leitura, vocabulário com **contagem real**, 5
perguntas com gabarito, e 14–20 citações **todas** com
`buscar.py --verificar` = CONFIRMADA + número de linha do acervo.

Commits: `8fd37a3` (data) + push. Lint: **0 erro novo**.

## 🐛 BUG REINCIDENTE — `write_file` corrompe texto (terceira vez em 48h)

O `write_file` **injetou 13 trechos corrompidos** na ficha 18 e ~13 na 17:

- CJK e outros ideogramas (vários ideogramas CJK corrompidos no mesmo turno)
- cirílico (a, i breve, o)
- **português partido**: `a_signed woman`, `e_rule_of_justice`, `fechoOperation`,
  `de_cases`, `homem_some`, `_exec` seguido de ideograma, dois ideogramas juntos
- e **inglês Leakado**: "closing", "cores", "cartas", "watson", "opening",
  "fecho", "conta", um ideograma, "hipnose"

**Regra (reforçada):** `write_file` em texto longo em PT-BR **corrompe**. Sempre:
1. rodar o detector de não-latino (não só CJK — o caso de hoje tinha cirílico,
   português partido e inglês leakado);
2. rodar o detector de **token misto** (`[A-Za-z]+_[A-Za-z_]+`) e de inglês
   leakado dentro de frases;
3. **ler as linhas corrigidas** (`sed -n 'Np'`) — a substituição por
   `str.replace` às vezes não casa (espaço fino/duplo) e o script "não
   encontra" sem avisar;
4. **evitar o `write_file` para trechos longos** — preferir `exec` com
   heredoc + `python3` para aplicar correções linha a linha.

## Medidas do dia (úteis para as próximas fichas)

- Conto 1: 10.586 palavras, RAMPA 6,75, 472 linhas (104–575), 2.847 tipos
- Conto 2: 6.915 palavras, RAMPA 6,76, 332 linhas (576–907), 2.026 tipos
- Posições na rampa por dificuldade: 1 Detetive Moribundo (6,21) · 2 Carfax
  (6,56) · 3 Bruce-Partington (6,70) · 4 Vila Glicínia (6,75) · 5 Círculo
  Vermelho (6,76) · 6 Seu Último Adeus (7,07) · 7 O Pé do Diabo (7,15).
- O `estado-leitura.yaml` **estava errado** em mim: eu tinha posto
  `conta_pos_rampa: 1` no Círculo Vermelho — o correto é **5** (a ordem da
  rampa é por dificuldade; a ordem do livro é outra). Corrigido antes do
  commit.

## Faltam (3 de 3)

3. "Os Planos do Bruce-Partington" — 908–1456 · 10.107 pal · RAMPA 6,70
4. "O Detetive Moribundo" — 1457–1752 · 5.223 pal · RAMPA 6,21 (já existe a
   **nota 16** = briefing; falta a ficha no padrão FL-01/8P-01)
5. "O Desaparecimento de Lady Frances Carfax" — 1753–2087 · 7.315 pal · 6,56
6. "O Pé do Diabo" — 2088–2434 · 9.297 pal · 7,15
7. "Seu Último Adeus" — 2435–2733 · 5.669 pal · 7,07

**Regra de ouro já aplicada nas fichas 17 e 18:** § 1–3 **antes** da leitura
(não estraga o conto) · § 4+ **depois** (gabarito) · § 11 e § 12 com campos
✍️ **em branco** para o William preencher · citações só entram se o
`--verificar` confirmar.
