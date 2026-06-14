"""
Service 3 — Vectorisation (doc ISI §3.3)
Transforme chaque chunk en vecteur dense via un modèle d'embedding français
(multilingual-e5-large). Implémentation inspirée du §3.3.4 de la doc.

Note e5 : le modèle attend des préfixes "query:" et "passage:" pour
distinguer requêtes et documents. On respecte cette convention.
"""
from functools import lru_cache

from app.models.schemas import Chunk, ChunkVectorise
from app.core.config import settings


@lru_cache(maxsize=1)
def _get_model():
    """Charge le modèle une seule fois (coûteux). Importé paresseusement."""
    from sentence_transformers import SentenceTransformer
    return SentenceTransformer(settings.EMBED_MODEL)


def vectoriser_textes(textes: list[str], est_requete: bool = False) -> list[list[float]]:
    """Encode une liste de textes. est_requete=True pour une question."""
    prefixe = "query: " if est_requete else "passage: "
    model = _get_model()
    vecteurs = model.encode(
        [prefixe + t for t in textes],
        batch_size=32,
        show_progress_bar=False,
        normalize_embeddings=True,   # utile pour la similarité cosinus
    )
    return [v.tolist() for v in vecteurs]


def vectoriser(chunks: list[Chunk]) -> list[ChunkVectorise]:
    """Vectorise une liste de chunks (documents)."""
    textes = [c.texte for c in chunks]
    embeddings = vectoriser_textes(textes, est_requete=False)
    resultat = []
    for chunk, vec in zip(chunks, embeddings):
        resultat.append(ChunkVectorise(**chunk.model_dump(), embedding=vec))
    return resultat


def vectoriser_question(question: str) -> list[float]:
    """Vectorise une question (avec le préfixe 'query:' attendu par e5)."""
    return vectoriser_textes([question], est_requete=True)[0]
