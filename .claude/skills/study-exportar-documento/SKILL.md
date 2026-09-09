---
name: study-exportar-documento
description: "Converte material já em markdown para .docx/.pptx/.pdf pronto para entregar ou imprimir. Use quando o usuário pede para gerar um trabalho, exportar em Word/PowerPoint, ou montar um PDF para imprimir."
---

# Exportar Documento — Trabalhos, Resumos e Provas em .docx/.pdf

**Tipo:** skill real (invocada via `CLAUDE.md` Regra 1)
**Escopo:** Study-Agent — última etapa de qualquer material que precise sair do markdown (trabalho para
entregar, resumo para imprimir, simulado para aplicar em papel)
**Trigger:** usuário pede para "gerar um trabalho", "exportar em word/docx", "montar um PDF pra imprimir"

---

## Objetivo

Study-Agent produz tudo internamente em Markdown (é o formato barato em tokens e fácil de indexar —
ver `CLAUDE.md` Regra 2). Esta skill é o **único ponto** onde esse markdown vira um arquivo que o
usuário efetivamente entrega/imprime: `.docx` (trabalho acadêmico) ou `.pdf` (prova/resumo pronto pra
imprimir).

---

## Como gerar — em ordem de preferência

O agente que está rodando o Study-Agent pode ser Claude Code, Hermes, opencode, ou outro — a estratégia
se adapta ao que está disponível, sem travar se faltar uma ferramenta:

### 1. Skills instaladas no repositório (método principal)

Já instaladas em `.claude/skills/` — usar sempre que o formato de saída bater:

- **`.docx`** (trabalho, memorando, carta) → skill `docx` (`.claude/skills/docx/`) — cria/edita Word de
  verdade: tabelas, imagens, comentários, tracked changes, cabeçalho/rodapé, sumário automático.
- **`.pptx`** (apresentação, seminário) → skill `pptx` (`.claude/skills/pptx/`) — gratuita e local
  (usa `PptxgenJS` + `LibreOffice`), com guia de design e checklist de QA visual. **Preferir esta** a
  `scientific-slides` quando o usuário não tem `OPENROUTER_API_KEY` configurada.

### 2. `pandoc` (fallback universal — funciona em qualquer agente com Bash)

```bash
pandoc entrada.md -o saida.docx --reference-doc=<template-opcional>.docx
pandoc entrada.md -o saida.pdf   # requer engine de PDF (ex.: LaTeX ou wkhtmltopdf instalado)
```

- Não precisa de MCP nem de API externa — só `pandoc` instalado no sistema (`apt install pandoc` /
  `brew install pandoc`).
- Aceita **template Word** (`--reference-doc`) se o usuário tiver um modelo institucional (timbre,
  fonte, margens da faculdade/curso) — perguntar se existe antes de gerar sem formatação.
- Para PDF com boa tipografia, prefira instalar um engine LaTeX leve (`tectonic` é mais rápido que
  TeX Live completo) ou usar `wkhtmltopdf` como alternativa mais simples.

### 3. MCP de documento (se o host tiver um conectado)

Se o ambiente tem um MCP/conector de documentos (ex.: Google Docs, Word Online) já autorizado pelo
usuário, é uma alternativa válida — mas **nunca assuma que existe**: verificar antes de tentar, e se
não estiver disponível, cair para pandoc sem reclamar.

---

## Processo

1. **Montar o markdown final** (o conteúdo já deve existir — resumo do `estudo-fluxo-03-aprender`,
   simulado do `study-gerar-provas-simulados`, etc.). Esta skill **não gera conteúdo pedagógico**, só
   converte o que já foi produzido.
2. **Estruturar para documento acadêmico** quando for "trabalho": capa (título, autor, matéria, data),
   sumário se o documento for longo (>3 seções), seções numeradas, referências no fim — perguntar os
   dados da capa se não estiverem no contexto (nome, instituição, disciplina).
3. **Escolher o método** (§Como gerar, em ordem de preferência) — testar disponibilidade antes de
   assumir (`command -v pandoc`, verificar skills carregadas do host).
4. **Gerar o arquivo** em `data/estudos/trabalhos/<tema>/<nome>.docx` (ou `.pdf`).
5. **Entregar ao usuário** via mecanismo de envio de arquivo do host (ex.: `SendUserFile` no Claude
   Code) — nunca deixar o arquivo só no disco sem avisar onde está.

---

## Quando NÃO usar

- Para simplesmente **ler** um material (resumo, plano de aula) — o markdown já é a forma de trabalho,
  não converta pra docx à toa. Converter só quando o usuário precisa **entregar/imprimir**.
- Para o material de estudo do dia a dia (RAG, revisão) — fica em `.md`, sempre.

---

## Saída

```
data/estudos/trabalhos/<tema>/
└── <nome>.docx | <nome>.pdf
```

## Dependências

- `pandoc` (obrigatório para o caminho 2 — instalar se ausente e avisar o usuário)
- Engine de PDF (`tectonic`/`wkhtmltopdf`, opcional — só se for gerar `.pdf`)
- Skill `.docx` do host **ou** MCP de documento (opcionais — usar se existirem)

## Referências

- `estudo-fluxo-03-aprender/SKILL.md` — fonte típica de conteúdo (resumo a exportar)
- `study-gerar-provas-simulados/SKILL.md` — fonte típica de conteúdo (simulado a exportar/imprimir)
- `CLAUDE.md` — Regra 2 (por que tudo nasce em Markdown, não binário)
