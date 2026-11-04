import json
from google import genai
from google.genai import types
from pydantic import BaseModel, Field
from src.config import settings
from src.agents.profiler_agent import CustomerProfile

class OutfitCombination(BaseModel):
    look_name: str = Field(description="Nome evocativo del look (es. Smart Office, Weekend Brunch)")
    new_pivot_id: str = Field(description="ID dell'articolo nuovo consigliato")
    paired_wardrobe_ids: list[str] = Field(description="Lista di article_id storici del guardaroba con cui abbinarlo")
    styling_rationale: str = Field(description="Spiegazione dell'armonia di colori e stili")

class MatcherResult(BaseModel):
    pivot_article_id: str = Field(description="L'article_id scelto come capo pivot dal pool candidati")
    pivot_prod_name: str = Field(description="Nome del capo pivot")
    outfits: list[OutfitCombination] = Field(description="Almeno 2 combinazioni di outfit con capi posseduti")

class MatcherAgent:
    def __init__(self):
        self.client = genai.Client(
            vertexai=True,
            project=settings.PROJECT_ID,
            location=settings.LOCATION
        )

    def select_pivot_and_match(
        self, 
        profile: CustomerProfile, 
        wardrobe: list[dict], 
        candidates: list[dict],
        retry_feedback: str = ""
    ) -> MatcherResult:
        """Single-Pass Ranking: seleziona il capo pivot tra i candidati reali e genera gli outfit."""
        
        # Lista capi posseduti con ID
        wardrobe_summary = [
            {"article_id": w["article_id"], "name": w["prod_name"], "color": w["colour_group_name"], "type": w["product_type_name"]}
            for w in wardrobe
        ]
        
        # Pool candidati reali forniti da DuckDB
        candidate_summary = [
            {"article_id": c["article_id"], "name": c["prod_name"], "color": c["colour_group_name"], "desc": c["detail_desc"]}
            for c in candidates
        ]

        feedback_clause = ""
        if retry_feedback:
            feedback_clause = f"\nATTENZIONE - FEEDBACK DAL CRITIC SUL TENTATIVO PRECEDENTE:\n{retry_feedback}\nCorreggi immediatamente questo errore!\n"

        prompt = f"""
Sei il Capsule Matcher Agent di Fashop. 
Il tuo obiettivo è selezionare UN SOLO CAPO PIVOT dalla lista CANDIDATI REALI che risponda al bisogno di stile 
e comporre almeno 2 outfit coordinati usando i capi già posseduti nel GUARDAROBA.

{feedback_clause}
PROFILO STILE: {profile.style_persona} | Palette: {profile.palette} | Gap: {profile.wardrobe_gap}

GUARDAROBA POSSEDUTO:
{json.dumps(wardrobe_summary, indent=2)}

CANDIDATI REALI DAL CATALOGO (SCEGLI SOLO DA QUI):
{json.dumps(candidate_summary, indent=2)}

REGOLE TASSATIVE:
1. Usa ESCLUSIVAMENTE un article_id presente nella lista CANDIDATI REALI come pivot_article_id.
2. In 'paired_wardrobe_ids', usa ESCLUSIVAMENTE gli article_id presenti nel GUARDAROBA POSSEDUTO.
"""
        response = self.client.models.generate_content(
            model=settings.GEMINI_MODEL,
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=MatcherResult,
                temperature=0.2
            )
        )
        return MatcherResult.model_validate_json(response.text)