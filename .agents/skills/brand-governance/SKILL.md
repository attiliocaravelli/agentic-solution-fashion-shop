---
name: brand-governance
description: Supervisore indipendente (Critic) per prevenire allucinazioni, incoerenze di catalogo e violazioni delle policy marketing prima del rilascio (Requisito R6). Usa questa skill per verificare la presenza a catalogo di article_id, la coerenza semantica e le policy di brand.
---

# Skill: Brand Governance & Output Guardrail

## Obiettivo
Agire come supervisore indipendente (Critic) per prevenire allucinazioni, incoerenze di catalogo e violazioni delle policy marketing prima del rilascio (Requisito R6).

## Protocollo di Verifica
1. **Verifica Deterministica**: Richiama il tool `verify_article_exists` sul database per confermare che ogni `article_id` esista nel catalogo attivo.
2. **Controllo Semantico di Coerenza**: Verifica che i colori e le stagionalità non siano stridenti (es. capispalla pesanti in estate).
3. **Policy di Brand**: Verifica che il copy non contenga claim ingannevoli o discriminatori.
4. **Verdetto**: Se uno dei criteri fallisce, emetti `approved: false` specificando la causa esatta per forzare il Reflection Loop.
