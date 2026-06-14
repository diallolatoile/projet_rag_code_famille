import { useState } from "react";
import ChatBox from "./components/ChatBox.jsx";
import Answer from "./components/Answer.jsx";
import PdfViewer from "./components/PdfViewer.jsx";

const API_CHAT = "/api/chat";

export default function App() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [erreur, setErreur] = useState("");
  const [pdf, setPdf] = useState(null); // { url, page, highlight }

  const poser = async (question) => {
    setLoading(true);
    setErreur("");
    setData(null);
    try {
      const r = await fetch(API_CHAT, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question, top_k: 4 }),
      });
      if (!r.ok) throw new Error("HTTP " + r.status);
      setData(await r.json());
    } catch (e) {
      setErreur("Impossible de joindre l'API. Vérifiez que le service est démarré (port 8000).");
    } finally {
      setLoading(false);
    }
  };

  const ouvrirPdf = (source) => {
    setPdf({
      url: source.pdf_url.split("#")[0],
      page: source.page,
      highlight: source.titre_article || "",
    });
  };

  return (
    <div className="app">
      <div className={"panneau-chat" + (pdf ? " avec-pdf" : "")}>
        <div className="bandeau">
          <h1>Chatbot Juridique — Code de la Famille sénégalais</h1>
          <p>Posez une question, obtenez une réponse sourcée avec renvoi au texte officiel</p>
        </div>
        <div className="contenu">
          <ChatBox onAsk={poser} loading={loading} onReset={() => setData(null)} />
          {loading && <div className="charge">Recherche dans le Code de la Famille…</div>}
          {erreur && <div className="charge">{erreur}</div>}
          {!loading && !erreur && <Answer data={data} onOpenPdf={ouvrirPdf} />}
        </div>
      </div>

      {pdf && (
        <PdfViewer
          pdfUrl={pdf.url}
          page={pdf.page}
          highlight={pdf.highlight}
          onClose={() => setPdf(null)}
        />
      )}
    </div>
  );
}
