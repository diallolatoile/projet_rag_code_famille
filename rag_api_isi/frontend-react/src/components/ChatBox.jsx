import { useState } from "react";

/** Zone de saisie de la question (doc ISI §5.2). */
export default function ChatBox({ onAsk, loading, onReset }) {
  const [question, setQuestion] = useState("");

  const envoyer = () => {
    const q = question.trim();
    if (q) onAsk(q);
  };

  return (
    <>
      <div className="barre">
        <input
          type="text"
          value={question}
          placeholder="Ex : Quelles sont les conditions d'âge pour se marier ?"
          onChange={(e) => setQuestion(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && envoyer()}
        />
        <button onClick={envoyer} disabled={loading}>Demander</button>
      </div>
      <div className="actions">
        <a onClick={() => { setQuestion(""); onReset(); }}>Réinitialiser</a>
      </div>
    </>
  );
}
