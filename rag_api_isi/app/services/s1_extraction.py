"""
Service 1 — Extraction (doc ISI §3.1)
Transforme le PDF du Code de la Famille en articles structurés (JSON).
Réutilise la logique d'extraction 3 colonnes éprouvée (tri par colonne,
recollage des mots coupés, hiérarchie livre/chapitre, correction des
chiffres romains).
"""
import re
import fitz  # PyMuPDF

from app.models.schemas import Article
from app.core.config import settings

# --- Détections ---
DEBUT_ARTICLE = re.compile(r"^(Article|Art\.?)\s+(\d+|premier)\b", re.IGNORECASE)
DEBUT_SECTION = re.compile(r"^(LIVRE|CHAPITRE|SECTION|TITRE|Paragraphe|SOUS-SECTION)\b")
PAGES_SOMMAIRE = range(1, 7)  # table des matières, ignorée


def _colonne(x_center: float) -> int:
    if x_center < 225:
        return 0
    elif x_center < 370:
        return 1
    return 2


def _entete_ou_pied(bbox, txt: str) -> bool:
    y0 = bbox[1]
    t = txt.strip()
    if y0 < 110 and t in ("Sénégalais", "CODE DE LA FAMILLE", "Code de la Famille"):
        return True
    if y0 > 760 and t.isdigit():
        return True
    return False


def _corriger_romains(texte: str) -> str:
    mots = (r"(LIVRE|CHAPITRE|SECTION|TITRE|PARAGRAPHE"
            r"|Livre|Chapitre|Section|Titre|Paragraphe)")

    def repl(m):
        return f"{m.group(1)} {m.group(2).replace('l', 'I')}"

    return re.sub(mots + r"\s+([IVXl]+)\b", repl, texte)


def _ligne_grasse(ligne) -> bool:
    spans = ligne["spans"]
    if not spans:
        return False
    sp = max(spans, key=lambda s: len(s["text"]))
    return bool(sp["flags"] & 16) or "Bold" in sp["font"]


def _lire_bloc(blk):
    """Classe les lignes d'un bloc en (type, texte)."""
    elements, para = [], ""

    def vider():
        nonlocal para
        if para:
            elements.append(("para", para.strip()))
            para = ""

    for ligne in blk["lines"]:
        texte = "".join(s["text"] for s in ligne["spans"]).strip()
        if not texte:
            continue
        if DEBUT_ARTICLE.match(texte):
            vider()
            elements.append(("num", texte))
        elif DEBUT_SECTION.match(texte):
            vider()
            elements.append(("section", texte))
        elif (elements and elements[-1][0] == "section" and not para
              and not DEBUT_ARTICLE.match(texte) and not DEBUT_SECTION.match(texte)):
            prec = elements[-1][1]
            elements[-1] = ("section",
                            (prec[:-1] + texte) if prec.endswith("-") else prec + " " + texte)
        elif _ligne_grasse(ligne):
            vider()
            elements.append(("titre", texte))
        elif para.endswith("-"):
            para = para[:-1] + texte
        elif para:
            para += " " + texte
        else:
            para = texte
    vider()
    return elements


def _numero(txt: str) -> str:
    m = re.search(r"(\d+)", txt)
    if m:
        return m.group(1)
    return "1" if "premier" in txt.lower() else "?"


def extraire_articles(pdf_path: str = None) -> list[Article]:
    """Extrait tous les articles du PDF et retourne une liste d'Article (ISI)."""
    pdf_path = pdf_path or settings.PDF_PATH
    doc = fitz.open(pdf_path)

    # 1) Collecte des éléments (type, texte, page) dans l'ordre de lecture
    elements = []
    for pno, page in enumerate(doc):
        if (pno + 1) in PAGES_SOMMAIRE:
            continue
        d = page.get_text("dict")
        blocs = [b for b in d["blocks"] if "lines" in b]
        blocs = [b for b in blocs
                 if not _entete_ou_pied(
                     b["bbox"], "".join(s["text"] for ln in b["lines"] for s in ln["spans"]))]
        blocs.sort(key=lambda b: (_colonne((b["bbox"][0] + b["bbox"][2]) / 2), b["bbox"][1]))
        for b in blocs:
            for typ, txt in _lire_bloc(b):
                elements.append((typ, txt, pno + 1))

    # 2) Fusion des fragments scindés (titres/sections/paragraphes coupés)
    PONCT = (".", ";", ":", "!", "?", "»")
    fus = []
    for typ, txt, page in elements:
        if fus and fus[-1][0] == typ == "section" and not DEBUT_SECTION.match(txt):
            p, t, pg = fus[-1]
            fus[-1] = (p, (t[:-1] + txt) if t.endswith("-") else t + " " + txt, pg)
        elif fus and fus[-1][0] == "section" and typ == "titre":
            p, t, pg = fus[-1]
            fus[-1] = ("section", (t[:-1] + txt) if t.endswith("-") else t + " " + txt, pg)
        elif fus and fus[-1][0] == typ == "titre":
            p, t, pg = fus[-1]
            fus[-1] = (p, (t[:-1] + txt) if t.endswith("-") else t + " " + txt, pg)
        elif fus and fus[-1][0] == typ == "para":
            p, t, pg = fus[-1]
            if t.endswith("-"):
                fus[-1] = (p, t[:-1] + txt, pg)
            elif not t.rstrip().endswith(PONCT):
                fus[-1] = (p, t + " " + txt, pg)
            else:
                fus.append((typ, txt, page))
        else:
            fus.append((typ, txt, page))

    # 3) Regroupement par article + suivi hiérarchique
    etat = {"livre": None, "titre": None, "chapitre": None}
    articles, courant = [], None

    def cloturer():
        nonlocal courant
        if courant:
            articles.append(courant)
            courant = None

    for typ, txt, page in fus:
        txt = _corriger_romains(txt)
        if typ == "section":
            h = txt.upper()
            if h.startswith("LIVRE"):
                etat["livre"], etat["titre"], etat["chapitre"] = txt, None, None
            elif h.startswith("TITRE"):
                etat["titre"], etat["chapitre"] = txt, None
            elif h.startswith("CHAPITRE"):
                etat["chapitre"] = txt
        elif typ == "num":
            cloturer()
            courant = Article(
                id_article=_numero(txt), titre_article=None, texte="",
                page_debut=page, page_fin=page,
                livre=etat["livre"], titre=etat["titre"], chapitre=etat["chapitre"],
            )
        elif typ == "titre":
            if courant and courant.titre_article is None:
                courant.titre_article = txt
        elif typ == "para":
            if courant:
                courant.texte = (courant.texte + " " + txt).strip()
                courant.page_fin = page

    cloturer()
    return articles
