# Rodada de ficção — 2026-11-22 07:15-07:40 UTC

## Resultado
- **16 obras baixadas** nesta rodada: 12 pela via primária (z-library) + 4 pela
  2ª via depois do conserto.
- Catálogo: 236 obras · **188 adquiridas** · 48 pendentes (era 184/52).
- Lint: **0 erro novo** (4 conhecidos, 1 aviso `esp:mnemos:tags-sem-kb`).

### Via primária (12)
A Colmeia (Cela) · A Dama das Camélias (Dumas filho) · A Educação Sentimental
(Flaubert) · A Grande Arte (Rubem Fonseca) · A Hora dos Ruminantes (Veiga) ·
A Jangada de Pedra (Saramago) · A Marcha de Radetzky (Roth) · A Morte de Artemio
Cruz (Fuentes) · A Princesa de Clèves (La Fayette) · A Sibila (Agustina) ·
A Sonata a Kreutzer (Tolstói) · A Tempestade (Shakespeare).

### 2ª via depois do fix (4)
O Delfim (Cardoso Pires) · A Vida é Sonho (Calderón) · História da Guerra do
Peloponeso (Tucídides) · Um Herói do Nosso Tempo (Lermontov).

Todos verificados: 0 byte nulo, 0 traceback, frontmatter com autor e subpasta
corretos, KB catalogado.

## 🐛 BUG GRAVE corrigido — `pipeline-biblio.py` nunca passava a CONTA

**Sintoma:** a 2ª via reportou `baixados: 0 · falhas: 49` com **114
DOWNLOAD-FALHOU** no log. Cada obra tentou 3 candidatos e todos falharam.

**Causa raiz:** `baixa_zlib()` chamava
`zlib-api.py download <id> <hash> --dest ...` **sem o argumento `conta`**.
O `zlib-api.py` tem `default="zlib2"` → **todos** os downloads iam para a
`zlib2`. E a `zlib2` era justamente a conta **zerada** (10/10 do dia).

Enquanto isso, `cota_zlib()` **somava as 8 contas** (40 downloads restantes) e
o pipeline acreditava ter cota. O z-library respondia "daily limit reached" e o
código traduzia isso como `"download falhou"` — **parecendo falha da obra**.

É o mesmo padrão de 2026-11-10 (BUG: cota somada sem conta) que foi corrigido
no `pipeline-aquisicao.py` e **nunca replicado no irmão**.

**Fix aplicado:**
1. `cota_zlib()` agora também preenche `COTAS_CONTA` (alias → restantes).
2. `baixa_zlib()` escolhe a conta com **mais saldo** (mesma política do
   `pipeline-aquisicao.py`: `max(candidatas, key=cotas.get)`), desconta o saldo
   local e passa a conta como argumento POSICIONAL ao `zlib-api.py`.

**Prova:** rodada `--max 1 --titulo "O Delfim"` antes → falhou; depois → baixou.

## 🐛 Efeito colateral achado no teste

O `--titulo` monta item mínimo (autor vazio, subpasta vazia) → o `.md` caiu em
`outros/O-Delfim.md` com `autor: ""`. Limpei o artefato (estado, KB, arquivo)
antes da rodada real. **Não usar `--titulo` para teste de download: ele não lê o
catálogo.** Preferir `--max 1` com o catálogo e filtrar pela obra.

## Pendências

1. **BookOrbit (192.168.15.26) FORA DO AR** — `Errno 113 No route to host` em
   todas as 16 subidas. Os 16 ebooks ficam em `data/biblioteca/_incoming/`
   (**37 arquivos, 142 MB**) e o cron `reenvio-orbit-automatico.sh` (15 min)
   sobe sozinho quando voltar.
2. **48 obras pendentes no catálogo** — das quais 27 são falhas de idioma
   (só existe EN; a rampa é PT-BR) e o resto são obras sem candidato aceitável
   no z-library/libgen hoje. **Instrução permanente do William (2026-11-18):
   ampliar o catálogo** quando a rodada saturar.
3. **Cota sobrando:** 29 downloads (zlib 4, zlib3-8 4-5 cada, zlib2 0).

## Arquivos tocados
- `scripts/pipeline-biblio.py` (o fix)
- `data/perfil/bibliotecario/pipeline-estado.json` (38 adquiridos hoje, 16 desta rodada)
- KBs de literatura-mundial-classica
