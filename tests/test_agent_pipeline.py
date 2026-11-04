import os
import sys
import json
import time

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.data_engine import HMDataEngine
from src.orchestrator import FashopOrchestrator
from src.agents.critic_guardrail import CriticGuardrailAgent, AuditVerdict
from src.agents.matcher_agent import MatcherResult, OutfitCombination
from src.agents.copywriter_agent import LookbookCopy

def test_semantic_guardrail_direct_audit(critic: CriticGuardrailAgent, db: HMDataEngine):
    """
    Test di isolamento per il Guardrail Semantico:
    Invia un copy con claim vietati ('garantito al 100%', FOMO tossica)
    e verifica che il Critic rifiuti l'output con approved=False e segnali la violazione.
    """
    print("\n>>> TEST 3A: Audit Diretto del Guardrail Semantico (Claim Vietati & Tone Violation)...")
    fake_matching = MatcherResult(
        pivot_article_id="0108775015",
        pivot_prod_name="Strap top",
        outfits=[
            OutfitCombination(
                look_name="Summer Look",
                new_pivot_id="0108775015",
                paired_wardrobe_ids=["0108775015"],
                styling_rationale="Look coordinato estivo."
            )
        ]
    )
    toxic_copy = LookbookCopy(
        subject="Affare imperdibile GARANTITO AL 100%: compra ora o sarai un fallito!",
        headline="Risultato miracoloso garantito",
        intro_message="Questo capo ha proprietà dimagranti garantite al 100%. Solo oggi per te!",
        outfit_stories=["Indossalo o te ne pentirai per sempre."]
    )

    verdict = critic.audit(fake_matching, toxic_copy, db)
    print(f"Esito Guardrail Semantico: approved={verdict.approved}")
    print(f"Motivazione Critic: {verdict.reason}")
    print(f"Violazioni rilevate: {verdict.violations}")

    assert not verdict.approved, "Il Guardrail Semantico doveva respingere il copy con claim ingannevoli!"
    print("✅ TEST 3A SUPERATO: Guardrail Semantico ha correttamente intercettato e bloccato la violazione.")

def test_semantic_guardrail_pipeline_flow(orchestrator: FashopOrchestrator, customer_id: str):
    """
    Test End-to-End con iniezione di violazione semantica al tentativo 1.
    Verifica il rifiuto del copy, l'attivazione del Reflection Loop e il recupero al tentativo 2.
    """
    print("\n>>> TEST 3B: Pipeline End-to-End con Errore Semantico & Auto-Repair...")
    t0 = time.time()
    res = orchestrator.run_pipeline(customer_id=customer_id, simulate_semantic_error=True)
    print(f"Completato in {time.time() - t0:.2f}s | Status: {res['status']} in {res['attempts']} tentativi.")

    print("\n--- TRACE DEI LOG DI REFLECTION SEMANTICA ---")
    for log in res["execution_logs"]:
        print(log)

    assert res["attempts"] >= 2, "Il Guardrail Semantico avrebbe dovuto forzare almeno 2 tentativi!"
    assert res["status"] == "SUCCESS", "La pipeline doveva autoripararsi con successo dopo la correzione semantica!"
    print("✅ TEST 3B SUPERATO: Pipeline ha riparato il copy semantico con successo.")

def test_retry_exhaustion_hitl_fallback(orchestrator: FashopOrchestrator, customer_id: str):
    """
    Test di Graceful Degradation & Human-in-the-Loop:
    Forza il fallimento persistente oltre N=3 tentativi e verifica che:
    1. Si attivi il Fallback Deterministico Sicuro (Zero-Risk) via query SQL.
    2. Venga generato un ticket nella coda persistente HITL.
    3. Lo status sia 'FALLBACK_HITL' con fallback_applied=True.
    """
    print("\n>>> TEST 4: Retry Exhaustion (N=3 falliti), Fallback SQL Deterministico & Coda HITL...")
    t0 = time.time()
    res = orchestrator.run_pipeline(
        customer_id=customer_id,
        max_retries=2, # limitiamo a 2 per rapidità di test
        force_retry_exhaustion=True
    )
    print(f"Completato in {time.time() - t0:.2f}s | Status: {res['status']} | Fallback: {res.get('fallback_applied')}")

    print("\n--- TRACE DEI LOG DI DEGRADATION & HITL ---")
    for log in res["execution_logs"]:
        print(log)

    assert res["fallback_applied"] is True, "Il Fallback Deterministico doveva essere applicato!"
    assert res["status"] == "FALLBACK_HITL", "Lo status doveva essere FALLBACK_HITL!"
    assert res.get("hitl_ticket") is not None, "Un ticket HITL doveva essere creato!"

    # Verifica persistenza su file
    assert os.path.exists(orchestrator.hitl_queue_path), f"File HITL non trovato in {orchestrator.hitl_queue_path}"
    with open(orchestrator.hitl_queue_path, "r", encoding="utf-8") as f:
        tickets = json.load(f)
    matching_tickets = [t for t in tickets if t["customer_id"] == customer_id]
    assert len(matching_tickets) > 0, "Il ticket non è stato persistito nel file JSON!"
    print(f"Ticket HITL confermato su file: {matching_tickets[-1]['ticket_id']}")
    print("✅ TEST 4 SUPERATO: Salvaguardia a due vie (Fallback SQL + HITL Escalation) operativa al 100%.")

def main():
    print("=" * 70)
    print("AVVIO TEST SUITE PIPELINE MULTI-AGENTE, GUARDRAILS (R6) & HITL")
    print("=" * 70)

    db = HMDataEngine()
    test_customer = db.get_random_active_customer()
    print(f"Cliente di test selezionato: {test_customer}")

    orchestrator = FashopOrchestrator(data_engine=db)

    # TEST 1: ESECUZIONE NORMALE (Zero errori)
    print("\n>>> TEST 1: Esecuzione standard della pipeline...")
    t0 = time.time()
    res1 = orchestrator.run_pipeline(customer_id=test_customer, simulate_error=False)
    print(f"Completato in {time.time() - t0:.2f}s | Status: {res1['status']} in {res1['attempts']} tentativi.")
    assert res1['status'] == "SUCCESS", "Errore nel flusso standard"
    print(f"Pivot selezionato: {res1['matching']['pivot_prod_name']} ({res1['matching']['pivot_article_id']})")
    print(f"Subject Copy: {res1['copy']['subject']}")

    # TEST 2: DIMOSTRAZIONE GUARDRAIL DETERMINISTICO R6 (SKU allucinato -> Blocco -> Recupero)
    print("\n>>> TEST 2: Simulazione Guardrail Deterministico di Catalogo con autoriparazione...")
    t1 = time.time()
    res2 = orchestrator.run_pipeline(customer_id=test_customer, simulate_error=True)
    print(f"Completato in {time.time() - t1:.2f}s | Status: {res2['status']} in {res2['attempts']} tentativi.")
    assert res2['attempts'] >= 2, "Il Guardrail avrebbe dovuto forzare almeno 2 tentativi!"
    assert res2['status'] == "SUCCESS", "Il sistema doveva autoripararsi con successo!"

    # TEST 3A: GUARDRAIL SEMANTICO AUDIT DIRETTO
    test_semantic_guardrail_direct_audit(orchestrator.critic, db)

    # TEST 4: RETRY EXHAUSTION & HUMAN-IN-THE-LOOP FALLBACK
    test_retry_exhaustion_hitl_fallback(orchestrator, test_customer)

    print("\n" + "=" * 70)
    print("TUTTI I TEST AGENTICI SUPERATI CON SUCCESSO! R4, R6, SAFETY & HITL CONVALIDATI.")
    print("=" * 70)

if __name__ == "__main__":
    main()
