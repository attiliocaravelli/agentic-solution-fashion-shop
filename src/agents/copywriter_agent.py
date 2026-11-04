import json
from google import genai
from google.genai import types
from pydantic import BaseModel, Field
from src.config import settings
from src.agents.profiler_agent import CustomerProfile
from src.agents.matcher_agent import MatcherResult

class LookbookCopy(BaseModel):
    subject: str = Field(description="Oggetto accattivante per la notifica o email")
    headline: str = Field(description="Titolo principale della comunicazione")
    intro_message: str = Field(description="Messaggio introduttivo empatico e orientato al riuso")
    outfit_stories: list[str] = Field(description="Descrizioni narrative per ciascun outfit proposto")

class CopywriterAgent:
    def __init__(self):
        self.client = genai.Client(
            vertexai=True,
            project=settings.PROJECT_ID,
            location=settings.LOCATION
        )

    def generate_lookbook(self, profile: CustomerProfile, matching: MatcherResult) -> LookbookCopy:
        """Produce il copy comunicativo personalizzato ed esplicativo."""
        prompt = f"""
Sei il Lookbook Copywriter di Fashop. Crea un messaggio editoriale di stile personalizzato.
Spiega con trasparenza come il nuovo capo '{matching.pivot_prod_name}' dà nuova vita ai vestiti che il cliente possiede già nell'armadio.

Profilo: {profile.style_persona}
Outfit Pianificati: {matching.model_dump_json()}

Scrivi con tono entusiasta, amichevole e sofisticato.
"""
        response = self.client.models.generate_content(
            model=settings.GEMINI_MODEL,
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=LookbookCopy,
                temperature=0.4
            )
        )
        return LookbookCopy.model_validate_json(response.text)