---
name: estudo-fluxo-02-organizar
description: "Etapa 2: processa e indexa materiais de estudo (áudio, PDF, DOCX, TXT) numa base de conhecimento estruturada. Use depois de descobrir o tópico, antes de aprender."
---

# estudo-fluxo-02-organizar

**Etapa 2 do Fluxo de Aprendizado: Organizar**

Processa e indexa os materiais de estudo (MP3, PDF, DOCX, TXT) numa base de conhecimento estruturada.

## Entrada
- Caminho de diretório com materiais
- Tópico já definido (de 01-descobrir)

## Processo
0. Se a pasta de origem estiver bagunçada (muitos arquivos soltos, duplicatas, sem organização),
   oferecer a skill `file-organizer` (`.claude/skills/file-organizer/`) antes de processar — organiza
   por tipo/tema e remove duplicata (por hash), sempre com confirmação antes de mover/apagar
1. Detecta tipos de arquivo
2. Processa cada tipo — **regra obrigatória: nunca ler o arquivo original diretamente** (ver `CLAUDE.md` Regra 2):
   - MP3/WAV → `study-audio-capture` transcreve → bruto em `data/audios/aulas/<materia>/<unidade>/parteN.txt` → elaborados (transcrição, resumo, pontos, perguntas) em `data/estudos/aulas/<materia>/<unidade>/parteN/`
   - PDF/EPUB/DOCX/RTF (material de referência/livro) → skill `book-to-skill` extrai estrutura → gera skill/`.md`
   - PDF/DOCX/PPTX/XLSX simples (ex.: plano de aula, nota curta, slide, planilha) → skill `markitdown` converte direto para `.md`, salvo em `data/estudos/notas/<tema>/`
   - PDF **escaneado** (foto de prova, formulário) → skill `pdf-processing-pro` (OCR) antes de markitdown
   - TXT/MD → já está em formato lido, só indexa
3. Extrai conceitos-chave do `.md` gerado (nunca do arquivo original)
4. Indexa na KnowledgeBase (`study-rag-local` se disponível) e registra em `data/biblioteca/` (via `study-gerenciar-bibliotecas` se for material recorrente)
5. Gera sumário de materiais

## Saída
- Arquivos processados em `data/estudos/`
- Índice de materiais (`02-materiais-indexados.md`)
- KnowledgeBase pronta para consultas

## Persona Padrão
Professor — valida que a organização está correta
