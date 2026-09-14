# Documentação Técnica — book-pipeline

## Arquitetura

```
┌────────────────────────────────────────────────────────────┐
│ start.sh (setsid + nohup)                                │
│   └── supervisor.sh (loop bash)                          │
│         └── server.py (ThreadingHTTPServer)              │
│               ├── GET  /              (lista pendentes)   │
│               ├── POST /processar/<id> (1 livro)         │
│               ├── POST /trazer-todos  (worker em bg)     │
│               ├── GET  /atualizar     (re-listar drive)  │
│               ├── GET  /worker-status  (JSON)             │
│               ├── GET  /health         (JSON)             │
│               └── Estado: /tmp/server-livros-state.json   │
└────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
                       OAuth 2.0 → Google Drive API v3
                                  │
                                  ▼
                         livros convertidos em
                   data/estudos/livros/<tema>/<prefixo><nome>.md
```

## Fluxo de processamento (worker_trazer_todos)

```
for item in sorted(pendentes, key=size):  # menor → maior
  state['worker']['current'] = item['name']
  save_state()  # atômico via .tmp + rename

  for categoria in MAPEAMENTO:
    dest = MAPEAMENTO[nome] or MAPEAMENTO[categoria]
    if not dest: skip "sem_mapeamento"

  tmp = /tmp/<file_id>
  baixar_drive(file_id, tmp)  # GET /files/{id}?alt=media
  converter(tmp, dest.md)  # markitdown, mobi, ou OCR

  if linhas(dest.md) < 50 and ext == 'pdf':
    ocr(tmp, dest.md)  # EasyOCR com 200dpi

  if ainda falhou and ext == 'pdf':
    shutil.copy(tmp, dest.md.REFERENCE.pdf)  # fallback

  state['done'].append(file_id)  # marca como feito
  save_state()  # atômico
```

## Mapeamento (categoria Drive → pasta local)

| Drive | Pasta local | Prefixo |
|---|---|---|
| Bibliologia | bibliologia/ | BL- |
| Cronologia e Contextos Históricos | cronologia-contextos-historicos/ | CC- |
| Bases da fé | bases-da-fe/ | BF- |
| Sexual | sexual/ | SX- |
| Feminilidade Cristã | familia-crista/ | FM- |
| Familia Cristã | familia-crista/ | FC- |
| Messias | messias/ | MS- |
| Pastoral | pastoral/ | PS- |
| Cultura dos Textos Biblicos | cultura-textos-biblicos/ | CT- |
| Arqueologia Biblica | arqueologia-biblica/ | AQ- |
| Hermeneutica e Exegese | exegese-hermeneutica/ | HE- |
| Simbologias Biblicas | referencias-biblicas/ | SB- |
| Personagens Bíblicos | referencias-biblicas/ | PB- |
| Teologia Bíblica | teologia-biblica/ | TB- |
| Manuais Bíblicos | manuais-biblicos/ | MB- |
| Dicionário Teológico e Exegético | dicionario-teologico/ | DT- |
| Línguas Originais | linguas-originais/ | LO- |
| Igreja | igreja-discipulado/ | IG- |
| Outros | outros/ | OU- |
| Teologia | teologia/ | TG- |
| Teologia Sistemática | teologia-sistematica/ | TS- |
| História da Igreja | historia-igreja/ | HI2- |
| Atlas & Mapas Bíblicos | atlas-mapas/ | AM- |
| Comentários Biblicos | comentarios-biblicos/ | CB- |
| Dicionários, Enciclopédias e Concordâncias Biblicas | dicionarios-concordancias/ | DC- |
| Filosofia Cristã | filosofia-crista/ | FC2- |
| Masculinidade Cristã | masculinidade-crista/ | MC- |
| Temperamentos | temperamentos/ | TP- |
| Literatura | literatura/ | LT- |
| Historia | historia/ | HI- |

Fallback: tudo que não bate → `_to_organize/XX-` (para revisão manual).

## Pipeline de conversão (em `converter()`)

```
1. markitdown (PDF/EPUB/DOCX) — timeout 10min
   └─ se > 50 linhas → OK
   
2. mobi lib + html2text (se for .mobi)
   └─ extrai HTML, converte, salva

3. EasyOCR + pdftoppm (se for .pdf)
   └─ 200dpi, OCR pt+en, timeout 60min

4. Fallback: copia o PDF como .REFERENCE.pdf
```

## Estado (state.json)

```json
{
  "done": ["file_id1", "file_id2", ...],
  "failed": [{"name": "...", "error": "..."}],
  "inventario": [...],  // cached do Drive
  "inventario_atualizado_em": "2026-09-10T...",
  "worker": {
    "running": true,
    "processed": 50,
    "errors": 14,
    "current": "file_atual.pdf",
    "started": "2026-09-10T...",
    "last_update": "..."
  }
}
```

`save_state()` é atômico: escreve em `.tmp` e renomeia — não corrompe se cair no meio.

## OAuth 2.0 — Google Drive

```python
# Refresh automático:
def get_token():
    if time.time() * 1000 < creds['expiry_date'] - 60000:
        return creds['access_token']  # ainda válido
    # Refresh
    data = urllib.parse.urlencode({
        'client_id': keys['client_id'],
        'client_secret': keys['client_secret'],
        'refresh_token': creds['refresh_token'],
        'grant_type': 'refresh_token',
    })
    req = urllib.request.Request('https://oauth2.googleapis.com/token', data=data)
    # retorna novo access_token
```

`access_token` expira em 1h. `refresh_token` é permanente. Renovar 60s antes de expirar.

## Concorrência

- **Download**: 1 por vez (simplifica gestão de memória)
- **Conversão**: 1 por vez no worker (markitdown/uvx usa muito CPU)
- **Server HTTP**: ThreadingHTTPServer (cada request em thread separada)
- **Worker**: thread daemon (roda junto com o server)

Para paralelizar no futuro: usar ThreadPoolExecutor com max_workers=2 para markitdown (mas atenção a OOM).

## Logs

- `/tmp/server-livros.log` — log principal (rotacionado manualmente se preciso)
- `/tmp/supervisor-livros.log` — log do supervisor
- `/tmp/supervisor-stdout.log` — stdout do setsid
- `/tmp/server-livros-state.json` — state persistente

## Troubleshooting

| Problema | Solução |
|---|---|
| Token expirado | Servidor auto-refresh. Se persistir, deletar `gdrive-credentials.json` e rodar `setup.sh` |
| OCR muito lento | PDFs > 50 MB demoram 10-30 min. Configurar `--max-pages` no `ocr-pdf.py` |
| Worker travado | Supervisor reinicia em 3s. Matar manualmente: `pkill -9 -f server-livros.py` |
| State corrompido | Backup manual: `cp state.json state.json.bak`. Auto-recupera do `.tmp` |
| Porta 8765 ocupada | `PORT=8888 bash start.sh` |
| Servidor não sobe | `cat /tmp/server-livros.log` — provavelmente erro de import ou dependência |

## Limites conhecidos

- **Google Drive API**: 1000 requests/100s por user. Listagens grandes = várias requests. O servidor já gerencia.
- **markitdown**: timeout 10 min padrão. PDFs muito grandes (500+ páginas) podem falhar.
- **EasyOCR**: 1h timeout. PDFs > 200 pp demoram demais.
- **uvx**: primeira execução baixa o pacote (~50MB). Demora ~30s no primeiro markitdown.

## Próximas evoluções

- [ ] Pular duplicatas automaticamente por hash md5
- [ ] Detectar idioma do livro (pt/es/en) automaticamente
- [ ] Gerar metadados extra (tamanho, idioma, topicos) via llm
- [ ] Atualizar kb-*.yaml automaticamente após cada download
- [ ] Adicionar botão "cancelar worker" no servidor
- [ ] Suporte a múltiplos drives/contas OAuth
- [ ] Integração com Zotero (exportar biblioteca)
- [ ] Dashboard de estatísticas (gaps por área, etc)
