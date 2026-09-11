# SKILL — book-pipeline

## Descrição

Skill que **automatiza todo o pipeline de trazer livros do Google Drive** (ou local) para a base `data/estudos/livros/`. Quando o usuário pedir muitos livros (≥15), ou livros pesados (≥50 MB), ou um drive inteiro, esta skill:

1. **Detecta** a necessidade
2. **Configura** automaticamente o OAuth do Google Drive (se ainda não estiver)
3. **Sobe** o servidor HTTP + supervisor imortal em background
4. **Inicia** o worker "Trazer Todos" (1 por 1, do menor pro maior)
5. **Mostra** ao usuário como acompanhar via navegador

O servidor processa cada livro com pipeline de fallbacks:
- `markitdown` (PDF/EPUB/DOCX)
- `mobi lib` + `html2text` (MOBI)
- `EasyOCR` + `pdftoppm` (PDF escaneado)
- Fallback final: copia o PDF como referência

Tudo persistido em state — sobrevive a crashes, restart do terminal, reinício da sessão.

## Quando ativar

**Trigger 1 — Pedido de muitos livros:**
- Usuário pede ≥15 livros
- Usuário pede um drive/pasta inteiro
- Usuário diz "baixa X" + categoria grande

**Trigger 2 — Livros pesados:**
- ≥1 livro com tamanho > 50 MB
- Categoria "Dicionários e Concordâncias" (sempre pesado)
- Qualquer coisa com PDF escaneado

**Trigger 3 — Repetição:**
- Já usou este fluxo antes na sessão
- Re-processamento de categoria após update de kbs

**Frases que ativam:**
- "traz os livros do Drive"
- "puxa tudo do Drive /1. Fides"
- "processa os livros do [drive/pasta]"
- "baixa os [N] livros"
- "trás os livros da categoria X"
- "indexa o drive"

## Quando NÃO ativar

- Pedido de 1-3 livros pequenos (processa direto)
- "traz o livro X" (1 livro) → fazer download direto, não precisa do servidor
- Arquivos já convertidos (não duplica)

## Localização dos arquivos

- **Servidor HTTP:** `.claude/skills/book-pipeline/server.py` (porta 8765)
- **Supervisor imortal:** `.claude/skills/book-pipeline/start.sh` (loop de restart)
- **OCR helper:** `.claude/skills/book-pipeline/ocr-pdf.py`
- **State:** `/tmp/server-livros-state.json` (sobrevive restart)
- **Log:** `/tmp/server-livros.log`
- **Config OAuth:** `~/.config/gdrive-mcp/gcp-oauth.keys.json` + `gdrive-credentials.json`

## Fluxo da skill (executado pela IA)

Quando ativada:

1. **Verificar dependências** (`uvx`, `python3`, `curl`, `lsof`)
2. **Verificar OAuth do Drive:**
   - Se `~/.config/gdrive-mcp/` não existe OU credenciais expiradas:
     - Rodar `./setup.sh` que cria o config e abre browser para login
3. **Copiar/criar o servidor** se ainda não existe
4. **Subir o servidor:**
   - `./start.sh` (imortal — restart automático se cair)
5. **Verificar inventário:**
   - GET `/atualizar` para listar arquivos do Drive
6. **Iniciar worker "Trazer Todos":**
   - POST `/trazer-todos`
   - Processa 1 por 1, salva state, atualiza kbs
7. **Mostrar URL pro usuário:**
   - `http://localhost:8765` (no navegador local)
   - `http://<server-ip>:8765` (se acessando de outra máquina)
8. **Sinalizar sucesso** com link pro user acompanhar

## Comandos disponíveis após ativar

- `tail -f /tmp/server-livros.log` — log em tempo real
- `curl -s http://localhost:8765/worker-status` — status do worker
- `curl -s http://localhost:8765/` — lista de pendentes (atualiza a cada 5s)
- `pkill -f server-livros.py` — parar tudo

## Comportamento esperado

- IA detecta pedido de muitos livros
- IA executa `./setup.sh` se necessário
- IA executa `./start.sh` para subir o servidor
- IA POST `/trazer-todos` para iniciar processamento
- IA mostra URL pro usuário acompanhar
- IA monitora progresso (a cada 5min?) e atualiza o usuário
- Se servidor cair, supervisor reinicia automaticamente
- Quando acabar, IA faz commit dos .md criados (se ainda não foi feito)
- IA atualiza kbs-*.yaml com novos livros

## Saída típica

```
✅ Servidor book-pipeline iniciado

📊 Status atual:
  Total no inventário: 437 livros (~8.5 GB)
  Já processados: 230
  Erros: 12
  Faltam: 207
  Worker: 🟢 Rodando
  Atual: Teologia Sistemática, Vol 2 - Bavinck

🌐 Acompanhe em: http://localhost:8765
   - Auto-refresh a cada 5 segundos
   - Lista os livros que ainda faltam
   - Mostra erros quando ocorrem

🛠️ Comandos úteis:
   tail -f /tmp/server-livros.log    # log ao vivo
   curl -s http://localhost:8765/worker-status

⏱️  Estimativa: ~1-3 horas para terminar (depende dos PDFs escaneados)
```

## Integração com outras skills

- `study-conhecimento` — quando o user pedir para organizar/catalogar
- `obsidian-export` — depois de indexar, o obsidian pode usar os metadados das kbs
- Outras personas (hermes, bibliotecário, etc) — podem consultar a biblioteca via kb

## Detalhes técnicos

Veja `docs/TECHNICAL.md` para implementação completa.
