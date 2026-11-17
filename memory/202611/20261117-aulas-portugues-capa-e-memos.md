## 📚 Aulas de Português — "só os áudios jogados" (corrigido 2026-11-17 04:10 UTC)

**Queixa do William:** "corrige ai as aulas de portuga, porque ta chegando só os audios jogados."

**Diagnóstico medido (3 camadas, todas reais):**

1. **Capa nunca saía (causa raiz, já corrigida em `0e2cd36`, 02:33 UTC de hoje).**
   O job do picoclaw era `agent_turn` (turno de LLM): o agente chamava só
   `send_file()` e respondia "Requested output delivered via tool attachment" →
   William recebia o mp3 sozinho. Sessões cron 13, 14, 15 e 16/11 confirmam
   (`tool_calls = ['send_file']` só). Agora o **script entrega ele mesmo** via
   API HTTP do Telegram (capa → sleep 2 → sendAudio), e o disparo é do
   **crontab do sistema** (`0 22 * * *` = 19:00 BRT), zero turno de LLM.
   Prova: log `data/perfil/portuga/logs/aula-20261117.log` → "✅ capa enviada /
   ✅ áudio enviado".

2. **Memos fora do ar = aula sem texto PARA SEMPRE (bug novo, corrigido hoje).**
   Quando o Memos falha, `enviar-aula.sh` segue (correto) e grava
   `status: enviado` + `memos_id: ""`. Nada volta depois para publicar: o script
   só olha a aula do dia. Resultado medido: **aulas 26, 31 e 32** enviadas no
   Telegram e ausentes do Memos.
   → **`scripts/backlog-memos-aulas-portugues.py`** (novo, idempotente): varre
   `status: enviado` + `memos_id` vazio, publica via `memos-post.sh`, grava o id
   no frontmatter **e** na linha do `_catalogo.md`. Se o Memos estiver fora, sai
   em 0 sem tocar em arquivo. Cron: `10 9,15,21 * * *` (06:10/12:10/18:10 BRT).
   Chamado também no fim de `scripts/rodar-aula-portugues.sh`.

3. **Sem Memos, o texto não existia em lugar nenhum (corrigido hoje).**
   A capa dizia "Texto completo no Memos" só quando havia link; sem link, o
   William ficava com mp3 e nada legível. Agora, **se `MEMO_URL` está vazio**,
   o script envia o roteiro `.md` como `sendDocument` depois do áudio, e a capa
   avisa "o texto completo vai no arquivo .md anexo (o Memos está fora do ar)".
   Com Memos funcionando, não duplica (o link cobre).

**Tags do Memos corrigidas no mesmo turno:** era `study-agent,aulas-portugues`
(tag solta, fora da taxonomia curada de 2026-11-05) → agora
`study-agent,estudo/portugues,tipo/aula,serie/aulas-portugues`.

**Estado do Memos em 2026-11-17 04:05 UTC:** fora do ar por **três** rotas —
IPv6 `2804:7f0:...` timeout, IPv4 `100.103.64.20` timeout, hostname sem
resolver (MagicDNS off). `tailscale ping 100.103.64.20` também dá timeout.
Não é bug do script: o backlog fica esperando.

**Regra durável:** *tarefa programada que depende de serviço externo precisa de
(a) entrega primária que não dependa dele e (b) fila de reprocessamento.*
A capa+áudio saem pelo Telegram (não dependem do Memos); o Memos é a **fila**
do backlog. Sem o item (b), toda falha de rede vira perda permanente e silenciosa.

**Arquivos mexidos:** `data/estudos/notas/portugues-aulas-diarias/enviar-aula.sh`
(bloco 9 sendDocument + capa condicional + tags) ·
`scripts/rodar-aula-portugues.sh` (chama o backlog) ·
`scripts/backlog-memos-aulas-portugues.py` (novo) · crontab do sistema (backup
em `/tmp/crontab-backup-20261117.txt`). Lint: 0 erro novo.
