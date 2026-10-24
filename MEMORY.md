### edge-tts 403 TrustedClientToken — bloqueio persistente (2026-10-16 19:01 BRT)
- **Sintoma:** `WSServerHandshakeError: 403` em `wss://speech.platform.bing.com/...` com TrustedClientToken rotativo.
- **Tentativas:** 3 retry seguidos no `tts-synth.py` (portuga→Francisca) — todas falharam idênticas.
- **Causa provável:** Microsoft rotacionou o `TrustedClientToken`/`Sec-MS-GEC` que o pacote edge-tts local usa hardcoded — versão 1-143.0.3650.75 do GEC não bate mais com o que o Bing aceita agora.
- **Workaround aplicado:** usar Speaches (Piper faber pt-BR, LXC 140) com override `--modelo speaches-ai/piper-pt_BR-faber-medium --voz faber`. Áudio gerado em 218s (~3:38), qualidade boa.
- **Lição:** quando o edge-tts quebrar, fallback masculino (faber) > pf_dora (Kokoro, qualidade "robótica/horrível" conforme tts-regras.md § 8).
- **Pendência durável:** monitorar atualizações do pacote edge-tts (`pip3 show edge-tts`); quando sair versão com TrustedClientToken novo, retomar Francisca. William prefere voz feminina pra Portuga.
- **Onde:** `data/perfil/memorias/tts-regras.md` (criar § 15 sobre fallback).
### Pipeline z-library → biblioteca (2026-10-24)
- **A skill `zlibrary` (skills/zlibrary/) NÃO funciona nesta instalação** — anti-bot DiamWall
  (HTTP 307 vazio → "Access Denied"). O que funciona: `data/perfil/bibliotecario/biblioteca-orbit/zlib-local.py`
  (wrapper do MCP `zlib-mcp@0.1.2`, que precisa de `nodejs`+`npm` instalados via apt).
- **Sem `uvx` aqui** → o `book-pipeline` (markitdown) não roda. Usar `epub2md.py`
  (EPUB via ebooklib+bs4, PDF via pdftotext, sempre com `normalizar_md.py`).
- **Bug do YAML no KB:** `yaml.safe_dump` com width default quebra caminhos longos →
  entradas apontam pra arquivo inexistente. Usar `width=4096` + nomes de arquivo SEM espaços.
- **Detalhes completos:** `data/perfil/memorias/zlibrary-pipeline.md`
