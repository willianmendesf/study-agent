# 2026-11-23 — Rodada diária de FICÇÃO (escala)

**Comando:** `data/perfil/bibliotecario/rodada-ficcao.sh --max 12`
**Horário:** 07:15–07:26 UTC (04:15 BRT) · log `data/perfil/bibliotecario/logs/rodada-ficcao-2026-11-23.log`

## Resultado: 24 obras

- **Via primária (z-library):** 12 adquiridos · 6 falhas → `=== 12 adquirido(s), 6 falha(s) ===`
- **2ª via (libgen, SEM cota):** **12 adquiridos** · 1 falha → `baixados: 12 · falhas: 1`
- **Total: 24 `.md` novos**, todos catalogados na KB e indexados (0 fora da KB).

### Via primária (12)
A Trégua (Primo Levi, italiano) · Bom Crioulo (Adolfo Caminha) · Casa Velha (Machado) ·
Ciranda de Pedra (Lygia F. Telles) · Conversa na Catedral (Vargas Llosa, mexicano) ·
Feira das Vaidades (Thackeray) · Feliz Ano Novo (Rubem Fonseca) · Inocência (Taunay) ·
Jubiabá (Jorge Amado) · Judas, o Obscuro (Thomas Hardy) · Leite Derramado (Chico Buarque) ·
Mar Morto (Jorge Amado)

### 2ª via — libgen, sem cota (12)
Medeia (Eurípides) · Metamorfoses (Ovídio) · Menino de Engenho (José Lins do Rego) ·
O Amante de Lady Chatterley (D. H. Lawrence) · No Urubuquaquá, no Pinhém (Guimarães Rosa) ·
Nana (Zola) · O Ano da Morte de Ricardo Reis (Saramago) · O Tambor (Günter Grass) ·
O Pêndulo de Foucault (Umberto Eco) · O Evangelho segundo Jesus Cristo (Saramago) ·
O Último Voo do Flamingo (Mia Couto) · Os Noivos (Manzoni)

**Auditoria** dos 24 arquivos: 0 bytes nulos · 0 traceback · 0 fora da KB ·
0 YAML inválido · 16k–318k palavras cada.

## Pendências

1. **BookOrbit (192.168.15.26) sem rota** — `URLError 113` em **todos** os uploads.
   Os ebooks ficaram em `_incoming/` (52 arquivos na fila) para o reenvio automático.
   O cron de 15 min também falha: `[07:15 UTC] Falha no teste de permissao (rc=1).`
   → não é bug nosso; é rede/serviço.
2. **Catálogo: 212/236 adquiridos · 24 em `falhou`.**
   Falhas de hoje (6, todas com cota já paga):
   - `Mensagem` (Pessoa) — texto-curto 19 KB/771 lin (3.748 palavras)
   - `O Barão nas Árvores` (Calvino) — conteudo-divergente (autor não aparece no ebook)
   - `A Pele` (Malaparte) — veio em inglês (gate de idioma correto)
   - `América` (Kafka) — PDF sem camada de texto (precisa OCR)
   - `Budapeste` (Chico Buarque) — texto-curto 254 KB/**147 lin** (40.463 palavras)
   - `Eugênio Oneguin` — nenhum candidato acima do limiar (melhor −0,34)
   As outras 18 são antigas: 12× "3 candidatos tentados, nenhum converteu",
   `Fortunata e Jacinta` (inglês), `O Asno de Ouro`, `Quarup`, `Recordações da Casa
   dos Mortos`, `Se um Viajante numa Noite de Inverno`, `Sonhos de uma Noite de Verão`,
   `Tieta do Agreste`, `Til`, `Ubirajara`, `Um Copo de Cólera`, `Viagens na Minha Terra`,
   `Zero`, `A Morte de Virgílio`, `A Normalista`, `A Regenta`, `As Naus`, `Satiricon`,
   `Tristram Shandy`.
3. **Cota z-library:** 5/10 restantes em cada uma das 8 contas = **40 disponíveis**.
4. **Catálogo:** ampliar candidatos (instrução permanente 2026-11-18).

## 🐛 Achado: o gate de "texto-curto" rejeita obra boa (3 casos medidos)

Medido rodando `epub2md.py` + os gates do próprio pipeline sobre os ebooks rejeitados:

| obra | evidência | por que caiu |
|---|---|---|
| Budapeste | 40.463 palavras, `conteudo_confere=True`, `autor_confere=True` | `MIN_LINHAS=200` — o EPUB tem parágrafos gigantes, só 147 linhas |
| Mensagem | 3.748 palavras, obra completa (poesia) | `MIN_BYTES=60_000` — livro curto por natureza |
| O Barão nas Árvores | 71.138 palavras, título na linha 2398 | `autor_confere` — o ebook não traz "Calvino" em lugar nenhum |

**Custo:** 3 downloads de cota perdidos (obra baixada e descartada).
**Correção proposta (NÃO aplicada, precisa de aprovação):** trocar o gate de
linhas/bytes por gate de **palavras** (ex.: `>= 2.500 palavras` + `conteudo_confere`),
e aceitar "título presente + >20k palavras" quando a ficha não cita autor.
Antes de aplicar, testar contra os corrompidos conhecidos (Dom Quixote com 104
tracebacks, arquivos de bytes nulos).

## Lint

`study-lint.py` → **0 erro novo**, 4 conhecidos, 1 aviso (`esp:mnemos:tags-sem-kb`).
