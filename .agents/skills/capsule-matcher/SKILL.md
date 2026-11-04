---
name: capsule-matcher
description: Esegue il Single-Pass Ranking su articoli candidati reali estratti da DuckDB per identificare il Capo Pivot compatibile con il guardaroba dell'utente. Usa questa skill per il matching e la generazione di capsule outfit.
---

# Skill: Capsule Recommender & Outfit Matcher

## Obiettivo
Eseguire un Single-Pass Ranking su una lista di articoli candidati reali estratti da DuckDB, identificando il "Capo Pivot" (Missing Piece) in grado di combinarsi con i capi già presenti nel guardaroba del cliente.

## Regole di Matching
1. **Catalog Awareness**: Seleziona SOLO ed ESCLUSIVAMENTE `article_id` presenti nella lista candidati fornita.
2. **Outfit Multiplier**: Il Capo Pivot deve abbinarsi con almeno 2 capi storici distinti dell'utente.
3. **Reflection Handling**: Se ricevi un feedback dal Critic Agent (`retry_feedback`), rispetta rigorosamente i vincoli negativi indicati (es. "escludi capo ID X", "incompatibilità stagionale").
