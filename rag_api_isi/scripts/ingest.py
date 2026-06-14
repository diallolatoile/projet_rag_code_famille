"""
Script d'ingestion : exécute le pipeline offline complet en ligne de commande.
  Service 1 (extraction) -> 2 (segmentation) -> 3 (vectorisation) -> 4 (indexation)

Usage :
  python -m scripts.ingest
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services import s1_extraction, s2_segmentation, s3_vectorisation, s4_indexation
from app.core.config import settings


def main():
    print("== Service 1 : Extraction ==")
    articles = s1_extraction.extraire_articles()
    print(f"   {len(articles)} articles extraits")

    print("== Service 2 : Segmentation ==")
    chunks = s2_segmentation.segmenter(articles)
    print(f"   {len(chunks)} chunks produits")

    print("== Service 3 : Vectorisation ==")
    print(f"   modèle : {settings.EMBED_MODEL} ({settings.EMBED_DIM} dim)")
    vectorises = s3_vectorisation.vectoriser(chunks)
    print(f"   {len(vectorises)} chunks vectorisés")

    print("== Service 4 : Indexation (Qdrant) ==")
    s4_indexation.creer_collection(settings.EMBED_DIM)
    n = s4_indexation.indexer(vectorises)
    print(f"   {n} points indexés dans '{settings.QDRANT_COLLECTION}'")

    print("\nIngestion terminée. L'API /api/chat est prête à répondre.")


if __name__ == "__main__":
    main()
