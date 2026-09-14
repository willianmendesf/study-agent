# book-pipeline

Skill para automatizar o pipeline de trazer livros do Google Drive (ou local) para a base `data/estudos/livros/`.

## Quick start

```bash
# 0. Configurar (uma vez, por usuário — ver SKILL.md "Configuração obrigatória")
#    cria data/perfil/book-pipeline-config.json com o ID da pasta do Drive + mapeamento

# 1. Setup de dependências/OAuth (uma vez)
bash .claude/skills/book-pipeline/setup.sh

# 2. Subir servidor (imune a crash)
bash .claude/skills/book-pipeline/start.sh

# 3. Acessar no navegador
# http://localhost:8765

# 4. Clicar "TRAZER TODOS" (processa 1 por 1, do menor pro maior)

# 5. Parar quando quiser
bash .claude/skills/book-pipeline/stop.sh
```

## Quando a skill ativa automaticamente

A skill ativa quando o usuário:

- Pede ≥15 livros
- Pede um drive/pasta inteiro
- Pede livros > 50 MB
- Diz "trás os livros do Drive"
- Diz "puxa tudo do Drive [pasta]"
- Diz "baixa os livros da categoria X"

Para 1-3 livros pequenos, faz download direto sem servidor.

## Estrutura

```
book-pipeline/
├── SKILL.md          ← instruções de quando ativar (lido pela IA)
├── README.md         ← este arquivo (humanos)
├── server.py         ← servidor HTTP (porta 8765, só 127.0.0.1)
├── ocr-pdf.py         ← helper de OCR para PDFs escaneados
├── setup.sh          ← configura OAuth do Drive + dependências
├── start.sh          ← sobe o servidor em background
├── stop.sh           ← para tudo
└── docs/
    └── TECHNICAL.md  ← detalhes de implementação
```

Config específica do usuário (fora deste diretório, dentro de `data/`, nunca no template):
`data/perfil/book-pipeline-config.json` (drive_root_folder_id, mapeamento, categorias_ignoradas).

## Monitoramento

```bash
# Status do worker
curl -s http://localhost:8765/worker-status | python3 -m json.tool

# Log em tempo real
tail -f /tmp/server-livros.log

# Listar livros processados (a partir da raiz do study-agent)
ls data/estudos/livros/*/*.md | wc -l
```

## Características

- **Imune a crash** — supervisor reinicia automaticamente
- **State persistente** — sobrevive a restart (state.json atômico)
- **Pipeline de fallbacks** — markitdown → mobi → OCR → PDF referência
- **Auto-refresh de token** — OAuth renovado quando expira
- **Filtros inteligentes** — pula imagens, duplicatas, MK Reforma Protestante
- **Log estruturado** — fácil de debugar

## Versão

- **v1.0** — implementação inicial (set 2026)
- Compatível com Python 3.12+
- Dependências: `python3`, `curl`, `lsof`, `uvx` (instala via pip)
