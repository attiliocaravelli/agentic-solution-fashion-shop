import json
from google import genai
from google.genai import types
from pydantic import BaseModel, Field
from src.config import settings
from src.data_engine import HMDataEngine
from src.agents.matcher_agent import MatcherResult
from src.agents.copywriter_agent import LookbookCopy

class AuditVerdict(BaseModel):
    approved: bool = Field(description="True se l'output supera tutti i controlli, altrimenti False")
    reason: str = Field(description="Spiegazione dettagliata in caso di rifiuto o conferma")
    violations: list[str] = Field(default=[], description="Lista di specifiche violazioni riscontrate")

class CriticGuardrailAgent:
    def __init__(self):
        self.client = genai.Client(
            vertexai=True,
            project=settings.PROJECT_ID,
            location=settings.LOCATION
        )

    def audit(
        self, 
        matching: MatcherResult, 
        copy: LookbookCopy, 
        data_engine: HMDataEngine
    ) -> AuditVerdict:
        """
        Esegue il doppio controllo:
        1. Deterministico: esistenza reale dell'SKU nel catalogo H&M.
        2. Semantico: conformità al brand, tono e coerenza generale.
        """
        violations = []

        # 1. CONTROLLO DETERMINISTICO (Zero Hallucination Check)
        pivot_id = matching.pivot_article_id
        if not data_engine.verify_article_exists(pivot_id):
            violations.append(f"ALLUCINAZIONE CATALOGO: L'article_id raccomandato '{pivot_id}' non esiste nel catalogo H&M.")

        # 2. CONTROLLO REGISTRI GUARDAROBA
        for outfit in matching.outfits:
            for w_id in outfit.paired_wardrobe_ids:
                if not data_engine.verify_article_exists(w_id):
                    violations.append(f"CAPO NON RICONOSCIUTO: L'abito dell'armadio '{w_id}' non è un codice valido.")

        if violations:
            return AuditVerdict(
                approved=False,
                reason=" | ".join(violations),
                violations=violations
            )

        # 3. CONTROLLO SEMANTICO (Brand Policy, Deceptive Claims & Tone of Voice)
        prompt = f"""
Sei il Governance & Safety Supervisor di Fashop.
Analizza il copy promozionale e la combinazione outfit per verificare con rigore:
1. Assenza di claim ingannevoli, promesse irrealistiche o discriminatori (es. "garantito al 100%", formule miracolistiche, FOMO aggressiva o manipolatoria).
2. Rispetto del Tone of Voice elegante, inclusivo ed empatico di Fashop (vietati toni perentori, intimidatori o denigratori).
3. Coerenza logica e stagionalità tra il capo pivot ('{matching.pivot_prod_name}') e il messaggio proposto.

Se riscontri qualsiasi violazione di policy o tono, imposta approved=False, compila violations con l'elenco esatto delle violazioni e spiega la motivazione in reason.

Oggetto: {copy.subject}
Titolo: {copy.headline}
Testo: {copy.intro_message}

Rispondi compilando lo schema JSON AuditVerdict.
"""
        response = self.client.models.generate_content(
            model=settings.GEMINI_MODEL,
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=AuditVerdict,
                temperature=0.0
            )
        )
        return AuditVerdict.model_validate_json(response.text)
