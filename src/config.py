import os
from dotenv import load_dotenv

# Carica eventuali variabili dal file .env se presente
load_dotenv()

class Settings:
    PROJECT_ID: str = os.getenv("GCP_PROJECT_ID", "qwiklabs-gcp-01-11c2bfff0128")
    LOCATION: str = os.getenv("GCP_LOCATION", "us-central1")
    ZONE: str = os.getenv("GCP_ZONE", "us-central1-b")
    GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
    GCS_BUCKET_NAME: str = os.getenv("GCS_BUCKET_NAME", "fashop-data-us-central1-11c2bfff")
    
    # Rilevamento automatico: se /mnt/data esiste (Cloud Run con GCS FUSE), usa quello
    DATA_DIR: str = os.getenv(
        "DATA_DIR", 
        "/mnt/data" if os.path.exists("/mnt/data/articles.parquet") else "./data"
    )

settings = Settings()