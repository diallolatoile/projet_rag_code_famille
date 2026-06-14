"""
API REST du système RAG — Chatbot Juridique Code de la Famille (ISI 2025-2026).
Expose les 6 services en endpoints conformes au §4.2 de la documentation :
  POST /api/extract    POST /api/segment    POST /api/vectorize
  POST /api/index      POST /api/search     POST /api/chat
"""
import json
import os

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.core.config import settings
from app.models.schemas import (
    Article, Chunk, ChunkVectorise, RequeteRecherche, RequeteChat,
    ResultatRecherche, ReponseChat,
)
from app.services import (
    s1_extraction, s2_segmentation, s3_vectorisation,
    s4_indexation, s5_recherche, s6_reponse,
)

app = FastAPI(
    title="RAG Code de la Famille — ISI",
    description="Chatbot juridique expert (Retrieval-Augmented Generation)",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], allow_methods=["*"], allow_headers=["*"],
)


@app.get("/")
def racine():
    return {
        "projet": "RAG Code de la Famille sénégalais — ISI 2025-2026",
        "services": ["extract", "segment", "vectorize", "index", "search", "chat"],
        "doc": "/docs",
    }


# ------------------------------------------------------------------
# Service 1 — POST /api/extract : PDF -> articles JSON
# ------------------------------------------------------------------
@app.post("/api/extract", response_model=list[Article])
def api_extract(file: UploadFile = File(None)):
    """Extrait les articles du PDF. Sans fichier, utilise le PDF par défaut."""
    pdf_path = settings.PDF_PATH
    if file is not None:
        pdf_path = f"data/_upload_{file.filename}"
        with open(pdf_path, "wb") as f:
            f.write(file.file.read())
    if not os.path.exists(pdf_path):
        raise HTTPException(404, f"PDF introuvable : {pdf_path}")
    articles = s1_extraction.extraire_articles(pdf_path)
    # sauvegarde intermédiaire
    with open(settings.ARTICLES_JSON, "w", encoding="utf-8") as f:
        json.dump([a.model_dump() for a in articles], f, ensure_ascii=False, indent=2)
    return articles


# ------------------------------------------------------------------
# Service 2 — POST /api/segment : articles -> chunks
# ------------------------------------------------------------------
@app.post("/api/segment", response_model=list[Chunk])
def api_segment(articles: list[Article] = None):
    """Segmente les articles en chunks. Sans corps, lit le JSON d'extraction."""
    if not articles:
        if not os.path.exists(settings.ARTICLES_JSON):
            raise HTTPException(400, "Aucun article fourni et aucun JSON d'extraction trouvé.")
        with open(settings.ARTICLES_JSON, encoding="utf-8") as f:
            articles = [Article(**a) for a in json.load(f)]
    chunks = s2_segmentation.segmenter(articles)
    with open(settings.CHUNKS_JSON, "w", encoding="utf-8") as f:
        json.dump([c.model_dump() for c in chunks], f, ensure_ascii=False, indent=2)
    return chunks


# ------------------------------------------------------------------
# Service 3 — POST /api/vectorize : chunks -> embeddings
# ------------------------------------------------------------------
@app.post("/api/vectorize")
def api_vectorize(chunks: list[Chunk] = None):
    """Vectorise les chunks. Retourne le nombre traité (les vecteurs sont lourds)."""
    if not chunks:
        if not os.path.exists(settings.CHUNKS_JSON):
            raise HTTPException(400, "Aucun chunk fourni et aucun JSON de chunks trouvé.")
        with open(settings.CHUNKS_JSON, encoding="utf-8") as f:
            chunks = [Chunk(**c) for c in json.load(f)]
    vectorises = s3_vectorisation.vectoriser(chunks)
    # on sauvegarde pour l'indexation
    with open(settings.CHUNKS_JSON.replace(".json", "_vec.json"), "w", encoding="utf-8") as f:
        json.dump([v.model_dump() for v in vectorises], f, ensure_ascii=False)
    return {"vectorises": len(vectorises), "dimension": settings.EMBED_DIM}


# ------------------------------------------------------------------
# Service 4 — POST /api/index : chunks vectorisés -> Qdrant
# ------------------------------------------------------------------
@app.post("/api/index")
def api_index():
    """Crée la collection et indexe les chunks vectorisés dans Qdrant."""
    vec_path = settings.CHUNKS_JSON.replace(".json", "_vec.json")
    if not os.path.exists(vec_path):
        raise HTTPException(400, "Lancez d'abord /api/vectorize.")
    with open(vec_path, encoding="utf-8") as f:
        vectorises = [ChunkVectorise(**v) for v in json.load(f)]
    s4_indexation.creer_collection(settings.EMBED_DIM)
    n = s4_indexation.indexer(vectorises)
    return {"indexes": n, "collection": settings.QDRANT_COLLECTION}


# ------------------------------------------------------------------
# Service 5 — POST /api/search : question -> top-K articles
# ------------------------------------------------------------------
@app.post("/api/search", response_model=list[ResultatRecherche])
def api_search(req: RequeteRecherche):
    return s5_recherche.rechercher(req.question, top_k=req.top_k, filtre_livre=req.filtre_livre)


# ------------------------------------------------------------------
# Service 6 — POST /api/chat : question -> réponse + sources
# ------------------------------------------------------------------
@app.post("/api/chat", response_model=ReponseChat)
def api_chat(req: RequeteChat):
    return s6_reponse.repondre(req.question, top_k=req.top_k)


# ------------------------------------------------------------------
# Pipeline complet (commodité : extract -> segment -> vectorize -> index)
# ------------------------------------------------------------------
@app.post("/api/ingest")
def api_ingest():
    """Lance tout le pipeline d'ingestion en une fois."""
    articles = s1_extraction.extraire_articles()
    chunks = s2_segmentation.segmenter(articles)
    vectorises = s3_vectorisation.vectoriser(chunks)
    s4_indexation.creer_collection(settings.EMBED_DIM)
    n = s4_indexation.indexer(vectorises)
    return {"articles": len(articles), "chunks": len(chunks), "indexes": n}


# Frontend statique (interface chatbot)
if os.path.isdir("frontend"):
    app.mount("/app", StaticFiles(directory="frontend", html=True), name="frontend")
