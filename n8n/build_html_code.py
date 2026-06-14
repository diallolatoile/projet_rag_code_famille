"""
Génère code_famille.html à partir de articles_chunks.json :
- 1 article = 1 section avec ancre id="art-N"
- titres structurels (livre/chapitre/section/paragraphe) insérés en en-tête
- à l'ouverture, l'article ciblé par #art-N est encadré + surligné (JS)
"""
import json
import html
from pathlib import Path

DOSSIER = Path(__file__).parent
SRC = DOSSIER / "articles_chunks.json"
OUT = DOSSIER / "interface" / "code_famille.html"

chunks = json.load(open(SRC, encoding="utf-8"))


def esc(s):
    return html.escape(s or "")


# Construire le corps : on insère un titre de niveau quand il change
corps = []
etat = {"livre": None, "chapitre": None, "section": None, "paragraphe": None}

for c in chunks:
    m = c["metadata"]
    # insérer les titres hiérarchiques qui ont changé
    for niveau, balise in [("livre", "h1"), ("chapitre", "h2"),
                           ("section", "h3"), ("paragraphe", "h4")]:
        val = m.get(niveau)
        if val and val != etat[niveau]:
            etat[niveau] = val
            # réinitialiser les niveaux inférieurs
            ordre = ["livre", "chapitre", "section", "paragraphe"]
            for k in ordre[ordre.index(niveau) + 1:]:
                etat[k] = None
            corps.append(f'<{balise} class="t-{niveau}">{esc(val)}</{balise}>')

    # l'article lui-même
    num = m["article"]
    titre = m.get("titre") or ""
    # le texte commence par "Article N — Titre. corps..." : on sépare le corps
    texte = c["text"]
    # retirer le préfixe "Article N — Titre." pour ne garder que le corps
    prefixe = f"Article {num}"
    corps_texte = texte
    if " — " in texte:
        corps_texte = texte.split(". ", 1)[1] if ". " in texte else texte

    corps.append(
        f'<article id="art-{num}" class="article">'
        f'<div class="art-num">Article {esc(str(num))}</div>'
        f'<div class="art-titre">{esc(titre)}</div>'
        f'<p class="art-corps">{esc(corps_texte)}</p>'
        f'<a class="art-pdf" href="{esc(m["pdf_url"])}" target="_blank">Voir dans le PDF (page {esc(str(m["page"]))}) ↗</a>'
        f'</article>'
    )

corps_html = "\n".join(corps)

PAGE = """<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Code de la Famille sénégalais</title>
<style>
  :root {
    --encre:#1a2b3c; --papier:#f7f5f0; --carte:#fff;
    --accent:#1d6e56; --accent-clair:#e1f5ee; --or:#b58a2e;
    --bordure:#e3ded3; --muet:#6b6358; --surlign:#fff3c4;
  }
  * { box-sizing:border-box; }
  body { margin:0; background:var(--papier); color:var(--encre);
    font-family:"Iowan Old Style","Palatino Linotype",Georgia,serif; line-height:1.7; }
  .bandeau { background:var(--encre); color:var(--papier); padding:20px 24px;
    border-bottom:3px solid var(--or); position:sticky; top:0; z-index:10; }
  .bandeau h1 { margin:0; font-size:20px; font-weight:600; }
  .conteneur { max-width:780px; margin:0 auto; padding:28px 20px 80px; }
  h1.t-livre { font-size:22px; color:var(--encre); border-bottom:2px solid var(--or);
    padding-bottom:6px; margin:38px 0 18px; }
  h2.t-chapitre { font-size:18px; color:var(--accent); margin:30px 0 14px; }
  h3.t-section { font-size:15px; color:var(--encre); margin:24px 0 12px;
    font-family:system-ui,sans-serif; text-transform:uppercase; letter-spacing:0.04em; }
  h4.t-paragraphe { font-size:14px; color:var(--muet); margin:18px 0 10px;
    font-family:system-ui,sans-serif; }
  .article { background:var(--carte); border:1px solid var(--bordure); border-radius:8px;
    padding:16px 20px; margin-bottom:14px; scroll-margin-top:80px; transition:all .4s; }
  .art-num { font-family:system-ui,sans-serif; font-size:12px; font-weight:600;
    color:var(--accent); letter-spacing:0.03em; }
  .art-titre { font-weight:600; font-size:16px; margin:2px 0 8px; }
  .art-corps { margin:0 0 10px; font-size:15.5px; }
  .art-pdf { font-family:system-ui,sans-serif; font-size:13px; color:var(--accent);
    text-decoration:none; font-weight:500; }
  .art-pdf:hover { text-decoration:underline; }
  /* article ciblé : encadré + surligné */
  .article.cible { border:2px solid var(--accent); background:var(--accent-clair);
    box-shadow:0 0 0 4px rgba(29,110,86,0.12); }
  .article.cible .art-corps { background:var(--surlign); padding:8px 10px; border-radius:4px; }
  .recherche { width:100%; padding:12px 16px; border:1px solid var(--bordure);
    border-radius:8px; font-size:15px; font-family:system-ui,sans-serif; margin-bottom:22px; }
</style>
</head>
<body>
  <div class="bandeau"><h1>Code de la Famille sénégalais</h1></div>
  <div class="conteneur">
    <input class="recherche" id="rech" type="text"
      placeholder="Aller à un article : tapez un numéro et Entrée (ex : 51)" />
    __CORPS__
  </div>
<script>
  function surligner() {
    document.querySelectorAll('.article.cible').forEach(function(a){ a.classList.remove('cible'); });
    var h = location.hash;  // ex: #art-51
    if (h && h.indexOf('#art-') === 0) {
      var el = document.querySelector(h.replace(/[^#a-z0-9-]/gi,''));
      if (el) { el.classList.add('cible'); el.scrollIntoView({behavior:'smooth', block:'start'}); }
    }
  }
  window.addEventListener('hashchange', surligner);
  window.addEventListener('load', surligner);
  document.getElementById('rech').addEventListener('keydown', function(e){
    if (e.key === 'Enter') {
      var n = this.value.trim().replace(/\\D/g,'');
      if (n) location.hash = '#art-' + n;
    }
  });
</script>
</body>
</html>"""

OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text(PAGE.replace("__CORPS__", corps_html), encoding="utf-8")
print(f"{OUT} écrit ({len(chunks)} articles, {OUT.stat().st_size // 1024} Ko)")
