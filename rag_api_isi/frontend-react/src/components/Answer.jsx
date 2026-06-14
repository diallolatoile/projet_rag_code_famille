/** Affiche la réponse et les sources cliquables (doc ISI §5.2 et §5.3). */
export default function Answer({ data, onOpenPdf }) {
  if (!data) {
    return <div className="vide">Votre réponse et les articles cités apparaîtront ici.</div>;
  }

  return (
    <>
      <div className="reponse">
        <div className="etiquette">Réponse</div>
        {data.reponse.split("\n").map((ligne, i) => (
          <p key={i} style={{ margin: "0 0 8px" }}>{ligne}</p>
        ))}
      </div>

      {data.sources?.length > 0 && (
        <>
          <p className="src-titre">Sources utilisées</p>
          {data.sources.map((s) => (
            <div className="src" key={s.id_article}>
              {s.score != null && (
                <span className="score">Score {s.score.toFixed(2)}</span>
              )}
              <div className="ref">
                Art. {s.id_article} — {s.titre_article || ""}
              </div>
              <div className="liens">
                <button
                  className="lien"
                  onClick={() => onOpenPdf(s)}
                  title="Ouvrir dans la visionneuse intégrée"
                >
                  Voir la page {s.page} (visionneuse) ↗
                </button>
                <a href={s.pdf_url} target="_blank" rel="noreferrer">
                  Ouvrir le PDF ↗
                </a>
              </div>
            </div>
          ))}
        </>
      )}
    </>
  );
}
