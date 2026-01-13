#!/usr/bin/env python3
"""
Supabase Data Ingestion Pipeline
Loads applications from scraped data, generates embeddings, labels, and integration keys using OpenAI.
"""
import os
import sys
import json
import re
import time
from pathlib import Path
from typing import List, Dict, Optional, Tuple
import asyncpg
from openai import AsyncOpenAI
from dotenv import load_dotenv

# Load environment variables from .env file
BASE_DIR = Path(__file__).parent.parent
ENV_PATH = BASE_DIR / ".env"
load_dotenv(ENV_PATH)

APPS_FILE = str(BASE_DIR / "data" / "scraped" / "apps_encontradas.txt")
FEATURES_FILE = str(BASE_DIR / "data" / "scraped" / "features_encontradas.json")

DATABASE_URL = os.getenv("DATABASE_URL")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

if not DATABASE_URL:
    raise ValueError("DATABASE_URL environment variable not set")
if not OPENAI_API_KEY:
    raise ValueError("OPENAI_API_KEY environment variable not set")

openai_client = AsyncOpenAI(api_key=OPENAI_API_KEY)

LABEL_CATALOG = [
    "Accounting", "Analytics", "Banking", "CRM", "Communication", "Compliance",
    "Customer Support", "Data Management", "Debt Collection", "Document Management",
    "E-commerce", "Email Marketing", "Financial Planning", "HR & Payroll", "Invoicing",
    "Inventory Management", "Legal Services", "Liquidity Management", "Marketing Automation",
    "Multi-Banking", "Online Payments", "Point of Sale", "Project Management", "Reporting",
    "Sales", "Shipping & Logistics", "Tax Management", "Time Tracking", "Workflow Automation"
]

def parse_apps_txt(file_path: str) -> List[Dict]:
    """Parse apps_encontradas.txt file"""
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()
    
    apps = []
    pattern = r"(\d+)\.\s+(.+?)\n\s+Link:\s+(.+?)\n\s+Imagen:\s+(.+?)\n\s+Precio:\s+(.+?)\n\s+Descripción:\s+(.+?)(?=\n\n-{80}|\n\n\d+\.|\Z)"
    matches = re.finditer(pattern, content, re.DOTALL)
    
    for match in matches:
        apps.append({
            "name": match.group(2).strip(),
            "url": match.group(3).strip(),
            "image_url": match.group(4).strip(),
            "price_text": match.group(5).strip(),
            "description": match.group(6).strip()
        })
    
    return apps

def load_features_json(file_path: str) -> Dict[str, Dict]:
    """Load features_encontradas.json and index by url"""
    with open(file_path, "r", encoding="utf-8") as f:
        features_list = json.load(f)
    
    features_by_url = {}
    for feature in features_list:
        url = feature.get("url")
        if url:
            features_by_url[url] = {
                "features_url": feature.get("features_url"),
                "num_sections": feature.get("num_secciones", 0),
                "features_text": feature.get("features_text", "")
            }
    
    return features_by_url

async def retry_openai_call(func, *args, retries=2, **kwargs):
    """Retry OpenAI API calls"""
    for attempt in range(retries + 1):
        try:
            return await func(*args, **kwargs)
        except Exception as e:
            if attempt == retries:
                print(f"OpenAI call failed after {retries} retries: {e}")
                raise
            print(f"Retry {attempt + 1}/{retries} after error: {e}")
            time.sleep(1)

async def generate_embedding(text: str) -> List[float]:
    """Generate embedding using OpenAI"""
    response = await retry_openai_call(
        openai_client.embeddings.create,
        model="text-embedding-3-small",
        input=text[:8000]
    )
    return response.data[0].embedding

async def extract_labels(text: str, allowed_labels: List[str]) -> List[str]:
    """Extract labels using OpenAI"""
    prompt = f"""You are a classification assistant. Given the following text about a business application, select 2-6 labels from the allowed list that best describe it.

Allowed labels: {', '.join(allowed_labels)}

Text:
{text[:2000]}

Respond ONLY with valid JSON in this exact format:
{{"labels": ["label1", "label2"]}}

Use only labels from the allowed list. Select between 2 and 6 labels."""

    response = await retry_openai_call(
        openai_client.chat.completions.create,
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "You are a classification assistant. Respond only with valid JSON."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.3,
        response_format={"type": "json_object"}
    )
    
    result = json.loads(response.choices[0].message.content)
    labels = result.get("labels", [])
    
    return [label for label in labels if label in allowed_labels][:6]

async def extract_integrations(text: str) -> List[str]:
    """Extract integration keys using OpenAI"""
    prompt = f"""You are an integration extraction assistant. Given the following text about a business application, extract a list of external services, platforms, or integrations mentioned (e.g., Stripe, DATEV, Zapier, Shopify, bexio, Twint, etc.).

Text:
{text[:2000]}

Respond ONLY with valid JSON in this exact format:
{{"integrations": ["Integration1", "Integration2"]}}

Extract between 0 and 20 integration names. Use proper capitalization."""

    response = await retry_openai_call(
        openai_client.chat.completions.create,
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "You are an integration extraction assistant. Respond only with valid JSON."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.3,
        response_format={"type": "json_object"}
    )
    
    result = json.loads(response.choices[0].message.content)
    integrations = result.get("integrations", [])
    
    return [integ.strip() for integ in integrations if integ.strip()][:20]

async def upsert_application(conn, app: Dict) -> str:
    """Upsert application and return app_id"""
    app_id = await conn.fetchval("""
        INSERT INTO application (name, url, image_url, price_text, description)
        VALUES ($1, $2, $3, $4, $5)
        ON CONFLICT (url) DO UPDATE SET
            name = EXCLUDED.name,
            image_url = EXCLUDED.image_url,
            price_text = EXCLUDED.price_text,
            description = EXCLUDED.description
        RETURNING id
    """, app["name"], app["url"], app.get("image_url"), app.get("price_text"), app.get("description"))
    
    return str(app_id)

async def upsert_features(conn, app_id: str, features: Dict):
    """Upsert application features"""
    await conn.execute("""
        INSERT INTO application_features (app_id, features_url, num_sections, features_text)
        VALUES ($1, $2, $3, $4)
        ON CONFLICT (app_id) DO UPDATE SET
            features_url = EXCLUDED.features_url,
            num_sections = EXCLUDED.num_sections,
            features_text = EXCLUDED.features_text
    """, app_id, features.get("features_url"), features.get("num_sections", 0), features.get("features_text", ""))

async def upsert_application_search(conn, app_id: str, embedding: List[float]) -> str:
    """Upsert application_search and return app_search_id"""
    # Convert embedding list to pgvector format string
    embedding_str = '[' + ','.join(map(str, embedding)) + ']'
    
    app_search_id = await conn.fetchval("""
        INSERT INTO application_search (app_id, embedding)
        VALUES ($1, $2::vector)
        ON CONFLICT (app_id) DO UPDATE SET
            embedding = EXCLUDED.embedding
        RETURNING id
    """, app_id, embedding_str)
    
    return str(app_search_id)

async def ensure_label_exists(conn, label: str):
    """Ensure label exists in labels table"""
    await conn.execute("""
        INSERT INTO labels (label, synonyms)
        VALUES ($1, $2)
        ON CONFLICT (label) DO NOTHING
    """, label, [])

async def initialize_schema(conn):
    """Initialize database schema if tables don't exist"""
    schema_sql = """
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
    """
    
    await conn.execute(schema_sql)

async def upsert_application_labels(conn, app_search_id: str, labels: List[str]):
    """Upsert application labels"""
    await conn.execute("DELETE FROM application_labels WHERE app_search_id = $1", app_search_id)
    
    for label in labels:
        await ensure_label_exists(conn, label)
        await conn.execute("""
            INSERT INTO application_labels (app_search_id, label)
            VALUES ($1, $2)
            ON CONFLICT DO NOTHING
        """, app_search_id, label)

async def upsert_integration_keys(conn, app_search_id: str, integrations: List[str]):
    """Upsert integration keys"""
    await conn.execute("DELETE FROM application_integration_keys WHERE app_search_id = $1", app_search_id)
    
    for integration in integrations:
        await conn.execute("""
            INSERT INTO application_integration_keys (app_search_id, integration_key)
            VALUES ($1, $2)
            ON CONFLICT DO NOTHING
        """, app_search_id, integration)

async def main():
    """Main ingestion pipeline"""
    print("=" * 80)
    print("SUPABASE DATA INGESTION PIPELINE")
    print("=" * 80)
    
    if not os.path.exists(APPS_FILE):
        raise FileNotFoundError(f"Apps file not found: {APPS_FILE}")
    if not os.path.exists(FEATURES_FILE):
        raise FileNotFoundError(f"Features file not found: {FEATURES_FILE}")
    
    print(f"✓ Found apps file: {APPS_FILE}")
    print(f"✓ Found features file: {FEATURES_FILE}")
    
    print("\n[1/6] Parsing input files...")
    apps = parse_apps_txt(APPS_FILE)
    features_by_url = load_features_json(FEATURES_FILE)
    print(f"✓ Parsed {len(apps)} applications")
    print(f"✓ Loaded {len(features_by_url)} feature sets")
    
    print("\n[2/6] Connecting to database...")
    conn = await asyncpg.connect(DATABASE_URL)
    print("✓ Connected to Supabase")
    
    try:
        print("\n[3/6] Initializing database schema...")
        await initialize_schema(conn)
        print("✓ Schema initialized (tables and indexes created)")
        
        print("\n[4/6] Initializing label catalog...")
        for label in LABEL_CATALOG:
            await ensure_label_exists(conn, label)
        print(f"✓ Initialized {len(LABEL_CATALOG)} labels")
        
        print("\n[5/6] Processing applications...")
        total = len(apps)
        for idx, app in enumerate(apps, 1):
            print(f"\n  [{idx}/{total}] Processing: {app['name']}")
            
            app_id = await upsert_application(conn, app)
            print(f"    ✓ Upserted application (id: {app_id[:8]}...)")
            
            features = features_by_url.get(app["url"], {})
            if features:
                await upsert_features(conn, app_id, features)
                print(f"    ✓ Upserted features")
            
            text_for_embedding = f"{app['name']}\n{app.get('description', '')}"
            if features.get("features_text"):
                text_for_embedding += f"\n{features['features_text'][:2000]}"
            
            print(f"    → Generating embedding...")
            embedding = await generate_embedding(text_for_embedding)
            app_search_id = await upsert_application_search(conn, app_id, embedding)
            print(f"    ✓ Generated embedding (search_id: {app_search_id[:8]}...)")
            
            print(f"    → Extracting labels...")
            labels = await extract_labels(text_for_embedding, LABEL_CATALOG)
            await upsert_application_labels(conn, app_search_id, labels)
            print(f"    ✓ Assigned labels: {', '.join(labels)}")
            
            print(f"    → Extracting integrations...")
            integrations = await extract_integrations(text_for_embedding)
            await upsert_integration_keys(conn, app_search_id, integrations)
            print(f"    ✓ Assigned integrations: {', '.join(integrations) if integrations else 'none'}")
        
        print("\n[6/7] Verifying data...")
        app_count = await conn.fetchval("SELECT COUNT(*) FROM application")
        search_count = await conn.fetchval("SELECT COUNT(*) FROM application_search")
        label_count = await conn.fetchval("SELECT COUNT(*) FROM labels")
        app_labels_count = await conn.fetchval("SELECT COUNT(*) FROM application_labels")
        integrations_count = await conn.fetchval("SELECT COUNT(*) FROM application_integration_keys")
        
        print(f"  Applications: {app_count}")
        print(f"  Search entries: {search_count}")
        print(f"  Labels: {label_count}")
        print(f"  Application-Label relations: {app_labels_count}")
        print(f"  Application-Integration relations: {integrations_count}")
        
        print("\n[7/7] Pipeline completed successfully!")
        print("=" * 80)
        
    finally:
        await conn.close()
        print("✓ Database connection closed")

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
