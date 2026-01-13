CREATE EXTENSION IF NOT EXISTS pgcrypto;
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS application (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL,
    url TEXT UNIQUE NOT NULL,
    image_url TEXT,
    price_text TEXT,
    description TEXT
);

CREATE TABLE IF NOT EXISTS application_features (
    app_id UUID PRIMARY KEY REFERENCES application(id) ON DELETE CASCADE,
    features_url TEXT,
    num_sections INTEGER,
    features_text TEXT
);

CREATE TABLE IF NOT EXISTS application_search (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    app_id UUID UNIQUE NOT NULL REFERENCES application(id) ON DELETE CASCADE,
    embedding vector(1536)
);

CREATE TABLE IF NOT EXISTS labels (
    label TEXT PRIMARY KEY,
    synonyms TEXT[] DEFAULT '{}'
);

CREATE TABLE IF NOT EXISTS application_labels (
    app_search_id UUID REFERENCES application_search(id) ON DELETE CASCADE,
    label TEXT REFERENCES labels(label) ON DELETE CASCADE,
    PRIMARY KEY (app_search_id, label)
);

CREATE TABLE IF NOT EXISTS application_integration_keys (
    app_search_id UUID REFERENCES application_search(id) ON DELETE CASCADE,
    integration_key TEXT NOT NULL,
    PRIMARY KEY (app_search_id, integration_key)
);

CREATE INDEX IF NOT EXISTS idx_application_url ON application(url);
CREATE INDEX IF NOT EXISTS idx_application_search_app_id ON application_search(app_id);
CREATE INDEX IF NOT EXISTS idx_application_labels_app_search_id ON application_labels(app_search_id);
CREATE INDEX IF NOT EXISTS idx_application_labels_label ON application_labels(label);
CREATE INDEX IF NOT EXISTS idx_application_integration_keys_app_search_id ON application_integration_keys(app_search_id);
CREATE INDEX IF NOT EXISTS idx_application_search_embedding ON application_search USING hnsw (embedding vector_cosine_ops);
