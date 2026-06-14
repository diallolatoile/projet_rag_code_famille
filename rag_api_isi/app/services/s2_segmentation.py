"""
Service 2 — Segmentation (doc ISI §3.2)
Découpe les articles en chunks. Stratégie de la doc :
- niveau article : 1 article = 1 chunk principal (cas courant) ;
- niveau sous-section : pour les articles longs (> seuil), découpage en
  alinéas avec chevauchement (overlap) pour préserver le contexte ;
- chunk enrichi : chaque chunk porte les métadonnées de son article parent.
"""
import re

from app.models.schemas import Article, Chunk
from app.core.config import settings


def _compter_tokens(texte: str) -> int:
    """Estimation simple du nombre de tokens (~mots + ponctuation)."""
    return len(re.findall(r"\w+|[^\w\s]", texte, re.UNICODE))


def _decouper_en_alineas(texte: str, max_tokens: int, overlap: int) -> list[str]:
    """Découpe un texte long en segments ~max_tokens avec chevauchement."""
    phrases = re.split(r"(?<=[.!?])\s+", texte)
    segments, courant, courant_tok = [], [], 0
    for ph in phrases:
        t = _compter_tokens(ph)
        if courant_tok + t > max_tokens and courant:
            segments.append(" ".join(courant))
            # chevauchement : on garde la fin du segment précédent
            recouvre, rtok = [], 0
            for p in reversed(courant):
                rtok += _compter_tokens(p)
                recouvre.insert(0, p)
                if rtok >= overlap:
                    break
            courant, courant_tok = recouvre[:], rtok
        courant.append(ph)
        courant_tok += t
    if courant:
        segments.append(" ".join(courant))
    return segments


def segmenter(articles: list[Article]) -> list[Chunk]:
    """Transforme une liste d'articles en chunks conformes à la doc ISI."""
    max_tok = settings.CHUNK_MAX_TOKENS
    overlap = settings.CHUNK_OVERLAP_TOKENS
    chunks: list[Chunk] = []

    for art in articles:
        texte_complet = art.texte.strip()
        # On préfixe le numéro + titre pour enrichir le contexte d'embedding
        prefixe = f"Article {art.id_article}"
        if art.titre_article:
            prefixe += f" — {art.titre_article}"
        contenu = f"{prefixe}. {texte_complet}" if texte_complet else prefixe

        nb_tok = _compter_tokens(contenu)

        if nb_tok <= max_tok:
            # cas courant : 1 article = 1 chunk
            chunks.append(Chunk(
                chunk_id=f"art_{art.id_article}_chunk_1",
                id_article=art.id_article,
                titre_article=art.titre_article,
                texte=contenu,
                page_debut=art.page_debut,
                page_fin=art.page_fin,
                livre=art.livre,
                chapitre=art.chapitre,
                tokens=nb_tok,
            ))
        else:
            # article long : découpage en sous-sections avec overlap
            segments = _decouper_en_alineas(texte_complet, max_tok, overlap)
            for i, seg in enumerate(segments, 1):
                texte_seg = f"{prefixe} (partie {i}). {seg}"
                chunks.append(Chunk(
                    chunk_id=f"art_{art.id_article}_chunk_{i}",
                    id_article=art.id_article,
                    titre_article=art.titre_article,
                    texte=texte_seg,
                    page_debut=art.page_debut,
                    page_fin=art.page_fin,
                    livre=art.livre,
                    chapitre=art.chapitre,
                    tokens=_compter_tokens(texte_seg),
                ))
    return chunks
