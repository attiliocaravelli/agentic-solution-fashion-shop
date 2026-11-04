import json
from google import genai
from google.genai import types
from pydantic import BaseModel, Field
from src.config import settings

class CustomerProfile(BaseModel):
    style_persona: str = Field(description="Definizione sintetica dello stile del cliente")
    palette: list[str] = Field(description="I 3 colori predominanti nel guardaroba")
    formality_level: str = Field(description="Livello di formalità: Casual, Smart-Casual, Formal")
    wardrobe_gap: str = Field(description="Tipologia di capo mancante per completare l'armadio")

class ProfilerAgent:
    def __init__(self):
        self.client = genai.Client(
            vertexai=True,
            project=settings.PROJECT_ID,
            location=settings.LOCATION
        )

    def verbalize_wardrobe(self, wardrobe: list[dict]) -> CustomerProfile:
        """Applica il Context Engineering GenRec compattando le transazioni storiche."""
        # Costruisce la sequenza testuale compattata
        wardrobe_text = "\n".join([
            f"- Data: {item['t_dat']} | Capo: {item['prod_name']} | Colore: {item['colour_group_name']} | "
            f"Tipo: {item['product_type_name']} | Categoria: {item['garment_group_name']}"
            for item in wardrobe
        ])

        prompt = f"""
Sei il Profiler Agent di Fashop. Analizza il seguente Guardaroba del cliente (transazioni storiche) 
ed estrai la Style Persona, la palette dominante e il "Wardrobe Gap" (il capo chiave mancante).

CRONOLOGIA GUARDAROBA CLIENTE:
{wardrobe_text}

Rispondi rigorosamente compilando lo schema JSON richiesto.
"""
        response = self.client.models.generate_content(
            model=settings.GEMINI_MODEL,
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=CustomerProfile,
                temperature=0.2
            )
        )
        return CustomerProfile.model_validate_json(response.text)