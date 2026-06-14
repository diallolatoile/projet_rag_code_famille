"""
Service 5 — Recherche / Retrieval (doc ISI §3.5)
Reçoit une question, l'encode avec le MÊME modèle d'embedding (cohérence
obligatoire, §3.5.2), interroge Qdrant et retourne les top-K articles
pertinents avec leur score et leurs métadonnées.
"""
from app.models.schemas import ResultatRecherche
from app.services import s3_vectorisation, s4_indexation
from app.core.config import settings


def rechercher(question: str, top_k: int = None,
               filtre_livre: str = None) -> list[ResultatRecherche]:
    top_k = top_k or settings.DEFAULT_TOP_K
    # 1) Encodage de la question (préfixe 'query:' pour e5)
    vecteur = s3_vectorisation.vectoriser_question(question)
    # 2) Recherche par similarité cosinus dans Qdrant
    return s4_indexation.rechercher(vecteur, top_k=top_k, filtre_livre=filtre_livre)
