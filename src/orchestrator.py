import os
import time
import json
from typing import Dict, Any, Optional, List
from src.data_engine import HMDataEngine
from src.agents.profiler_agent import ProfilerAgent, CustomerProfile
from src.agents.matcher_agent import MatcherAgent, MatcherResult, OutfitCombination
from src.agents.copywriter_agent import CopywriterAgent, LookbookCopy
from src.agents.critic_guardrail import CriticGuardrailAgent, AuditVerdict

class FashopOrchestrator:
    def __init__(self, data_engine: Optional[HMDataEngine] = None):
        self.db = data_engine or HMDataEngine()
        self.profiler = ProfilerAgent()
        self.matcher = MatcherAgent()
        self.copywriter = CopywriterAgent()
        self.critic = CriticGuardrailAgent()
        self.hitl_queue_path = os.path.join(self.db.data_dir, "hitl_review_queue.json")

    def _enqueue_hitl_ticket(self, ticket: Dict[str, Any]) -> None:
        """Salva asincronamente l'evento in una coda persistente JSON per la revisione del team CRM/Stylist."""
        try:
            tickets = []
            if os.path.exists(self.hitl_queue_path):
                try:
                    with open(self.hitl_queue_path, "r", encoding="utf-8") as f:
                        tickets = json.load(f)
                except Exception:
                    tickets = []
            tickets.append(ticket)
            with open(self.hitl_queue_path, "w", encoding="utf-8") as f:
                json.dump(tickets, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"[ORCHESTRATOR HITL ERROR] Impossibile scrivere su coda HITL: {e}")

    def _build_deterministic_fallback(
        self, 
        profile: CustomerProfile, 
        wardrobe: List[Dict[str, Any]], 
        gender: str
    ) -> tuple[MatcherResult, LookbookCopy]:
        """
        Costruisce un fallback deterministico sicuro (Zero-Risk):
        1. Query SQL pura per trovare un capo a catalogo attivo compatibile con la palette.
        2. Associazione con i capi storici del guardaroba.
        3. Generazione di copy pre-approvato da template, zero allucinazioni LLM.
        """
        fallback_item = self.db.get_deterministic_fallback_item(index_group=gender, palette=profile.palette)
        if not fallback_item:
            fallback_item = {
                "article_id": "0108775015",
                "prod_name": "Strap top",
                "colour_group_name": "Black",
                "product_type_name": "Vest top"
            }

        pivot_id = str(fallback_item["article_id"]).zfill(10)
        pivot_name = fallback_item.get("prod_name", "Capo Essenziale")

        # Seleziona fino a 2 capi storici dall'armadio
        paired_ids = [str(w["article_id"]).zfill(10) for w in wardrobe[:2]]
        outfits = [
            OutfitCombination(
                look_name="Essential Capsule Look",
                new_pivot_id=pivot_id,
                paired_wardrobe_ids=paired_ids,
                styling_rationale=f"Abbinamento sicuro e senza tempo basato sul capo essenziale '{pivot_name}' coordinato ai tuoi acquisti storici."
            ),
            OutfitCombination(
                look_name="Daily Versatile Look",
                new_pivot_id=pivot_id,
                paired_wardrobe_ids=paired_ids[:1],
                styling_rationale="Look versatile perfetto per ogni momento della giornata con armonia cromatica garantita."
            )
        ]

        matching = MatcherResult(
            pivot_article_id=pivot_id,
            pivot_prod_name=pivot_name,
            outfits=outfits
        )

        copy = LookbookCopy(
            subject=f"La selezione essenziale per il tuo stile: {pivot_name}",
            headline="Un classico senza tempo dal catalogo H&M",
            intro_message=(
                f"Abbiamo selezionato per te un articolo fondamentale dal catalogo H&M ({pivot_name}), "
                f"perfettamente coordinabile con i capi e i colori della tua storia di acquisto."
            ),
            outfit_stories=[
                "Combinalo con i tuoi capi preferiti per un look sobrio, elegante ed equilibrato.",
                "Una soluzione versatile concepita per durare e valorizzare il tuo guardaroba esistente."
            ]
        )

        return matching, copy

    def run_pipeline(
        self, 
        customer_id: str, 
        max_retries: int = 3, 
        simulate_error: bool = False,
        simulate_semantic_error: bool = False,
        force_retry_exhaustion: bool = False
    ) -> Dict[str, Any]:
        """
        Esegue il flusso end-to-end con Reflection Loop e salvaguardia a due vie:
        - simulate_error=True: inietta un ID fittizio ('0999999999') al tentativo 1 per mostrare il blocco deterministico.
        - simulate_semantic_error=True: inietta un copy con claim vietati al tentativo 1 per testare il guardrail semantico.
        - force_retry_exhaustion=True: forza il fallimento di tutti i tentativi per dimostrare la Graceful Degradation e l'HITL queue.
        """
        logs = []
        logs.append(f"Avvio pipeline per cliente: {customer_id}")

        # 1. Estrazione dati storici
        wardrobe = self.db.get_customer_wardrobe(customer_id, limit=10)
        if not wardrobe:
            return {"status": "ERROR", "message": f"Nessuna transazione per il cliente {customer_id}"}
        logs.append(f"Estratti {len(wardrobe)} capi dal guardaroba storico.")

        # 2. Verbalization GenRec
        profile = self.profiler.verbalize_wardrobe(wardrobe)
        logs.append(f"Profilo stilistico: {profile.style_persona} | Gap: {profile.wardrobe_gap}")

        # 3. Candidati dal catalogo reale
        gender = "Ladieswear" if "Women" in profile.style_persona or "Donna" in profile.style_persona else "Menswear"
        candidates = self.db.get_candidate_items_for_capsule(index_group=gender, limit=20)
        if not candidates:
            candidates = self.db.get_candidate_items_for_capsule(index_group="Ladieswear", limit=20)
        logs.append(f"Estratti {len(candidates)} articoli candidati reali dal catalogo.")

        # 4. Multi-Agent Reflection Loop
        attempt = 0
        retry_feedback = ""
        matching: Optional[MatcherResult] = None
        copy: Optional[LookbookCopy] = None
        verdict: Optional[AuditVerdict] = None
        fallback_applied = False
        hitl_ticket = None

        while attempt < max_retries:
            attempt += 1
            logs.append(f"\n--- [TENTATIVO {attempt}/{max_retries}] ---")

            # Matcher propone il look
            matching = self.matcher.select_pivot_and_match(
                profile=profile,
                wardrobe=wardrobe,
                candidates=candidates,
                retry_feedback=retry_feedback
            )

            # SCENARIO TRAPPOLA DETERMINISTICA (R6): Inietta errore SKU fittizio
            if (simulate_error and attempt == 1) or force_retry_exhaustion:
                logs.append("⚠️ [DEMO TRIGGER - DETERMINISTICO]: Iniezione intenzionale di un articolo fittizio non a catalogo ('0999999999')...")
                matching.pivot_article_id = "0999999999"

            logs.append(f"Matcher seleziona capo pivot: {matching.pivot_article_id} ({matching.pivot_prod_name})")

            # Copywriter scrive la proposta
            copy = self.copywriter.generate_lookbook(profile, matching)

            # SCENARIO TRAPPOLA SEMANTICA: Inietta claim vietati o tono aggressivo
            if (simulate_semantic_error and attempt == 1) or (force_retry_exhaustion and attempt == 2):
                logs.append("⚠️ [DEMO TRIGGER - SEMANTICO]: Iniezione intenzionale di claim ingannevoli ('garantito al 100%') e FOMO aggressiva...")
                copy.subject = "Affare irripetibile garantito al 100%: acquista subito o te ne pentirai!"
                copy.intro_message = "Prodotto con efficacia miracolosa garantita al 100%. Solo oggi, se non compri sarai l'unico escluso."

            # Il Critic Guardrail verifica l'output
            verdict = self.critic.audit(matching, copy, self.db)

            if verdict.approved:
                logs.append(f"✅ GUARDRAIL APPROVATO al tentativo {attempt}! Procedo con il rilascio.")
                break
            else:
                logs.append(f"🛑 GUARDRAIL RIFIUTATO: {verdict.reason}")
                if attempt < max_retries:
                    logs.append("🔄 Avvio Reflection Loop: feedback inviato al Matcher per autoriparazione...")
                    retry_feedback = f"ERRORE NEL TENTATIVO PRECEDENTE: {verdict.reason}. Scegli un articolo differente, rigorosamente presente nei candidati e mantieni tono sobrio e senza claim ingannevoli."
                    simulate_error = False
                    simulate_semantic_error = False

        # 5. Salvaguardia a Due Vie a Fine Retry (Graceful Degradation + HITL Escalation)
        if not verdict or not verdict.approved:
            logs.append(f"\n⚠️ [RETRY EXHAUSTION]: Raggiunto il limite di {max_retries} tentativi senza approvazione del Guardrail.")
            logs.append("🛡️ [SAFE DEGRADATION]: Attivazione del Fallback Deterministico Sicuro (Zero-Risk via SQL puro)...")
            
            fallback_matching, fallback_copy = self._build_deterministic_fallback(profile, wardrobe, gender)
            matching = fallback_matching
            copy = fallback_copy
            fallback_applied = True

            # Registrazione nella coda Human-in-the-Loop
            hitl_ticket = {
                "ticket_id": f"HITL-{customer_id[:8]}-{int(time.time())}",
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                "customer_id": customer_id,
                "severity": "WARNING",
                "status": "PENDING_REVIEW",
                "exhausted_attempts": attempt,
                "last_critic_reason": verdict.reason if verdict else "Unknown error",
                "last_violations": verdict.violations if verdict else [],
                "fallback_article_id": fallback_matching.pivot_article_id,
                "customer_style": profile.style_persona
            }
            self._enqueue_hitl_ticket(hitl_ticket)
            logs.append(f"📥 [HITL QUEUE]: Evento registrato con ID {hitl_ticket['ticket_id']} per revisione manuale team CRM/Stylist.")

        return {
            "status": "FALLBACK_HITL" if fallback_applied else ("SUCCESS" if verdict and verdict.approved else "FAILED"),
            "attempts": attempt,
            "fallback_applied": fallback_applied,
            "escalated_to_human": fallback_applied,
            "hitl_ticket": hitl_ticket,
            "customer_id": customer_id,
            "profile": profile.model_dump(),
            "matching": matching.model_dump() if matching else {},
            "copy": copy.model_dump() if copy else {},
            "verdict": verdict.model_dump() if verdict else {},
            "execution_logs": logs
        }
