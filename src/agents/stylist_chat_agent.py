import json
import re
from typing import List, Dict, Any, Optional
from google import genai
from google.genai import types
from src.config import settings
from src.data_engine import HMDataEngine

class StylistChatAgent:
    """
    Agente Conversazionale per lo Shopping Interattivo (Personal Stylist AI).
    Consente al cliente di dialogare in linguaggio naturale, comprendere cosa acquistare
    e ricevere consigli di abbinamento circolari basati sul proprio guardaroba storico.
    """
    def __init__(self, data_engine: Optional[HMDataEngine] = None):
        self.db = data_engine or HMDataEngine()
        self.client = genai.Client(
            vertexai=True,
            project=settings.PROJECT_ID,
            location=settings.LOCATION
        )

    def respond(
        self,
        user_message: str,
        conversation_history: List[Dict[str, str]],
        customer_id: str,
        wardrobe: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        # 1. Recupera articoli candidati rilevanti dal catalogo H&M
        if hasattr(self.db, "search_articles"):
            candidates = self.db.search_articles(user_message, limit=12)
        else:
            candidates = self.db.get_candidate_items_for_capsule(limit=12)
        if not candidates:
            candidates = self.db.get_candidate_items_for_capsule(limit=12)

        # 2. Formatta la cronologia del guardaroba posseduto
        wardrobe_summary = "\n".join([
            f"- [POSSEDUTO] ID: {item['article_id']} | {item['prod_name']} ({item['colour_group_name']}) - {item['garment_group_name']}"
            for item in wardrobe[:8]
        ])

        # 3. Formatta gli articoli a catalogo disponibili per l'acquisto
        catalog_summary = "\n".join([
            f"- [A CATALOGO] ID: {c['article_id']} | {c['prod_name']} ({c['colour_group_name']}) | Categoria: {c['garment_group_name']} | Dettaglio: {c.get('detail_desc', '')[:100]}"
            for c in candidates
        ])

        system_instruction = f"""
Sei il Personal Stylist AI di Fashop, un consulente di moda d'alta gamma empatico, sofisticato e orientato alla moda sostenibile e circolare (principi GenRec).
Il tuo obiettivo è guidare il cliente nell'acquisto intelligente di nuovi capi a catalogo che valorizzino e riattivino i capi che possiede già nel suo guardaroba virtuale.

REGOLE CRITICHE DI COMPORTAMENTO:
1. Conosci alla perfezione il Guardaroba Storico del cliente: fai riferimenti specifici ai capi che già possiede quando proponi abbinamenti.
2. Quando suggerisci cosa comprare, seleziona ESCLUSIVAMENTE tra gli ARTICOLI DISPONIBILI A CATALOGO elencati qui sotto.
3. Cita SEMPRE il nome del capo e il codice ID esatto nel formato: **Nome Capo** (Codice: `0xxxxxxxxx`).
4. Spiega il razionale stilistico: perché questo nuovo acquisto completa il suo look, con quale capo del suo guardaroba si abbina e per quale occasione è perfetto.
5. Mantieni un tono raffinato, accogliente e professionale in lingua italiana.
6. Non inventare MAI codici articolo fittizi: ogni proposta deve provenire dalla lista del catalogo fornita.

GUARDAROBA POSSEDUTO DAL CLIENTE:
{wardrobe_summary}

ARTICOLI DISPONIBILI A CATALOGO PER L'ACQUISTO:
{catalog_summary}
"""

        # Costruisci lo storico dei messaggi per la chiamata
        contents = []
        for msg in conversation_history[-6:]:
            role = "user" if msg["role"] == "user" else "model"
            contents.append(types.Content(
                role=role,
                parts=[types.Part.from_text(text=msg["content"])]
            ))
        
        # Aggiungi il messaggio utente corrente
        contents.append(types.Content(
            role="user",
            parts=[types.Part.from_text(text=user_message)]
        ))

        response = self.client.models.generate_content(
            model=settings.GEMINI_MODEL,
            contents=contents,
            config=types.GenerateContentConfig(
                system_instruction=system_instruction,
                temperature=0.4
            )
        )

        reply_text = response.text or ""

        # Estrai gli ID degli articoli citati nella risposta per renderizzare card visive
        recommended_items = []
        for cand in candidates:
            if cand["article_id"] in reply_text:
                recommended_items.append(cand)

        return {
            "reply": reply_text,
            "recommended_items": recommended_items
        }
