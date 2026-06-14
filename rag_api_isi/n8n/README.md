# Alternative n8n — RAG ISI

Cette version réadapte l'orchestration n8n à l'architecture ISI. Plutôt que de
refaire le calcul lourd (embeddings e5, recherche Qdrant) dans des nodes n8n,
les workflows **appellent l'API FastAPI** des 6 services. n8n joue son rôle
naturel : orchestrer, exposer un webhook, brancher d'autres outils (Slack,
e-mail, planification…).

## Pourquoi cette approche ?

- **Cohérence** : un seul moteur d'embedding (e5) et une seule base (Qdrant),
  partagés entre l'API et n8n. Pas de divergence de résultats.
- **Simplicité** : les nodes n8n restent lisibles (un appel HTTP par étape).
- **Réutilisation** : toute la logique testée du backend est réutilisée.

## Workflows

| Fichier | Rôle |
|---------|------|
| `n8n_ingestion.json` | Déclenche le pipeline d'ingestion via `POST /api/ingest` |
| `n8n_chat.json` | Webhook → `POST /api/chat` → réponse sourcée |

## Mise en route

n8n est inclus dans le `docker-compose.yml` principal (avec sa propre base
Postgres). Tout démarre ensemble :

```bash
docker compose up -d
```

Ensuite, dans n8n (http://localhost:5678) :

1. Importer les deux fichiers JSON (*Workflows → Import from File*).
2. Pour l'ingestion : ouvrir *RAG ISI - Ingestion* → **Execute Workflow**
   (appelle `POST http://api:8000/api/ingest`).
3. Pour le chat : activer *RAG ISI - Chat* ; le webhook répond sur
   `http://localhost:5678/webhook/rag-isi-chat`.

> n8n nécessite `N8N_ENCRYPTION_KEY` et `N8N_USER_MANAGEMENT_JWT_SECRET` dans
> le fichier `.env` à la racine du projet.

## Test du webhook chat

```bash
curl -X POST http://localhost:5678/webhook/rag-isi-chat \
  -H "Content-Type: application/json" \
  -d '{"question":"Conditions pour reconnaître un enfant naturel ?"}'
```

La réponse a la même structure que l'API (`reponse` + `sources` cliquables),
donc le frontend `frontend/index.html` fonctionne avec l'une ou l'autre source
en changeant simplement l'URL cible.
