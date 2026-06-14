"""
Service 6 — Réponse / Génération augmentée (doc ISI §3.6)
Synthétise une réponse juridique sourcée à partir de la question et des
articles retrouvés. Prompt système conforme au §3.6.3 de la doc.
Sources cliquables via #page=N (§3.6.4).
"""
import json
import urllib.request

from app.models.schemas import ResultatRecherche, SourceCitee, ReponseChat
from app.services import s5_recherche
from app.core.config import settings


# Prompt système (doc ISI §3.6.3)
SYSTEM_PROMPT = (
    "Vous êtes un expert juridique spécialisé dans le Code de la Famille "
    "sénégalais. Répondez UNIQUEMENT sur la base des articles fournis "
    "ci-dessous. Citez systématiquement chaque article utilisé avec son "
    "numéro et son titre. Si la réponse ne se trouve pas dans les articles "
    "fournis, dites-le explicitement. Structurez votre réponse de façon "
    "claire et pédagogique, pour un citoyen non juriste."
)


def _construire_contexte(resultats: list[ResultatRecherche]) -> str:
    blocs = []
    for r in resultats:
        titre = r.titre_article or ""
        blocs.append(
            f"[Article {r.id_article} — {titre} (page {r.page})]\n{r.texte}")
    return "\n\n".join(blocs)


def _appeler_ollama(prompt: str) -> str:
    payload = json.dumps({
        "model": settings.LLM_MODEL,
        "prompt": prompt,
        "stream": False,
    }).encode("utf-8")
    req = urllib.request.Request(
        f"{settings.OLLAMA_URL}/api/generate",
        data=payload, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=600) as resp:
        return json.loads(resp.read())["response"].strip()


def _appeler_openai(prompt: str) -> str:
    from openai import OpenAI
    client = OpenAI(api_key=settings.OPENAI_API_KEY)
    resp = client.chat.completions.create(
        model=settings.OPENAI_MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
    )
    return resp.choices[0].message.content.strip()


def _appeler_mistral(prompt: str) -> str:
    """LLM via l'API Mistral (recommandé doc ISI §4.1)."""
    from mistralai import Mistral
    client = Mistral(api_key=settings.MISTRAL_API_KEY)
    resp = client.chat.complete(
        model=settings.MISTRAL_MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
    )
    return resp.choices[0].message.content.strip()


def repondre(question: str, top_k: int = None) -> ReponseChat:
    # 1) Recherche des articles pertinents (Service 5)
    resultats = s5_recherche.rechercher(question, top_k=top_k)

    # 2) Construction du prompt augmenté
    contexte = _construire_contexte(resultats)
    prompt = (
        f"{SYSTEM_PROMPT}\n\n"
        f"ARTICLES PERTINENTS:\n{contexte}\n\n"
        f"QUESTION: {question}\n\n"
        f"RÉPONSE (en français, précise et sourcée) :"
    )

    # 3) Génération selon le provider configuré (doc ISI §4.1 : GPT-4 / Mistral / Claude)
    if settings.LLM_PROVIDER == "mistral" and settings.MISTRAL_API_KEY:
        reponse = _appeler_mistral(prompt)
    elif settings.LLM_PROVIDER == "openai" and settings.OPENAI_API_KEY:
        reponse = _appeler_openai(prompt)
    else:
        reponse = _appeler_ollama(prompt)

    # 4) Sources cliquables (#page=N, §3.6.4)
    sources = [
        SourceCitee(
            id_article=r.id_article,
            titre_article=r.titre_article,
            page=r.page,
            score=round(r.score, 3),
            pdf_url=f"{settings.PDF_PUBLIC_URL}#page={r.page}",
        )
        for r in resultats
    ]

    return ReponseChat(question=question, reponse=reponse, sources=sources)
