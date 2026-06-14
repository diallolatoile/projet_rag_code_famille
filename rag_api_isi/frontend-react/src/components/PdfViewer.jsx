import { useEffect, useRef, useState } from "react";
import * as pdfjsLib from "pdfjs-dist";
import pdfWorker from "pdfjs-dist/build/pdf.worker.min.mjs?url";

pdfjsLib.GlobalWorkerOptions.workerSrc = pdfWorker;

/**
 * Visionneuse PDF.js (doc ISI §5.2) : ouvre le PDF à une page donnée
 * et surligne le passage correspondant à l'article cité.
 */
export default function PdfViewer({ pdfUrl, page, highlight, onClose }) {
  const canvasRef = useRef(null);
  const [pdf, setPdf] = useState(null);
  const [pageNum, setPageNum] = useState(page || 1);
  const [total, setTotal] = useState(0);

  // chargement du document
  useEffect(() => {
    let annule = false;
    pdfjsLib.getDocument(pdfUrl).promise.then((doc) => {
      if (annule) return;
      setPdf(doc);
      setTotal(doc.numPages);
    });
    return () => { annule = true; };
  }, [pdfUrl]);

  useEffect(() => { setPageNum(page || 1); }, [page]);

  // rendu de la page courante + surlignage
  useEffect(() => {
    if (!pdf || !canvasRef.current) return;
    let annule = false;

    pdf.getPage(pageNum).then((pg) => {
      if (annule) return;
      const echelle = 1.4;
      const viewport = pg.getViewport({ scale: echelle });
      const canvas = canvasRef.current;
      const ctx = canvas.getContext("2d");
      canvas.width = viewport.width;
      canvas.height = viewport.height;

      pg.render({ canvasContext: ctx, viewport }).promise
        .then(() => pg.getTextContent())
        .then((txt) => {
          if (annule || !highlight) return;
          const cible = highlight.toLowerCase().slice(0, 24);
          ctx.fillStyle = "rgba(255, 220, 50, 0.42)";
          txt.items.forEach((it) => {
            if (it.str && it.str.toLowerCase().includes(cible.slice(0, 14))) {
              const t = pdfjsLib.Util.transform(viewport.transform, it.transform);
              const h = Math.hypot(t[2], t[3]);
              ctx.fillRect(t[4], t[5] - h, it.width * echelle, h * 1.2);
            }
          });
        });
    });
    return () => { annule = true; };
  }, [pdf, pageNum, highlight]);

  return (
    <div className="panneau-pdf">
      <div className="pdf-bandeau">
        <span className="titre">Code de la Famille</span>
        <button onClick={() => setPageNum((n) => Math.max(1, n - 1))}>◀</button>
        <span>Page {pageNum} / {total || "…"}</span>
        <button onClick={() => setPageNum((n) => Math.min(total, n + 1))}>▶</button>
        <button className="fermer" onClick={onClose}>Retour au chat ✕</button>
      </div>
      <div className="pdf-zone">
        <canvas ref={canvasRef} />
      </div>
    </div>
  );
}
