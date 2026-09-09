---
name: study-analytics-dashboard
description: "Dashboard de progresso com métricas de retenção, engajamento e pontos fracos. Use quando o usuário pede para ver progresso, estatísticas, ou revisar pontos fracos."
---

# Learning Analytics Dashboard — Acompanhamento de Progresso

**Tipo:** camada automática (não é skill)  
**Escopo:** Study-Agent (persistência cross-session)  
**Transparência:** Zero configuração, zero comandos

---

## O que faz (invisível pro usuário)

A cada sessão de aprendizado:
1. **Registra métricas** (tempo, estágio, persona, conceitos revisados)
2. **Calcula retenção** (% conceitos retidos vs. esquecidos)
3. **Detecta weak points** (conceitos com <70% acerto)
4. **Mostra progresso visual** (histórico de domínio)

**Usuário vê:** Dashboard com gráficos, weak points, próximos marcos

---

## Fluxo (Automático)

```
Usuário termina sessão de aprendizado
    ↓
Orquestrador coleta:
  - tempo_sessao: 45 minutos
  - estágio: 03-aprender
  - persona_usada: Professor
  - conceitos_revisados: [Coração, Sistema Circulatório]
  - acertos: 7/10 (70%)
  - tópicos_fracos: [Válvulas Cardíacas (45%)]
    ↓
Analytics calcula:
  - retention_rate: 78% (vs. esperado 85%)
  - weak_points: [Válvulas Cardíacas, Ciclo Cardíaco]
  - mastery_score: 68/100 (progresso)
  - stage_progression: 60% do estágio 03 concluído
    ↓
Dashboard atualiza `data/analytics/<materia>.yaml`
    ↓
Próxima sessão, Tutor oferece:
  "Vejo que você trava em Válvulas. Deixa revisar?"
```

---

## Métrica de Dashboard

```yaml
analytics:
  usuario_id: "aprendiz-001"
  materia: "Anatomia"
  periodo: "2026-01-01 a 2026-01-31"
  
  # 1. Retenção Geral
  retention_rate: 0.78        # % de conceitos retidos após 7 dias
  target_retention: 0.85      # meta do aprendiz
  
  # 2. Weak Points (conceitos que precisam revisão)
  weak_points:
    - titulo: "Válvulas Cardíacas"
      acerto: 0.45            # 45% acerto
      tentativas: 11
      ultima_revisao: "2026-01-28"
      proxima_revisao_fsrs: "2026-02-01"
    
    - titulo: "Ciclo Cardíaco"
      acerto: 0.62            # 62% acerto
      tentativas: 8
      ultima_revisao: "2026-01-26"
      proxima_revisao_fsrs: "2026-02-02"
  
  # 3. Mastery Timeline (quando atingiu >90% em cada tópico)
  mastery_timeline:
    "Sistema Circulatório": "2026-01-15"
    "Coração": null           # ainda não atingiu 90%
    "Veias": "2026-01-20"
    "Artérias": "2026-01-18"
  
  # 4. Persona Effectiveness (qual persona funciona melhor)
  persona_effectiveness:
    "Professor": { sessoes: 12, retention: 0.82 }
    "Tutor": { sessoes: 5, retention: 0.75 }
    "Coach": { sessoes: 3, retention: 0.90 }
    "Mentor": { sessoes: 1, retention: 0.88 }
  
  # 5. Stage Duration vs. Esperado
  stage_progression:
    "01-descobrir": { concluido: "2026-01-05", dias_esperado: 3, dias_real: 2 }
    "02-organizar": { concluido: "2026-01-10", dias_esperado: 5, dias_real: 7 }
    "03-aprender": { em_progresso: 60%, dias_desde_inicio: 18 }
    "04-praticar": null
    "05-testar": null
    "06-dominio": null
  
  # 6. Engagement Score (0-100)
  engagement_score: 78
    # = (frequencia * 0.4) + (profundidade * 0.3) + (retenção * 0.3)
    # frequencia: 8/10 (5+ sessões por semana)
    # profundidade: 7/10 (tempo médio 40 min/sessão)
    # retenção: 7.8/10 (78% vs. 85% target)
  
  # 7. Histórico (append-only log)
  historico:
    - data: "2026-01-30T14:30:00Z"
      evento: "sessao_concluida"
      estágio: "03-aprender"
      persona: "Professor"
      duração: "45min"
      conceitos: 2
      acertos: 7/10
      retention_antes: 0.76
      retention_depois: 0.78
    
    - data: "2026-01-29T10:15:00Z"
      evento: "weak_point_detectado"
      conceito: "Válvulas Cardíacas"
      acerto: 0.45
      sugestão: "revisar com Coach (melhor retention neste tópico)"
```

---

## Visualizações (Markdown/ASCII)

### Dashboard Resumido (o que Orquestrador mostra)
```
═══════════════════════════════════════════════════════
 📊 PROGRESSO DE APRENDIZADO — Anatomia Cardiovascular
═══════════════════════════════════════════════════════

🎯 Retenção Geral
   ████████░░ 78% (meta: 85%)
   ⚠️ Ligeiramente abaixo da meta — revisar weak points

🔴 Conceitos com Dificuldade (revisão necessária)
   1. Válvulas Cardíacas        ████░░░░░░ 45%  ← urgente
   2. Ciclo Cardíaco            ██████░░░░ 62%
   3. Pressão Arterial          ███████░░░ 70%

✅ Conceitos Dominados (>90%)
   ✓ Sistema Circulatório (100% — 2026-01-15)
   ✓ Veias (95% — 2026-01-20)
   ✓ Artérias (92% — 2026-01-18)

⏱️ Progresso por Estágio
   01-Descobrir ✓ (2 dias)
   02-Organizar ✓ (7 dias)
   03-Aprender  ▓▓▓▓▓▓░░░░ 60% (18 dias até agora)
   04-Praticar  ░░░░░░░░░░ não iniciado
   05-Testar    ░░░░░░░░░░ não iniciado
   06-Domínio   ░░░░░░░░░░ não iniciado

🔥 Engajamento
   Sessões/semana: 5  |  Tempo/sessão: 40min  |  Score: 78/100

🎓 Próximos Passos
   1. Revisar "Válvulas Cardíacas" com Coach (terça-feira)
   2. Consolidar "Ciclo Cardíaco" com exercícios
   3. Avançar para 04-Praticar quando Válvulas atingir 80%
```

### Gráfico de Progresso (Timeline)
```
Semana 1                Semana 2                Semana 3
├────────────────────────────────────────────────────────┤
│ 01    02    03         03         03         03   04   │
│ ✓     ✓     [░░░░▓▓▓▓░░░░░░░░░░░░░░▓▓░]  [ ]  [ ]  │
│       Day5  Day20                                       │
└────────────────────────────────────────────────────────┘
```

---

## Integração com SessionContext

```yaml
# Arquivo persistente: data/analytics/anatomia.yaml
# Atualizado a cada sessão, versionado no git

anatomia:
  user_id: "aprendiz-001"
  topico: "Cardiovascular"
  ultima_atualizacao: "2026-01-30T15:00:00Z"
  
  # Dados compilados acima ↑
```

---

## Auto-Instalação (Background)

- LLM coleta métricas automaticamente
- YAML é atualizado após cada sessão (silent, sem prompt)
- Histórico append-only (nunca sobrescreve, sempre adiciona)

---

## Qualidade & Privacidade

- **Precisão:** 100% (dados diretos de sessão)
- **Rastreabilidade:** append-only log com timestamp
- **Privacidade:** apenas aprendiz + domínio, sem PII
- **Integridade:** versionado em git (auditável)

---

## Referências

- [Learning Analytics Review - Heliyon](https://www.cell.com/heliyon/fulltext/S2405-8440(24)01414-2)
- [AI Learning Analytics Dashboards](https://8allocate.com/blog/ai-learning-analytics-dashboards-for-instructors/)
- [Canvas Analytics](https://www.canvaslms.com/)
