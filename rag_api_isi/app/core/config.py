"""
Configuration centrale du système RAG — Chatbot Juridique Code de la Famille.
Projet ISI 2025-2026. Valeurs surchargeables par variables d'environnement.
"""
import os


class Settings:
    # --- Document source ---
    PDF_PATH = os.getenv("PDF_PATH", "data/CODE-DE-LA-FAMILLE.pdf")
    PDF_PUBLIC_URL = os.getenv("PDF_PUBLIC_URL", "http://localhost:8080/CODE-DE-LA-FAMILLE.pdf")

    # --- Service 3 : Vectorisation (modèle d'embedding français, doc ISI) ---
    EMBED_MODEL = os.getenv("EMBED_MODEL", "intfloat/multilingual-e5-large")
    EMBED_DIM = int(os.getenv("EMBED_DIM", "1024"))   # e5-large = 1024 dimensions

    # --- Service 4 : Indexation (Qdrant, doc ISI) ---
    QDRANT_HOST = os.getenv("QDRANT_HOST", "localhost")
    QDRANT_PORT = int(os.getenv("QDRANT_PORT", "6333"))
    QDRANT_COLLECTION = os.getenv("QDRANT_COLLECTION", "code_famille_senegal")

    # --- Service 6 : Génération (LLM) ---
    # Provider au choix (doc ISI §4.1) : "ollama" (local), "mistral", "openai".
    LLM_PROVIDER = os.getenv("LLM_PROVIDER", "ollama")
    OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
    LLM_MODEL = os.getenv("LLM_MODEL", "llama3.2")
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
    OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    MISTRAL_API_KEY = os.getenv("MISTRAL_API_KEY", "")
    MISTRAL_MODEL = os.getenv("MISTRAL_MODEL", "mistral-large-latest")

    # --- Service 2 : Segmentation ---
    CHUNK_MAX_TOKENS = int(os.getenv("CHUNK_MAX_TOKENS", "550"))   # doc ISI : 400-600
    CHUNK_OVERLAP_TOKENS = int(os.getenv("CHUNK_OVERLAP_TOKENS", "80"))  # doc ISI : 50-100

    # --- Service 5 : Recherche ---
    DEFAULT_TOP_K = int(os.getenv("DEFAULT_TOP_K", "4"))   # doc ISI : 3-5

    # --- Fichiers intermédiaires du pipeline d'ingestion ---
    ARTICLES_JSON = os.getenv("ARTICLES_JSON", "data/articles_extraits.json")
    CHUNKS_JSON = os.getenv("CHUNKS_JSON", "data/chunks.json")


settings = Settings()
