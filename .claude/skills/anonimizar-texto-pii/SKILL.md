---
name: anonimizar-texto-pii
description: Use antes de enviar texto com dados pessoais brasileiros (CPF, RG, CNH, e-mail, telefone, endereço, CEP, dados bancários, CID etc.) a modelo externo, busca na web, issue, PR ou log — mascara com tags numeradas (<|CPF_1|>) e restaura depois. Também para "anonimizar", "mascarar PII", "tirar dado pessoal" de logs, dumps e documentos. Roda local; não detecta nomes livres.
---

# anonimizar-texto-pii — Mascarar dados pessoais em texto

Detecta identificadores pessoais em português brasileiro (NER local + regex + validação de dígito
verificador) e troca por tags `<|CPF_1|>`, `<|EMAIL_1|>`… Tudo local, sem rede em uso.

## Quando usar

- Texto de produção, log, dump, e-mail ou documento vai para **fora** da máquina (LLM externo, busca,
  issue/PR, mensagem a terceiro). Complementa a cautela com dados pessoais de conversas e sessões.
- Não substitui consulta por código/ID: se dá para consultar sem PII, faça assim.
- **Limite:** detecta documentos, contatos, endereços e dados bancários; **não detecta nomes livres**.
  Trate nomes à parte.

## Instalar (uma vez)

```bash
bash .claude/skills/anonimizar-texto-pii/scripts/install.sh
```

Cria `~/.local/share/anonimizador-dp/` (venv + modelo NER de 4 MB, com checagem de SHA-256).

## Usar

```bash
echo '{"text":"CPF 529.982.247-25, e-mail a@b.com"}' | \
  ~/.local/share/anonimizador-dp/venv/bin/python .claude/skills/anonimizar-texto-pii/scripts/anonymize.py
```

Saída: `{"text": "...tags...", "map": {tag: original}, "counts": {...}}`.

Restaurar a resposta de um modelo externo:

```json
{"mode":"restore","text":"<resposta>","map":{...}}
```

Saída: `text`, `unrestored` (tags que sumiram) e `stray` (tags soltas). Se não vierem vazios, avise o
usuário em vez de adivinhar.

## Regras

1. Envie para fora **apenas** o `text` mascarado.
2. `map` contém PII: mantenha só no turno atual; nunca grave em arquivo, memória, log ou commit.
3. Exemplos e testes usam dados fictícios.

## Terceiros

`anonimizador-dp` (Anatel, GPL-3.0-only) e seu modelo, instalados do PyPI/GitHub Releases em ambiente
separado e chamados como processo à parte. Nenhum código dele é copiado para este repositório.

## Modo automático (picoclaw)

O picoclaw não precisa lembrar de chamar a skill: o hook `scripts/anonymize_hook.py` mascara **toda**
mensagem antes de cada chamada ao modelo (inclusive histórico, saída de ferramentas e prompt de sistema)
e restaura as tags na resposta e nos argumentos de ferramentas. Se o anonimizador falhar, o turno é
abortado e nada é enviado (`ANON_FAIL_OPEN=1` inverte isso). Ativar:

```bash
bash .claude/skills/anonimizar-texto-pii/scripts/install.sh
python3 .claude/skills/anonimizar-texto-pii/scripts/enable_picoclaw_hook.py <config.json do picoclaw> \
  --python ~/.local/share/anonimizador-dp/venv/bin/python \
  --hook "$PWD/.claude/skills/anonimizar-texto-pii/scripts/anonymize_hook.py" \
  --anon-home ~/.local/share/anonimizador-dp
```

Reinicie o picoclaw depois. Limites: nomes livres e imagens não são mascarados.
