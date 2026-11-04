---
name: wardrobe-profiler
description: Converte la cronologia delle transazioni cliente (dataset H&M) in un Guardaroba Semantico compatto usando le euristiche Netflix GenRec (Retain in Full, Summarize, Denoise). Usa questa skill per profilare lo stile dell'utente e individuare il wardrobe gap.
---

# Skill: Wardrobe Profiler & Context Engineer

## Obiettivo
Convertire la cronologia grezza delle transazioni del cliente (dataset H&M) in una rappresentazione qualitativa compatta ("Guardaroba Semantico"), applicando le euristiche del paper Netflix GenRec.

## Euristiche di Compattazione (GenRec)
1. **Retain in Full**: Conserva descrizioni complete per capi di valore (capispalla, abiti, calzature).
2. **Summarize**: Raggruppa i capi basici ripetitivi (t-shirt, intimo) in un unico segnale riassuntivo.
3. **Denoise**: Ignora transazioni anomale isolate e concentra l'attenzione sulle ultime 10 transazioni significative (Elbow Point).

## Output Atteso
Un oggetto JSON valido con:
- `style_persona`: sintesi dello stile prevalente (es. "Minimalist Smart-Casual").
- `palette`: lista dei 3 colori dominanti.
- `formality_level`: "Casual", "Smart-Casual", o "Formal".
- `wardrobe_gap`: identificazione del capo chiave mancante nell'armadio.
