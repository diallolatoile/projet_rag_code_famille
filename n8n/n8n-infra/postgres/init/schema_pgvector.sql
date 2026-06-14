-- =====================================================================
-- Schéma pgvector pour le RAG "Code de la Famille"
-- À placer dans ./postgres/init/ (monté en /docker-entrypoint-initdb.d)
-- pour être exécuté automatiquement à la création de la base.
--
-- Embeddings : Ollama "nomic-embed-text" -> vecteurs de 768 dimensions.
-- =====================================================================

-- 1) Activer l'extension pgvector (l'image pgvector/pgvector:pg16 l'inclut)
CREATE EXTENSION IF NOT EXISTS vector;

-- 2) Table des chunks (1 ligne = 1 article)
CREATE TABLE IF NOT EXISTS code_famille_chunks (
    id          BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    chunk_id    TEXT UNIQUE NOT NULL,        -- ex: 'art_51'
    text        TEXT        NOT NULL,        -- contenu indexé
    metadata    JSONB       NOT NULL,        -- {article, titre, livre, ...}
    embedding   VECTOR(768)                  -- vecteur nomic-embed-text
);

-- 3) Index sur le numéro d'article (filtrage éventuel par métadonnée)
CREATE INDEX IF NOT EXISTS code_famille_chunks_article_idx
    ON code_famille_chunks ((metadata->>'article'));

-- =====================================================================
-- APRÈS INDEXATION : créer l'index vectoriel (à lancer une seule fois,
-- une fois les 854 articles insérés)
-- =====================================================================
-- docker compose exec postgres sh -c 'psql -U n8n -d n8n -c "
--   CREATE INDEX IF NOT EXISTS code_famille_chunks_embedding_idx
--     ON code_famille_chunks
--     USING ivfflat (embedding vector_cosine_ops)
--     WITH (lists = 100);"'


-- =====================================================================
-- REQUÊTES DE RÉFÉRENCE (utilisées dans les nodes Postgres de n8n)
-- =====================================================================

-- (A) INSERTION d'un chunk (node "Insert pgvector" du workflow d'indexation).
--     IMPORTANT : on utilise le dollar-quoting ($$ ... $$) au lieu de
--     paramètres séparés par virgules. En effet, le JSON des métadonnées
--     contient des virgules, qui cassaient la substitution de n8n et
--     provoquaient l'erreur "invalid input syntax for type json".
--     Le dollar-quoting protège le texte ET le JSON sans échappement.
--
-- INSERT INTO code_famille_chunks (chunk_id, text, metadata, embedding)
-- VALUES (
--   '{{ $('Tronquer pour embedding').item.json.chunk_id }}',
--   $$ {{ $('Tronquer pour embedding').item.json.text }} $$,
--   $$ {{ JSON.stringify($('Tronquer pour embedding').item.json.metadata) }} $$::jsonb,
--   '[{{ $json.embedding.join(",") }}]'::vector
-- )
-- ON CONFLICT (chunk_id) DO UPDATE
--   SET text = EXCLUDED.text,
--       metadata = EXCLUDED.metadata,
--       embedding = EXCLUDED.embedding;


-- (B) RECHERCHE des k articles les plus proches de la question
--     (node "Recherche pgvector" du workflow de question).
--     L'opérateur <=> = distance cosinus (plus petit = plus proche).
--
-- SELECT
--     chunk_id,
--     text,
--     metadata,
--     1 - (embedding <=> '[{{ $json.embedding.join(",") }}]'::vector) AS similarite
-- FROM code_famille_chunks
-- ORDER BY embedding <=> '[{{ $json.embedding.join(",") }}]'::vector
-- LIMIT 5;


-- =====================================================================
-- VÉRIFICATIONS UTILES (à lancer depuis le terminal hôte)
-- =====================================================================
-- Compter les articles indexés :
--   docker compose exec postgres sh -c 'psql -U n8n -d n8n -c "SELECT count(*) FROM code_famille_chunks;"'
--
-- Voir les 5 premiers titres :
--   docker compose exec postgres sh -c 'psql -U n8n -d n8n -c "SELECT chunk_id, metadata->>'\''titre'\'' FROM code_famille_chunks LIMIT 5;"'
--
-- Vider la table pour réindexer proprement :
--   docker compose exec postgres sh -c 'psql -U n8n -d n8n -c "TRUNCATE code_famille_chunks;"'