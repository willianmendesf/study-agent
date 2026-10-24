### edge-tts 403 TrustedClientToken — bloqueio persistente (2026-10-16 19:01 BRT)
- **Sintoma:** `WSServerHandshakeError: 403` em `wss://speech.platform.bing.com/...` com TrustedClientToken rotativo.
- **Tentativas:** 3 retry seguidos no `tts-synth.py` (portuga→Francisca) — todas falharam idênticas.
- **Causa provável:** Microsoft rotacionou o `TrustedClientToken`/`Sec-MS-GEC` que o pacote edge-tts local usa hardcoded — versão 1-143.0.3650.75 do GEC não bate mais com o que o Bing aceita agora.
- **Workaround aplicado:** usar Speaches (Piper faber pt-BR, LXC 140) com override `--modelo speaches-ai/piper-pt_BR-faber-medium --voz faber`. Áudio gerado em 218s (~3:38), qualidade boa.
- **Lição:** quando o edge-tts quebrar, fallback masculino (faber) > pf_dora (Kokoro, qualidade "robótica/horrível" conforme tts-regras.md § 8).
- **Pendência durável:** monitorar atualizações do pacote edge-tts (`pip3 show edge-tts`); quando sair versão com TrustedClientToken novo, retomar Francisca. William prefere voz feminina pra Portuga.
- **Onde:** `data/perfil/memorias/tts-regras.md` (criar § 15 sobre fallback).