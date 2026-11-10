# 2026-11-10 — Aula de Português #25 (Portuga) + correção do cron

## Cron das 19:00 BRT (22:00 UTC) — job da aula de Português

**Sintoma:** o cron disparou com mensagem apontando para
`/home/study-agent/data/estudos/notas/portugues-aulas-diarias/enviar-aula.sh`
— **path que NÃO EXISTE nesta LXC** (o repo real é `/home/willian/study-agent`).
O script "rodou" só porque eu translatei o path na mão; o job, sozinho, quebraria.

**Causa raiz:** o job foi criado na instalação antiga (`/home/study-agent`) e
**nunca foi corrigido** na migração para `/home/willian/study-agent` (2026-11-05).
Mesma classe do bug do `commit-data-diario.sh` (já registrado em MEMORY.md:
*"nunca hardcodar /home/... em script de repo"*). A，这次 **o path estava na
mensagem do cron**, não num script.

**Correção aplicada (2026-11-10 22:03 BRT):**
1. Backup: `cron/jobs.json.bak-20261110-220301`.
2. `picoclaw cron add` com o path certo → novo id `32f8b231fc55fc05`.
3. `picoclaw cron remove ff78ebb31148637c` (o antigo).
4. Verificado no `picoclaw cron list`: schedule `0 22 * * *`, enabled,
   next run 2026-11-11 22:00.

**Lição:** `picoclaw cron` **não tem comando de edição** — só `add`, `remove`,
`enable`, `disable`. Para mudar a mensagem de um job: `add` (novo) → `remove`
(antigo). Sempre com backup do `cron/jobs.json` antes.

**Verificação a fazer em todo cron:** o path citado na mensagem existe?
`ls` antes de rodar. Job de 19:00 já tinha falhado silenciosamente antes.

## Aula #25 entregue

- **Roteiro:** `data/estudos/notas/portugues-aulas-diarias/aula-25-adjetivo-o-que-e-e-concorda-como.md`
- **Título:** Adjetivo: o que é e como ele concorda · Trimestre T2
- **Fonte:** Bechara (cap. 14) + Moreno (vol. 2, cap. 11)
- **Áudio:** `data/perfil/portuga/audios/aula-25.mp3` · 1.638.793 bytes · **276,7 s (4:36)** · Francisca (edge-tts pt-BR)
- **Memo:** `memos/R89k9YjwGw4zLEWYdfT5gX`
- **Catálogo:** linha 25 passou de `roteiro_pronto` → `enviado`
- **Próxima pendente:** #26 (Adjetivo: simples, composto, primitivo, derivado)

**Fluxo que funcionou (medido):**
- `enviar-aula.sh` descobre a próxima por `status: roteiro_pronto` no `_catalogo.md`
  (menor número, não ordem do arquivo).
- TTS via `data/perfil/scripts/tts-run.sh --texto-md` → 10 chunks, 276,7 s.
- O script **não envia** ao Telegram — imprime `CAPA_TEXTUAL` + `AUDIO_FILE`
  e o agente chama `message()` + `send_file()` no mesmo turno (sem mensagem
  no meio, senão o Telegram agrupa tudo num bloco só de áudio).
- **Duração real:** ~4 min (TTS 276 s + Memos + catálogo). O "~1 min" do
  enunciado do cron é otimista — o `exec` do picoclaw corta em 300 s, então
  o script **precisa** rodar em `nohup ... &` e ser consultado por log.

**Regra:** cron que dispara script longo → sempre `nohup ... > log 2>&1 &`
e depois `tail` do log. Rodar em foreground estoura o timeout de 300 s
(o TTS sozinho leva 276 s).

## Commits

- `6be927c` (data) — aula 25 + catálogo + índice do cache TTS
- `2adcdbc` (repo) — `cron/jobs.json` com o path corrigido

Lint: **0 erro novo**, 4 conhecidos no baseline, 1 aviso (tags sem KB).
