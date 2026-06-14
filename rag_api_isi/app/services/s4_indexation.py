"""
Service 4 — Indexation / Stockage (doc ISI §3.4)
Stocke les vecteurs et métadonnées dans Qdrant.
Implémentation conforme au §3.4.4 de la documentation.
"""
from functools import lru_cache

from app.models.schemas import ChunkVectorise, ResultatRecherche
from app.core.config import settings


@lru_cache(maxsize=1)
def _client():
    from qdrant_client import QdrantClient
    return QdrantClient(host=settings.QDRANT_HOST, port=settings.QDRANT_PORT)


def creer_collection(dim: int = None):
    """(Re)crée la collection vectorielle avec la distance cosinus."""
    from qdrant_client.models import Distance, VectorParams
    dim = dim or settings.EMBED_DIM
    _client().recreate_collection(
        collection_name=settings.QDRANT_COLLECTION,
        vectors_config=VectorParams(size=dim, distance=Distance.COSINE),
    )


def indexer(chunks: list[ChunkVectorise]) -> int:
    """Insère les chunks vectorisés dans Qdrant. Retourne le nombre indexé."""
    from qdrant_client.models import PointStruct

    champs = ["chunk_id", "id_article", "titre_article", "texte",
              "page_debut", "page_fin", "livre", "chapitre", "tokens"]
    points = []
    for i, c in enumerate(chunks):
        d = c.model_dump()
        points.append(PointStruct(
            id=i,
            vector=c.embedding,
            payload={k: d[k] for k in champs},
        ))
    _client().upsert(collection_name=settings.QDRANT_COLLECTION, points=points)
    return len(points)


def rechercher(vecteur_question: list[float], top_k: int = 4,
               filtre_livre: str = None) -> list[ResultatRecherche]:
    """Recherche les top-k chunks les plus proches (avec filtre optionnel)."""
    from qdrant_client.models import Filter, FieldCondition, MatchValue

    qfilter = None
    if filtre_livre:
        qfilter = Filter(must=[FieldCondition(
            key="livre", match=MatchValue(value=filtre_livre))])

    res = _client().search(
        collection_name=settings.QDRANT_COLLECTION,
        query_vector=vecteur_question,
        limit=top_k,
        with_payload=True,
        query_filter=qfilter,
    )
    sorties = []
    for r in res:
        p = r.payload
        sorties.append(ResultatRecherche(
            score=float(r.score),
            id_article=p["id_article"],
            titre_article=p.get("titre_article"),
            texte=p["texte"],
            page=p["page_debut"],
            livre=p.get("livre"),
            chapitre=p.get("chapitre"),
        ))
    return sorties


def compter() -> int:
    """Nombre de points dans la collection."""
    info = _client().get_collection(settings.QDRANT_COLLECTION)
    return info.points_count
