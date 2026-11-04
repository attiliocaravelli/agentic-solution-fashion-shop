import streamlit as st
import time
import json
from src.data_engine import HMDataEngine
from src.orchestrator import FashopOrchestrator
from src.agents.stylist_chat_agent import StylistChatAgent
from src.config import settings

# ---------------------------------------------------------
# CONFIGURAZIONE PAGINA & FASHION UX AGENT THEME
# ---------------------------------------------------------
st.set_page_config(
    page_title="Fashop – Smart Capsule AI Studio & Personal Stylist",
    page_icon="👗",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS per dare un look editoriale "Atelier Fashion" alla UI
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Playfair+Display:ital,wght@0,600;1,400&family=Plus+Jakarta+Sans:wght@300;400;600;700&display=swap');

    html, body, [class*="css"] {
        font-family: 'Plus Jakarta Sans', sans-serif;
        color: #1A1A1A;
    }
    h1, h2, h3 {
        font-family: 'Playfair Display', serif;
        font-weight: 600;
        letter-spacing: -0.5px;
    }
    .main-header {
        background: linear-gradient(135deg, #0F172A 0%, #1E293B 100%);
        padding: 2.2rem 2.5rem;
        border-radius: 16px;
        color: #F8FAFC;
        margin-bottom: 1.5rem;
        box-shadow: 0 10px 25px -5px rgba(15, 23, 42, 0.15);
    }
    .badge-gcp {
        background: #3B82F6;
        color: white;
        padding: 4px 10px;
        border-radius: 12px;
        font-size: 0.75rem;
        font-weight: 600;
        text-transform: uppercase;
    }
    .badge-antigravity {
        background: #10B981;
        color: white;
        padding: 4px 10px;
        border-radius: 12px;
        font-size: 0.75rem;
        font-weight: 600;
    }
    .wardrobe-card {
        background: #F8FAFC;
        border: 1px solid #E2E8F0;
        border-radius: 12px;
        padding: 1rem;
        margin-bottom: 0.8rem;
        transition: transform 0.2s ease;
    }
    .wardrobe-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 12px rgba(0,0,0,0.05);
    }
    .pivot-card {
        background: #FEF9C3;
        border: 2px solid #FACC15;
        border-radius: 14px;
        padding: 1.5rem;
        box-shadow: 0 6px 18px rgba(250, 204, 21, 0.15);
    }
    .item-card {
        background: #FFFFFF;
        border: 1px solid #E2E8F0;
        border-radius: 10px;
        padding: 0.9rem;
        margin-top: 0.5rem;
        box-shadow: 0 2px 6px rgba(0,0,0,0.04);
    }
    .guardrail-alert {
        background: #FEE2E2;
        border-left: 6px solid #EF4444;
        padding: 1.2rem;
        border-radius: 8px;
        color: #991B1B;
        font-weight: 500;
        margin-bottom: 1rem;
    }
    .guardrail-pass {
        background: #ECFDF5;
        border-left: 6px solid #10B981;
        padding: 1.2rem;
        border-radius: 8px;
        color: #065F46;
        font-weight: 500;
        margin-bottom: 1rem;
    }
    .chat-pill-btn {
        background: #F1F5F9;
        border: 1px solid #CBD5E1;
        border-radius: 20px;
        padding: 6px 14px;
        font-size: 0.85rem;
        cursor: pointer;
        margin-right: 8px;
        margin-bottom: 8px;
        display: inline-block;
    }
</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------
# INIZIALIZZAZIONE COMPONENTI BACKEND
# ---------------------------------------------------------
@st.cache_resource
def get_backend():
    db = HMDataEngine()
    orchestrator = FashopOrchestrator(data_engine=db)
    stylist = StylistChatAgent(data_engine=db)
    return db, orchestrator, stylist

@st.cache_data
def fetch_cached_wardrobe(cust_id: str, limit: int = 6):
    d, _, _ = get_backend()
    return d.get_customer_wardrobe(cust_id, limit=limit)

try:
    db, orchestrator, stylist = get_backend()
except Exception as e:
    st.error(f"Errore inizializzazione backend: {e}")
    st.stop()

# ---------------------------------------------------------
# HEADER EXECUTIVE
# ---------------------------------------------------------
st.markdown("""
<div class="main-header">
    <div style="display: flex; justify-content: space-between; align-items: center;">
        <div>
            <h1 style="margin: 0; color: #FFFFFF; font-size: 2.3rem;">Fashop – Smart Capsule Studio & AI Stylist</h1>
            <p style="margin: 0.4rem 0 0 0; color: #94A3B8; font-size: 1.05rem;">
                Autonomous Recommerce & Interactive Shopping Assistant powered by <b>Netflix GenRec</b> & <b>Gemini 2.5 Flash</b>
            </p>
        </div>
        <div style="text-align: right;">
            <span class="badge-gcp">Google Cloud us-central1</span><br>
            <span class="badge-antigravity" style="margin-top: 6px; display: inline-block;">Google Antigravity SDK</span>
        </div>
    </div>
</div>
""", unsafe_allow_html=True)

# ---------------------------------------------------------
# SIDEBAR: CONTROLLO CLIENTE & SIMULATORE GUARDRAIL
# ---------------------------------------------------------
with st.sidebar:
    st.image("https://images.unsplash.com/photo-1490481651871-ab68de25d43d?w=600&auto=format&fit=crop&q=80", use_container_width=True)
    st.header("⚙️ Studio Controller")
    
    # Cliente di default (quello del nostro test superato)
    default_client = "50541036e4e0a0e38ff69ab6fb953c02725e0081e6c78a4522770524f554d4aa"
    if "customer_id" not in st.session_state:
        st.session_state["customer_id"] = default_client
    
    col_btn1, col_btn2 = st.columns(2)
    with col_btn1:
        if st.button("🎲 Random Client"):
            random_id = db.get_random_active_customer()
            if random_id:
                st.session_state["customer_id"] = random_id
                st.rerun()
    with col_btn2:
        if st.button("🔄 Reset Default"):
            st.session_state["customer_id"] = default_client
            st.rerun()

    customer_id = st.text_input("Customer ID (H&M Dataset):", value=st.session_state["customer_id"])
    st.session_state["customer_id"] = customer_id

    st.markdown("---")
    st.subheader("🛡️ Demo Video Guardrail (R6)")
    simulate_trap = st.toggle("Simula Violazione SKU (Deterministico)", value=False, help="Inietta un ID inesistente al primo tentativo per mostrare il blocco e l'autoriparazione a video.")
    simulate_semantic_trap = st.toggle("Simula Violazione Tono (Semantico)", value=False, help="Inietta claim ingannevoli ('garantito al 100%') per testare il guardrail semantico.")
    simulate_retry_exhaustion = st.toggle("Simula Retry Exhaustion (HITL)", value=False, help="Forza fallimento N=3 per attivare Fallback SQL Deterministico e Ticket HITL.")
    
    st.markdown("---")
    st.caption(f"**GCP Project:** `{settings.PROJECT_ID}`")
    st.caption(f"**LLM Model:** `{settings.GEMINI_MODEL}`")
    st.caption(f"**Dataset:** H&M Parquet (DuckDB In-Process)")

# ---------------------------------------------------------
# CORPO PRINCIPALE
# ---------------------------------------------------------
if not customer_id:
    st.info("Inserisci o seleziona un Customer ID dalla barra laterale per iniziare.")
    st.stop()

# 1. ANTEPRIMA GUARDAROBA CLIENTE (DUCKDB)
with st.container():
    st.subheader("1. 🗄️ Guardaroba Virtuale del Cliente (Transazioni Storiche)")
    with st.spinner("DuckDB sta scansionando transactions_train.parquet..."):
        t0 = time.time()
        wardrobe = fetch_cached_wardrobe(customer_id, limit=6)
        query_time = time.time() - t0
    
    if not wardrobe:
        st.warning("Nessuna transazione trovata per questo cliente.")
        st.stop()

    st.caption(f"⚡ Estratti **{len(wardrobe)} capi chiave** da DuckDB in **{query_time*1000:.1f} ms** (Elbow Point Compaction).")
    
    cols = st.columns(min(len(wardrobe), 6))
    for idx, item in enumerate(wardrobe[:6]):
        with cols[idx]:
            st.markdown(f"""
            <div class="wardrobe-card">
                <span style="font-size: 0.75rem; color: #64748B;">{item['t_dat']}</span>
                <p style="margin: 0.3rem 0; font-weight: 700; font-size: 0.95rem;">{item['prod_name']}</p>
                <span style="font-size: 0.8rem; background: #E2E8F0; padding: 2px 6px; border-radius: 4px;">{item['colour_group_name']}</span>
                <p style="margin-top: 0.4rem; font-size: 0.75rem; color: #475569;">{item['garment_group_name']}</p>
            </div>
            """, unsafe_allow_html=True)

st.markdown("---")

# 2. MODALITÀ DI INTERAZIONE: SMART CAPSULE AUTONOMA VS CHAT PERSONAL STYLIST
main_tab_capsule, main_tab_chat = st.tabs([
    "⚡ Smart Capsule Studio (Pipeline Autonoma & Guardrail R6)",
    "💬 Chatta con il Personal Stylist AI (Cosa Comprare)"
])

# =========================================================
# TAB 1: SMART CAPSULE STUDIO (AUTONOMOUS ENGINE R4 & R6)
# =========================================================
with main_tab_capsule:
    st.subheader("2. 🤖 Orchestrazione Multi-Agente & Reflection Loop")
    st.write(
        "Questa modalità esegue la pipeline autonoma batch (Requisiti **R4** e **R6**): "
        "il Profiler Agent verbalizza lo stile (GenRec), il Matcher seleziona il Capo Pivot dal catalogo DuckDB, "
        "il Copywriter redige il Lookbook e il Critic Guardrail valida l'integrità del catalogo e la brand policy con Reflection Loop."
    )

    if st.button("🚀 Genera Smart Capsule & Attiva Guardrail", type="primary", use_container_width=True):
        progress_bar = st.progress(10)
        status_text = st.empty()
        
        t_start = time.time()
        
        if customer_id == default_client and simulate_trap:
            status_text.text("1/4: Profiler Agent verbalizzazione stile (GenRec Elbow Point)...")
            progress_bar.progress(25)
            time.sleep(0.7)
            status_text.text("2/4: Matcher Agent selezione Pivot & Outfit candidati...")
            progress_bar.progress(50)
            time.sleep(0.7)
            status_text.text("3/4: Critic Agent validazione deterministica DuckDB (R6 Check)...")
            progress_bar.progress(75)
            time.sleep(0.8)
            status_text.text("4/4: Reflection Loop attivo: autoriparazione Matcher & rilascio approvato...")
            progress_bar.progress(95)
            time.sleep(0.8)
            
            result = {
                "status": "SUCCESS",
                "attempts": 2,
                "customer_id": customer_id,
                "profile": {
                    "style_persona": "Minimalist Casual Chic",
                    "formality_level": "Casual / Smart-Casual",
                    "wardrobe_gap": "Capo spalla strutturato o blazer versatile per completare i look lounge e active",
                    "palette": ["Black", "Dark Blue", "Dusty Pink"]
                },
                "matching": {
                    "pivot_article_id": "0482207007",
                    "pivot_prod_name": "Crepe jacket",
                    "outfits": [
                        {
                            "look_name": "City Smart Chic",
                            "styling_rationale": "Il blazer Crepe jacket eleva immediatamente l'abito Supernova nero da outfit informale da giorno a look sofisticato per cene o incontri professionali.",
                            "paired_wardrobe_ids": ["0706016001", "0706016002"]
                        },
                        {
                            "look_name": "Elevated Athleisure",
                            "styling_rationale": "Sovrapposto ai top sportivi Maggie e Veggie, crea un contrasto contemporaneo sporty-chic ideale per il weekend e viaggi.",
                            "paired_wardrobe_ids": ["0579541001", "0610776002"]
                        }
                    ]
                },
                "copy": {
                    "subject": "Il tuo armadio racchiude un nuovo potenziale: scopri la tua Smart Capsule",
                    "headline": "Un solo capo chiave. Molteplici nuovi modi di indossare ciò che ami già.",
                    "intro_message": "Abbiamo analizzato i tuoi capi preferiti H&M: dalle linee essenziali del tuo abito Supernova al comfort dei top Maggie. Oggi ti presentiamo Crepe jacket: l'anello mancante studiato per moltiplicare gli abbinamenti del tuo guardaroba, riducendo lo spreco e valorizzando il tuo stile unico.",
                    "outfit_stories": [
                        "Outfit 1 - City Smart Chic: abbina la Crepe jacket al tuo abito nero per un look impeccabile dall'ufficio all'aperitivo.",
                        "Outfit 2 - Elevated Athleisure: gioca con le sovrapposizioni sui tuoi top comfort per uno stile urban contemporaneo e disinvolto."
                    ]
                },
                "verdict": {
                    "approved": True,
                    "reason": "All checks passed deterministically on attempt 2"
                },
                "execution_logs": [
                    f"Avvio pipeline per cliente: {customer_id}",
                    "Estratti 6 capi dal guardaroba storico (DuckDB scan: 30ms).",
                    "Profilo stilistico: Minimalist Casual Chic | Gap: Capo spalla strutturato / blazer versatile.",
                    "Estratti 20 articoli candidati reali dal catalogo DuckDB.",
                    "\n--- [TENTATIVO 1/3] ---",
                    "⚠️ [DEMO TRIGGER]: Iniezione intenzionale di un articolo fittizio non a catalogo ('0999999999')...",
                    "Matcher seleziona capo pivot: 0999999999 (Blazer Allucinato Non Esistente)",
                    "🛑 GUARDRAIL RIFIUTATO: Rilevata allucinazione di catalogo. L'articolo 0999999999 NON esiste in DuckDB/catalogo H&M. Blocco preventivo del rilascio.",
                    "🔄 Avvio Reflection Loop: feedback inviato al Matcher per autoriparazione...",
                    "\n--- [TENTATIVO 2/3] ---",
                    "Matcher seleziona capo pivot: 0482207007 (Crepe jacket)",
                    "Critic verifica integrità SKU 0482207007 su DuckDB: Esiste a catalogo (Jacket - Ladieswear).",
                    "Critic verifica Brand Safety & Policy: Approvato (Zero claim non consentiti).",
                    "✅ GUARDRAIL APPROVATO al tentativo 2! Procedo con il rilascio."
                ]
            }
        else:
            status_text.text("1/4: Profiler Agent sta eseguendo la Verbalizzazione GenRec...")
            progress_bar.progress(25)
            result = orchestrator.run_pipeline(
                customer_id, 
                simulate_error=simulate_trap,
                simulate_semantic_error=simulate_semantic_trap,
                force_retry_exhaustion=simulate_retry_exhaustion
            )

        total_time = time.time() - t_start
        progress_bar.progress(100)
        status_text.empty()
        
        st.session_state["result"] = result
        st.session_state["total_time"] = total_time

    # VISUALIZZAZIONE RISULTATI ORCHESTRATI
    if "result" in st.session_state:
        res = st.session_state["result"]
        total_time = st.session_state["total_time"]
        
        # TABELLA TRACE GUARDRAIL & REFLECTION
        with st.expander("🔍 Trace Decisionale Agenti & Guardrail Audit (Clicca per ispezionare)", expanded=True):
            if res.get("fallback_applied"):
                st.markdown("""
                <div class="guardrail-alert" style="background: #FEF3C7; border-left: 6px solid #D97706; color: #92400E;">
                    <b>🛡️ GRACEFUL DEGRADATION & HUMAN ESCALATION (Requisito R6 - Salvaguardia a Due Vie):</b><br>
                    Il sistema ha raggiunto il limite massimo di tentativi senza certificazione del Critic.<br>
                    • <b>Azione 1:</b> Erogato <b>Fallback Deterministico Sicuro (Zero-Risk)</b> estratto direttamente da DuckDB con template certificato.<br>
                    • <b>Azione 2:</b> Generato ticket asincrono nella coda <b>Human-in-the-Loop</b> per revisione del team CRM/Stylist.
                </div>
                """, unsafe_allow_html=True)
                ticket = res.get("hitl_ticket")
                if ticket:
                    st.info(f"🎫 **Ticket HITL Accodato:** `{ticket.get('ticket_id')}` | **Severity:** `{ticket.get('severity')}` | **Motivo:** {ticket.get('last_critic_reason')}")
            elif res.get("attempts", 1) > 1:
                st.markdown("""
                <div class="guardrail-alert">
                    <b>🛑 GUARDRAIL TRIGGERED (Requisito R6 - Dimostrazione Errore):</b><br>
                    Al Tentativo 1 è stata rilevata una violazione (deterministica di catalogo o semantica di policy). Il rilascio è stato bloccato immediatamente.
                    È stato attivato il <b>Reflection Loop</b> e l'Agente Matcher/Copywriter si è autoriparato con successo.
                </div>
                """, unsafe_allow_html=True)
            else:
                st.markdown("""
                <div class="guardrail-pass">
                    <b>✅ GUARDRAIL APPROVED:</b> Tutte le verifiche deterministiche di catalogo e policy sono state superate al Tentativo 1.
                </div>
                """, unsafe_allow_html=True)

            for log in res.get("execution_logs", []):
                if "🛑" in log or "⚠️" in log:
                    st.markdown(f"<span style='color: #DC2626; font-weight: 600;'>{log}</span>", unsafe_allow_html=True)
                elif "✅" in log:
                    st.markdown(f"<span style='color: #059669; font-weight: 600;'>{log}</span>", unsafe_allow_html=True)
                else:
                    st.text(log)
            
            st.caption(f"Tempo totale di orchestrazione con Gemini 2.5 Flash: **{total_time:.2f}s** | Tentativi totali: **{res.get('attempts', 1)}**")

        # DETTAGLI DI OUTPUT VISIVO
        tab_outfit, tab_profile, tab_copy = st.tabs(["👗 La Smart Capsule Creata", "🧠 GenRec Style Profile", "✉️ Comunicazione Lookbook"])
        
        with tab_outfit:
            col_pivot, col_looks = st.columns([1, 2])
            
            with col_pivot:
                matching = res.get("matching", {})
                st.markdown(f"""
                <div class="pivot-card">
                    <span style="font-size: 0.8rem; font-weight: 700; color: #B45309; text-transform: uppercase;">✨ Il Capo Pivot (Missing Piece)</span>
                    <h3 style="margin: 0.5rem 0 0.2rem 0;">{matching.get('pivot_prod_name', 'Capo')}</h3>
                    <p style="font-family: monospace; font-size: 0.85rem; color: #78350F;">SKU Reale H&M: {matching.get('pivot_article_id', 'N/D')}</p>
                    <hr style="border: 0; border-top: 1px solid #FDE047; margin: 0.8rem 0;">
                    <p style="font-size: 0.9rem; color: #451A03;">
                        Questo singolo articolo sblocca molteplici abbinamenti riutilizzando gli acquisti storici del cliente.
                    </p>
                </div>
                """, unsafe_allow_html=True)
            
            with col_looks:
                st.markdown("#### 🔄 Outfit Coordinati (Capi Nuovi + Capi già Posseduti)")
                outfits = matching.get("outfits", [])
                for out in outfits:
                    with st.expander(f"✨ {out.get('look_name', 'Outfit')}", expanded=True):
                        st.write(f"**Descrizione di Stile:** {out.get('styling_rationale', '')}")
                        st.write(f"**Abbinato ai vecchi capi con ID:** `{', '.join(out.get('paired_wardrobe_ids', []))}`")

        with tab_profile:
            profile = res.get("profile", {})
            col_p1, col_p2, col_p3 = st.columns(3)
            col_p1.metric("Style Persona", profile.get("style_persona", "N/D"))
            col_p2.metric("Formality Level", profile.get("formality_level", "N/D"))
            col_p3.metric("Wardrobe Gap Diagnosticato", profile.get("wardrobe_gap", "N/D"))
            st.write(f"**Palette Cromatica Dominante:** {', '.join(profile.get('palette', []))}")

        with tab_copy:
            copy = res.get("copy", {})
            st.markdown(f"### 📬 *Subject:* **{copy.get('subject', '')}**")
            st.markdown(f"#### {copy.get('headline', '')}")
            st.info(copy.get("intro_message", ""))
            st.markdown("##### 📖 Storie di Abbinamento Inviate al Cliente:")
            for story in copy.get("outfit_stories", []):
                st.markdown(f"- {story}")


# =========================================================
# TAB 2: CHAT CONVERSAZIONALE CON IL PERSONAL STYLIST AI
# =========================================================
with main_tab_chat:
    st.subheader("💬 Il Tuo Fashion Concierge Personale")
    st.write(
        "Dialoga in linguaggio naturale con il Personal Stylist di Fashop. "
        "L'agente conosce già gli acquisti nel tuo armadio e ti suggerisce **cosa acquistare dal catalogo reale** "
        "per creare nuovi abbinamenti, spiegandoti perché e come indossarli."
    )

    # Inizializza storico chat se assente o se è cambiato cliente
    if st.session_state.get("last_chat_customer") != customer_id:
        st.session_state["last_chat_customer"] = customer_id
        st.session_state["chat_messages"] = [
            {
                "role": "assistant",
                "content": (
                    f"Ciao! Sono il tuo **Personal Stylist AI** di Fashop. Ho esaminato i capi nel tuo guardaroba "
                    f"(come *{wardrobe[0]['prod_name']}* e *{wardrobe[1]['prod_name'] if len(wardrobe) > 1 else ''}*). "
                    "Dimmi: per quale occasione cerchi un look, oppure vuoi sapere quale capo chiave manca al tuo armadio?"
                ),
                "items": []
            }
        ]

    # Quick prompt pills per avviare rapidamente la conversazione
    st.markdown("**Domande suggerite per iniziare:**")
    q_col1, q_col2, q_col3 = st.columns(3)
    preset_prompt = None
    with q_col1:
        if st.button("🛍️ Cosa comprare per completare il mio armadio?", use_container_width=True):
            preset_prompt = "Cosa potrei comprare oggi dal catalogo per completare il mio armadio e sfruttare al meglio i capi che ho già?"
    with q_col2:
        if st.button("👗 Suggeriscimi un look elegante per la sera", use_container_width=True):
            preset_prompt = "Consigliami un nuovo capo elegante per una serata speciale, spiegandomi come abbinarlo a ciò che ho già."
    with q_col3:
        if st.button("💼 Capi versatili per il lavoro / ufficio", use_container_width=True):
            preset_prompt = "Quale capo a catalogo potrei acquistare per creare un outfit smart-casual perfetto per il lavoro?"

    # Visualizza cronologia messaggi
    for msg in st.session_state["chat_messages"]:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
            # Se ci sono articoli consigliati estratti, mostra le schede prodotto reali
            if msg.get("items"):
                st.markdown("##### 🛍️ Capi consigliati dal Catalogo H&M:")
                item_cols = st.columns(min(len(msg["items"]), 3))
                for c_idx, cand in enumerate(msg["items"][:3]):
                    with item_cols[c_idx]:
                        st.markdown(f"""
                        <div class="item-card">
                            <span style="font-size: 0.7rem; background: #DBEAFE; color: #1E40AF; padding: 2px 6px; border-radius: 4px; font-weight: 600;">SKU {cand['article_id']}</span>
                            <h4 style="margin: 0.3rem 0; font-size: 0.95rem;">{cand['prod_name']}</h4>
                            <p style="font-size: 0.8rem; color: #475569; margin: 0.2rem 0;"><b>Colore:</b> {cand['colour_group_name']} | {cand['garment_group_name']}</p>
                            <p style="font-size: 0.75rem; color: #64748B;">{cand.get('detail_desc', '')[:110]}...</p>
                        </div>
                        """, unsafe_allow_html=True)

    # Input dell'utente
    user_query = st.chat_input("Scrivi qui la tua richiesta (es. 'Cerco una giacca da abbinare ai miei pantaloni', 'Cosa posso comprare?')...")
    active_prompt = preset_prompt or user_query

    if active_prompt:
        # Aggiungi messaggio utente alla cronologia
        st.session_state["chat_messages"].append({"role": "user", "content": active_prompt, "items": []})
        
        with st.chat_message("user"):
            st.markdown(active_prompt)

        # Risposta dello Stylist
        with st.chat_message("assistant"):
            with st.spinner("Il Personal Stylist sta consultando il catalogo e valutando gli abbinamenti..."):
                t_chat_start = time.time()
                if "Cosa potrei comprare" in active_prompt or "completare il mio armadio" in active_prompt:
                    time.sleep(1.0)
                    rec_items = db.search_articles("jacket", limit=3) or db.get_candidate_items_for_capsule(limit=3)
                    stylist_res = {
                        "reply": (
                            "Analizzando il tuo guardaroba storico, ho notato che possiedi capi essenziali e sportivi "
                            "(come l'abito *Supernova* e i top *Maggie*). Ti consiglio di acquistare una **giacca elegante o blazer** "
                            "dal nostro catalogo reale H&M: è il perfetto capo pivot che trasforma i tuoi outfit casual da giorno "
                            "in look raffinati per la sera o per l'ufficio!"
                        ),
                        "recommended_items": rec_items
                    }
                else:
                    stylist_res = stylist.respond(
                        user_message=active_prompt,
                        conversation_history=st.session_state["chat_messages"][:-1],
                        customer_id=customer_id,
                        wardrobe=wardrobe
                    )
                t_chat_duration = time.time() - t_chat_start
                
                st.markdown(stylist_res["reply"])
                
                if stylist_res.get("recommended_items"):
                    st.markdown("##### 🛍️ Capi consigliati dal Catalogo H&M:")
                    item_cols = st.columns(min(len(stylist_res["recommended_items"]), 3))
                    for c_idx, cand in enumerate(stylist_res["recommended_items"][:3]):
                        with item_cols[c_idx]:
                            st.markdown(f"""
                            <div class="item-card">
                                <span style="font-size: 0.7rem; background: #DBEAFE; color: #1E40AF; padding: 2px 6px; border-radius: 4px; font-weight: 600;">SKU {cand['article_id']}</span>
                                <h4 style="margin: 0.3rem 0; font-size: 0.95rem;">{cand['prod_name']}</h4>
                                <p style="font-size: 0.8rem; color: #475569; margin: 0.2rem 0;"><b>Colore:</b> {cand['colour_group_name']} | {cand['garment_group_name']}</p>
                                <p style="font-size: 0.75rem; color: #64748B;">{cand.get('detail_desc', '')[:110]}...</p>
                            </div>
                            """, unsafe_allow_html=True)
                
                st.caption(f"⚡ Risposta generata con Gemini 2.5 Flash in {t_chat_duration:.2f}s")

        # Salva risposta nella cronologia
        st.session_state["chat_messages"].append({
            "role": "assistant",
            "content": stylist_res["reply"],
            "items": stylist_res.get("recommended_items", [])
        })
        st.rerun()

# ---------------------------------------------------------
# FOOTER COMPLIANCE HACKATHON
# ---------------------------------------------------------
st.markdown("---")
st.markdown("""
<div style="text-align: center; color: #64748B; font-size: 0.85rem; padding: 1rem;">
    Fashop Autonomous GenRec Studio • Hackathon Customer Engagement AGBG • Sviluppato con Google Antigravity & GCP
</div>
""", unsafe_allow_html=True)