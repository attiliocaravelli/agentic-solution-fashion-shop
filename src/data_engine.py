import os
import duckdb
from typing import List, Dict, Any, Optional
from src.config import settings

class HMDataEngine:
    """
    Data Access Layer vettorizzato basato su DuckDB in-process.
    Elabora i 31.7M di record di H&M a zero costo di query e latenza < 40ms.
    """

    def __init__(self, data_dir: Optional[str] = None):
        self.data_dir = data_dir or settings.DATA_DIR
        self.articles_path = os.path.join(self.data_dir, "articles.parquet")
        self.transactions_path = os.path.join(self.data_dir, "transactions_train.parquet")
        self.customers_path = os.path.join(self.data_dir, "customers.parquet")
        
        # Connessione in-memory a DuckDB (istanza locale per processo)
        self.con = duckdb.connect(database=":memory:")
        self._verify_dataset_availability()

    def _verify_dataset_availability(self):
        """Verifica la disponibilità dei file sorgente nel filesystem."""
        missing = []
        for path in [self.articles_path, self.transactions_path, self.customers_path]:
            if not os.path.exists(path):
                missing.append(path)
        if missing:
            print(f"[DATA ENGINE WARNING] File mancanti nel path '{self.data_dir}': {missing}")

    def get_customer_metadata(self, customer_id: str) -> Optional[Dict[str, Any]]:
        """Recupera il record anagrafico da customers.parquet."""
        query = f"""
        SELECT customer_id, FN, Active, club_member_status, fashion_news_frequency, age
        FROM '{self.customers_path}'
        WHERE customer_id = '{customer_id}'
        LIMIT 1
        """
        df = self.con.execute(query).df()
        if df.empty:
            return None
        return df.to_dict(orient="records")[0]

    def get_customer_wardrobe(self, customer_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Estrae il 'Guardaroba Virtuale' dagli acquisti storici.
        Implementa l'euristica GenRec (Elbow point a K=10) per filtrare
        solo i capi rilevanti e ottimizzare il token budget dell'LLM.
        """
        query = f"""
        SELECT 
            t.t_dat,
            t.article_id,
            ROUND(t.price, 4) AS price,
            a.prod_name,
            a.product_type_name,
            a.product_group_name,
            a.graphical_appearance_name,
            a.colour_group_name,
            a.perceived_colour_value_name,
            a.index_group_name,
            a.garment_group_name,
            a.detail_desc
        FROM '{self.transactions_path}' t
        JOIN '{self.articles_path}' a ON t.article_id = a.article_id
        WHERE t.customer_id = '{customer_id}'
        ORDER BY t.t_dat DESC
        LIMIT {limit}
        """
        df = self.con.execute(query).df()
        return df.to_dict(orient="records")

    def get_candidate_items_for_capsule(
        self, 
        index_group: str = "Ladieswear", 
        target_garment: str = "Blouses", 
        limit: int = 25
    ) -> List[Dict[str, Any]]:
        """
        Estrae dal catalogo un pool di articoli reali e attivi.
        Fornito all'agente per eseguire il Single-Pass Ranking (prefill-only),
        prevenendo la generazione allucinata di codici articolo inesistenti.
        """
        query = f"""
        SELECT 
            article_id,
            prod_name,
            product_type_name,
            product_group_name,
            colour_group_name,
            index_group_name,
            garment_group_name,
            detail_desc
        FROM '{self.articles_path}'
        WHERE index_group_name LIKE '%{index_group}%'
          AND garment_group_name LIKE '%{target_garment}%'
          AND detail_desc IS NOT NULL
        LIMIT {limit}
        """
        df = self.con.execute(query).df()
        return df.to_dict(orient="records")

    def search_articles(
        self, 
        query_text: str = "", 
        limit: int = 15
    ) -> List[Dict[str, Any]]:
        """
        Ricerca rapida su articles.parquet per la chat con il Personal Stylist.
        Consente all'assistente di recuperare capi pertinenti richiesti dall'utente in linguaggio naturale.
        """
        conditions = ["detail_desc IS NOT NULL"]
        if query_text.strip():
            stopwords = {"vorrei", "cosa", "posso", "comprare", "abbinare", "consigliami", "cerco", "delle", "degli", "della", "dello", "un", "una", "uno", "per", "con", "il", "lo", "la", "i", "gli", "le", "del"}
            words = [w.strip().replace("'", "").replace('"', '') for w in query_text.lower().split() if len(w.strip()) > 2 and w.lower() not in stopwords]
            if words:
                subconds = [f"(prod_name ILIKE '%{w}%' OR product_type_name ILIKE '%{w}%' OR garment_group_name ILIKE '%{w}%' OR colour_group_name ILIKE '%{w}%' OR detail_desc ILIKE '%{w}%')" for w in words[:4]]
                conditions.append(f"({' OR '.join(subconds)})")
        
        where_clause = " AND ".join(conditions)
        query = f"""
        SELECT 
            article_id,
            prod_name,
            product_type_name,
            product_group_name,
            colour_group_name,
            index_group_name,
            garment_group_name,
            detail_desc
        FROM '{self.articles_path}'
        WHERE {where_clause}
        LIMIT {limit}
        """
        try:
            df = self.con.execute(query).df()
            if df.empty and query_text.strip():
                return self.get_candidate_items_for_capsule(limit=limit)
            return df.to_dict(orient="records")
        except Exception:
            return self.get_candidate_items_for_capsule(limit=limit)

    def verify_article_exists(self, article_id: str) -> bool:
        """
        Strumento deterministico per il Guardrail di Safety (Requisito R6):
        Controlla in tempo costante se un article_id esiste realmente nel catalogo H&M.
        """
        clean_id = str(article_id).zfill(10)
        query = f"""
        SELECT COUNT(*) 
        FROM '{self.articles_path}' 
        WHERE article_id = '{clean_id}'
        """
        count = self.con.execute(query).fetchone()[0]
        return count > 0

    def get_deterministic_fallback_item(
        self, 
        index_group: str = "Ladieswear", 
        gender: Optional[str] = None,
        palette: Optional[List[str]] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Fallback Deterministico Sicuro (Zero-Risk):
        Recupera un articolo di catalogo garantito, abbinabile per palette e categoria,
        eseguendo una query SQL pura senza allucinazioni da LLM.
        """
        target_group = gender or index_group
        color_filter = ""
        if palette:
            colors = [p.replace("'", "").strip() for p in palette if p.strip()]
            if colors:
                subconds = [f"colour_group_name ILIKE '%{c}%'" for c in colors[:3]]
                color_filter = f"AND ({' OR '.join(subconds)})"

        query = f"""
        SELECT 
            article_id,
            prod_name,
            product_type_name,
            product_group_name,
            colour_group_name,
            index_group_name,
            garment_group_name,
            detail_desc
        FROM '{self.articles_path}'
        WHERE index_group_name LIKE '%{target_group}%'
          AND detail_desc IS NOT NULL
          {color_filter}
        ORDER BY article_id ASC
        LIMIT 1
        """
        try:
            df = self.con.execute(query).df()
            if df.empty:
                query_fallback = f"""
                SELECT 
                    article_id,
                    prod_name,
                    product_type_name,
                    product_group_name,
                    colour_group_name,
                    index_group_name,
                    garment_group_name,
                    detail_desc
                FROM '{self.articles_path}'
                WHERE index_group_name LIKE '%{target_group}%'
                  AND detail_desc IS NOT NULL
                LIMIT 1
                """
                df = self.con.execute(query_fallback).df()
            return df.to_dict(orient="records")[0] if not df.empty else None
        except Exception:
            return None

    def get_random_active_customer(self) -> str:
        """Utility per le demo: restituisce rapidamente un customer_id con acquisti documentati."""
        query = f"""
        SELECT customer_id
        FROM '{self.transactions_path}'
        GROUP BY customer_id
        HAVING COUNT(*) >= 5
        LIMIT 1
        """
        res = self.con.execute(query).fetchone()
        return res[0] if res else ""