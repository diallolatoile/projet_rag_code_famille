# RAG — Chatbot Juridique Code de la Famille (ISI 2025-2026)

Système **Retrieval-Augmented Generation** appliqué au **Code de la Famille
sénégalais**, conforme au cahier des charges ISI. Deux implémentations :

1. **API REST FastAPI** — les 6 services en architecture orientée services (SOA).
2. **Workflow n8n** — alternative low-code (dossier `n8n/`).

---

## Architecture : les 6 services (doc ISI §3)

| # | Service | Endpoint | Rôle |
|---|---------|----------|------|
| 1 | Extraction | `POST /api/extract` | PDF → articles structurés (JSON) |
| 2 | Segmentation | `POST /api/segment` | Articles → chunks enrichis |
| 3 | Vectorisation | `POST /api/vectorize` | Chunks → embeddings (e5) |
| 4 | Indexation | `POST /api/index` | Vecteurs → Qdrant |
| 5 | Recherche | `POST /api/search` | Question → top-K articles |
| 6 | Réponse LLM | `POST /api/chat` | Question → réponse + sources |

Pipeline d'ingestion (offline) : services 1→4. Pipeline d'inférence (temps
réel) : services 5→6.

## Stack technique (doc ISI §4.1)

| Couche | Technologie | Conforme ISI |
|--------|-------------|--------------|
| Backend | Python 3.11, FastAPI | ✅ |
| Extraction PDF | PyMuPDF | ✅ |
| Embeddings | sentence-transformers — `multilingual-e5-large` (1024 dim, français) | ✅ |
| Base vectorielle | Qdrant | ✅ |
| LLM | **Mistral** / OpenAI (API) ou Ollama `llama3.2` (local) — au choix | ✅ |
| Frontend | **React** + Vite (chatbot + sources cliquables) | ✅ |
| Visionneuse PDF | **PDF.js** (navigation directe + surlignage) | ✅ |
| Conteneurisation | Docker Compose | ✅ |

Le LLM se choisit par `LLM_PROVIDER` : `mistral` (recommandé doc), `openai`,
ou `ollama` (local, hors-ligne, sans coût).

## Structure d'un chunk (doc ISI §3.2.4)

```json
{
  "chunk_id": "art_51_chunk_1",
  "id_article": "51",
  "titre_article": "Déclaration de naissance",
  "texte": "Article 51 — Déclaration de naissance. Toute naissance...",
  "page_debut": 12,
  "page_fin": 12,
  "livre": "LIVRE PREMIER DES PERSONNES",
  "chapitre": "CHAPITRE IV DE L'ETAT CIVIL",
  "tokens": 312
}
```

---

## Installation et lancement

### 1. Configurer le `.env`
```bash
cp .env.example .env
```
Par défaut le LLM est **Ollama** (local, gratuit). Pour utiliser **Mistral**
(recommandé par la doc ISI), éditez le `.env` :
```
LLM_PROVIDER=mistral
MISTRAL_API_KEY=votre_cle_mistral
```
Aucune autre modification n'est nécessaire : la bascule est automatique.

### 2. Placer le PDF
```bash
cp CODE-DE-LA-FAMILLE.pdf data/
```

### 3. Démarrer la stack
```bash
docker compose up -d
```
Cela lance : Qdrant, Ollama (+ téléchargement de llama3.2), l'API FastAPI et
le serveur PDF.

### 3. Lancer l'ingestion (services 1→4)
Première option, via l'API :
```bash
curl -X POST http://localhost:8000/api/ingest
```
Deuxième option, en ligne de commande :
```bash
docker compose -f ./rag_api_infra/docker-compose.yml exec api python /code/scripts/ingest.py
```
Le premier lancement télécharge le modèle e5-large (~2 Go).

### 4. Interroger le chatbot
- Interface web : http://localhost:8000/app
- Documentation interactive de l'API : http://localhost:8000/docs
- En direct :
```bash
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"question":"Quelles sont les conditions d_age pour se marier ?","top_k":4}'
```

---

## Utilisation service par service

Chaque service est appelable indépendamment (principe SOA) :

```bash
# Service 1 : extraction
curl -X POST http://localhost:8000/api/extract

# Service 2 : segmentation (lit le JSON d'extraction)
curl -X POST http://localhost:8000/api/segment

# Service 3 : vectorisation
curl -X POST http://localhost:8000/api/vectorize

# Service 4 : indexation Qdrant
curl -X POST http://localhost:8000/api/index

# Service 5 : recherche (sans génération)
curl -X POST http://localhost:8000/api/search \
  -H "Content-Type: application/json" \
  -d '{"question":"déclaration de naissance","top_k":3}'
```

---

## Choix techniques vs cahier des charges

- **Embeddings français** : `multilingual-e5-large` (recommandé doc §3.3.3),
  excellent en français, déployable localement et gratuit.
- **Base vectorielle** : Qdrant (recommandé doc §3.4.2 pour la production,
  filtres sur métadonnées, API REST).
- **LLM** : Ollama `llama3.2` en local pour la confidentialité et le coût zéro ;
  bascule possible vers OpenAI via `LLM_PROVIDER=openai` (doc §4.1).
- **Sources cliquables** : `#page=N` (doc §3.6.4), servies par nginx.

## Alternative n8n

Le dossier `n8n/` contient les workflows équivalents (ingestion + chat),
réadaptés à la structure de chunk ISI, pour une mise en œuvre low-code.
Voir `n8n/README.md`.
