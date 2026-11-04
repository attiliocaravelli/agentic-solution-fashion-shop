import os
import sys
import time

# Permette l'esecuzione diretta del test dalla root del progetto
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.data_engine import HMDataEngine
from src.config import settings

def main():
    print("=" * 60)
    print("AVVIO TEST FUNZIONALE E BENCHMARK: DUCKDB DATA ENGINE")
    print(f"Target Data Directory: {settings.DATA_DIR}")
    print(f"GCP Project ID:        {settings.PROJECT_ID}")
    print(f"Default Region:        {settings.LOCATION}")
    print("=" * 60)

    # Inizializzazione motore
    start_init = time.time()
    engine = HMDataEngine()
    print(f"[OK] Engine inizializzato in: {time.time() - start_init:.4f}s")

    # 1. Ricerca cliente di test
    print("\n[Step 1] Ricerca customer con storico acquisti (>= 5 transazioni)...")
    t0 = time.time()
    test_customer = engine.get_random_active_customer()
    if not test_customer:
        print("[FAIL] Nessun cliente trovato. Assicurati che transactions_train.parquet sia presente.")
        return
    print(f"[OK] Cliente identificato: {test_customer} (Latenza: {time.time() - t0:.4f}s)")

    # 2. Estrazione del Guardaroba Virtuale (Elbow Point GenRec)
    print("\n[Step 2] Estrazione Guardaroba Virtuale (K=5 capi recenti)...")
    t1 = time.time()
    wardrobe = engine.get_customer_wardrobe(test_customer, limit=5)
    print(f"[OK] Estratti {len(wardrobe)} capi in {time.time() - t1:.4f}s")
    for idx, item in enumerate(wardrobe, 1):
        print(f"   {idx}. [{item['t_dat']}] {item['prod_name']} ({item['colour_group_name']}) - Tipo: {item['product_type_name']}")

    # 3. Estrazione Pool Candidati per il Single-Pass Ranking
    print("\n[Step 3] Estrazione Candidati per Capsula (Ladieswear - Blouses)...")
    t2 = time.time()
    candidates = engine.get_candidate_items_for_capsule(index_group="Ladieswear", target_garment="Blouses", limit=10)
    print(f"[OK] Estratti {len(candidates)} candidati in {time.time() - t2:.4f}s")
    assert len(candidates) > 0, "Errore: nessun candidato restituito dalla query."

    # 4. Verifica Strumento Guardrail (Requisito R6)
    print("\n[Step 4] Test deterministico Guardrail anti-allucinazione...")
    valid_id = wardrobe[0]['article_id']
    fake_id = "0999999999"  # ID fittizio non presente in catalogo

    t3 = time.time()
    is_valid_real = engine.verify_article_exists(valid_id)
    is_fake_rejected = engine.verify_article_exists(fake_id)
    print(f"[OK] Controllo completato in {time.time() - t3:.4f}s")
    print(f"   - Esistenza ID reale ({valid_id}): {is_valid_real} (Atteso: True)")
    print(f"   - Esistenza ID fittizio ({fake_id}): {is_fake_rejected} (Atteso: False)")

    assert is_valid_real is True, "Validazione fallita: l'ID reale deve essere confermato dal Guardrail."
    assert is_fake_rejected is False, "Validazione fallita: l'ID fittizio deve essere respinto dal Guardrail."

    print("\n" + "=" * 60)
    print("TUTTI I TEST DELLO STEP 2 COMPLETATI CON SUCCESSO! ENGINE PRONTO.")
    print("=" * 60)

if __name__ == "__main__":
    main()