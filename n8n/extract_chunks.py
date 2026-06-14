"""
Extraction du Code de la Famille -> chunks JSON pour RAG.
1 article = 1 chunk, enrichi de métadonnées (livre, chapitre, section,
paragraphe, page, titre) et d'une URL cliquable vers la page du PDF.

Réutilise la même logique d'extraction 3 colonnes que extract.py.
"""
import fitz  # PyMuPDF
import re
import json
from pathlib import Path

# --- Paramètres ---
DOSSIER = Path(__file__).parent
SRC = DOSSIER / "CODE-DE-LA-FAMILLE.pdf"
OUT_JSON = DOSSIER / "articles_chunks.json"

# URL publique où le PDF sera servi (voir service nginx du docker-compose).
# La référence cliquable sera PDF_BASE_URL + "#page=N".
PDF_BASE_URL = "http://localhost:8080/CODE-DE-LA-FAMILLE.pdf"
DOCUMENT_NOM = "Code de la Famille sénégalais"

PAGES_SOMMAIRE = range(1, 7)  # pages 1 à 6 : table des matières, ignorées ici

doc = fitz.open(SRC)


# ---------------------------------------------------------------------------
# Fonctions d'extraction (identiques à extract.py)
# ---------------------------------------------------------------------------
def colonne(x_center):
    if x_center < 225:
        return 0
    elif x_center < 370:
        return 1
    return 2


def est_entete_ou_pied(bbox, txt):
    y0 = bbox[1]
    if y0 < 110 and txt.strip() in ("Sénégalais", "CODE DE LA FAMILLE", "Code de la Famille"):
        return True
    if y0 > 760 and txt.strip().isdigit():
        return True
    return False


DEBUT_ARTICLE = re.compile(r"^(Article|Art\.?)\s+(\d+|premier)\b", re.IGNORECASE)
DEBUT_SECTION = re.compile(r"^(LIVRE|CHAPITRE|SECTION|TITRE|Paragraphe|SOUS-SECTION)\b")


def corriger_chiffres_romains(texte):
    mots = (r"(LIVRE|CHAPITRE|SECTION|TITRE|PARAGRAPHE"
            r"|Livre|Chapitre|Section|Titre|Paragraphe)")

    def remplace(m):
        return f"{m.group(1)} {m.group(2).replace('l', 'I')}"

    return re.sub(mots + r"\s+([IVXl]+)\b", remplace, texte)


def ligne_est_grasse(ligne):
    spans = ligne["spans"]
    if not spans:
        return False
    sp = max(spans, key=lambda s: len(s["text"]))
    return bool(sp["flags"] & 16) or "Bold" in sp["font"]


def lire_lignes_bloc(blk):
    """Comme extract.py mais chaque élément porte aussi son numéro de page
    (ajouté plus bas, au niveau de la page)."""
    elements = []
    para = ""

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
        elif ligne_est_grasse(ligne):
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


# ---------------------------------------------------------------------------
# 1) Collecte de tous les éléments du corps, avec leur page
# ---------------------------------------------------------------------------
elements_globaux = []  # liste de (type, texte, page)

for pno, page in enumerate(doc):
    if (pno + 1) in PAGES_SOMMAIRE:
        continue

    d = page.get_text("dict")
    blocs = [b for b in d["blocks"] if "lines" in b]
    blocs = [b for b in blocs
             if not est_entete_ou_pied(b["bbox"],
                                       "".join(s["text"] for ln in b["lines"] for s in ln["spans"]))]
    blocs.sort(key=lambda b: (colonne((b["bbox"][0] + b["bbox"][2]) / 2), b["bbox"][1]))

    for b in blocs:
        for typ, txt in lire_lignes_bloc(b):
            elements_globaux.append((typ, txt, pno + 1))

# ---------------------------------------------------------------------------
# 2) Fusion des éléments scindés (titres/sections/paragraphes coupés)
#    On conserve la page du PREMIER morceau.
# ---------------------------------------------------------------------------
PONCT_FORTE = (".", ";", ":", "!", "?", "»")
fusionnes = []
for typ, txt, page in elements_globaux:
    if fusionnes and fusionnes[-1][0] == typ == "section" and not DEBUT_SECTION.match(txt):
        p, t, pg = fusionnes[-1]
        fusionnes[-1] = (p, (t[:-1] + txt) if t.endswith("-") else t + " " + txt, pg)
    elif fusionnes and fusionnes[-1][0] == "section" and typ == "titre":
        p, t, pg = fusionnes[-1]
        fusionnes[-1] = ("section", (t[:-1] + txt) if t.endswith("-") else t + " " + txt, pg)
    elif fusionnes and fusionnes[-1][0] == typ == "titre":
        p, t, pg = fusionnes[-1]
        fusionnes[-1] = (p, (t[:-1] + txt) if t.endswith("-") else t + " " + txt, pg)
    elif fusionnes and fusionnes[-1][0] == typ == "para":
        p, t, pg = fusionnes[-1]
        if t.endswith("-"):
            fusionnes[-1] = (p, t[:-1] + txt, pg)
        elif not t.rstrip().endswith(PONCT_FORTE):
            fusionnes[-1] = (p, t + " " + txt, pg)
        else:
            fusionnes.append((typ, txt, page))
    else:
        fusionnes.append((typ, txt, page))

# ---------------------------------------------------------------------------
# 3) Regroupement par article + suivi de l'état hiérarchique
# ---------------------------------------------------------------------------
def quel_niveau(titre_section):
    """Renvoie la clé de métadonnée correspondant au type de titre."""
    h = titre_section.upper()
    if h.startswith("LIVRE"):
        return "livre"
    if h.startswith("TITRE"):
        return "titre_section"
    if h.startswith("CHAPITRE"):
        return "chapitre"
    if h.startswith("SECTION") or h.startswith("SOUS-SECTION"):
        return "section"
    if h.startswith("PARAGRAPHE"):
        return "paragraphe"
    return None


# état hiérarchique courant ; un niveau plus haut réinitialise les niveaux inférieurs
HIERARCHIE = ["livre", "titre_section", "chapitre", "section", "paragraphe"]
etat = {k: None for k in HIERARCHIE}

chunks = []
article_courant = None


def cloturer_article():
    """Construit le chunk de l'article courant et l'ajoute à la liste."""
    global article_courant
    if article_courant is None:
        return
    num = article_courant["numero_txt"]
    titre = article_courant["titre"]
    corps = " ".join(article_courant["paras"]).strip()
    # texte du chunk : on inclut numéro + titre pour un meilleur embedding
    texte = f"{num}"
    if titre:
        texte += f" — {titre}"
    if corps:
        texte += f". {corps}"

    page = article_courant["page"]
    meta = {
        "document": DOCUMENT_NOM,
        "article": article_courant["numero"],
        "titre": titre or None,
        "livre": article_courant["etat"]["livre"],
        "chapitre": article_courant["etat"]["chapitre"],
        "section": article_courant["etat"]["section"],
        "paragraphe": article_courant["etat"]["paragraphe"],
        "page": page,
        "pdf_url": f"{PDF_BASE_URL}#page={page}",
    }
    chunks.append({
        "chunk_id": f"art_{article_courant['numero']}",
        "text": corriger_chiffres_romains(texte),
        "metadata": meta,
    })
    article_courant = None


def numero_article(txt):
    """Extrait le numéro d'article ('Article 169' -> 169, 'premier' -> 1)."""
    m = re.search(r"(\d+)", txt)
    if m:
        return int(m.group(1))
    if "premier" in txt.lower():
        return 1
    return None


for typ, txt, page in fusionnes:
    txt = corriger_chiffres_romains(txt)

    if typ == "section":
        cloturer_article()
        niveau = quel_niveau(txt)
        if niveau:
            etat[niveau] = txt
            # réinitialiser les niveaux inférieurs
            idx = HIERARCHIE.index(niveau)
            for k in HIERARCHIE[idx + 1:]:
                etat[k] = None

    elif typ == "num":
        cloturer_article()
        article_courant = {
            "numero_txt": txt,
            "numero": numero_article(txt),
            "titre": None,
            "paras": [],
            "page": page,
            "etat": dict(etat),  # copie de l'état hiérarchique au moment de l'article
        }

    elif typ == "titre":
        # premier 'titre' après un 'num' = titre de l'article
        if article_courant is not None and article_courant["titre"] is None:
            article_courant["titre"] = txt

    elif typ == "para":
        if article_courant is not None:
            article_courant["paras"].append(txt)

cloturer_article()  # dernier article

# ---------------------------------------------------------------------------
# 4) Écriture du JSON
# ---------------------------------------------------------------------------
with open(OUT_JSON, "w", encoding="utf-8") as f:
    json.dump(chunks, f, ensure_ascii=False, indent=2)

print(f"{len(chunks)} chunks (articles) écrits -> {OUT_JSON}")
# aperçu
for c in chunks[:2]:
    print(json.dumps(c, ensure_ascii=False, indent=2)[:600])
