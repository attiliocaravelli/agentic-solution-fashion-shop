FROM python:3.11-slim

# Disabilita il buffering dell'output per i log realtime di Cloud Run
ENV PYTHONUNBUFFERED=1
ENV PORT=8080

WORKDIR /app

# Dipendenze di sistema minime
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Installazione librerie Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copia dell'intero repository applicativo
COPY . .

EXPOSE 8080

# Avvio dell'interfaccia Streamlit ottimizzata per Cloud Run
CMD ["streamlit", "run", "app_ui.py", "--server.port=8080", "--server.address=0.0.0.0", "--server.headless=true", "--server.enableCORS=false"]