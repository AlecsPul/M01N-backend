#!/usr/bin/env python3
"""
Synonyms Generator for Labels
Generates and updates synonyms for each label using OpenAI.
"""
import os
import sys
import json
import time
from pathlib import Path
from typing import List
import asyncpg
from openai import AsyncOpenAI
from dotenv import load_dotenv

# Load environment variables
BASE_DIR = Path(__file__).parent.parent
ENV_PATH = BASE_DIR / ".env"
load_dotenv(ENV_PATH)

DATABASE_URL = os.getenv("DATABASE_URL")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

if not DATABASE_URL:
    raise ValueError("DATABASE_URL environment variable not set")
if not OPENAI_API_KEY:
    raise ValueError("OPENAI_API_KEY environment variable not set")

openai_client = AsyncOpenAI(api_key=OPENAI_API_KEY)


async def retry_openai_call(func, *args, retries=2, **kwargs):
    """Retry OpenAI API calls"""
    for attempt in range(retries + 1):
        try:
            return await func(*args, **kwargs)
        except Exception as e:
            if attempt == retries:
                print(f"    ⚠ OpenAI call failed after {retries} retries: {e}")
                return None
            print(f"    → Retry {attempt + 1}/{retries} after error: {e}")
            time.sleep(1)


async def generate_synonyms(label: str) -> List[str]:
    """
    Generate 1-3 synonyms for a label using OpenAI
    
    Args:
        label: The label to generate synonyms for
        
    Returns:
        List of 1-3 synonyms
    """
    prompt = f"""You are a synonym generation assistant. Given a business/software category label, provide 1-3 relevant synonyms or alternative terms.

Label: {label}

Rules:
- Provide 1-3 synonyms that are commonly used alternatives
- Use proper capitalization
- Synonyms should be semantically similar or related terms
- If the label is very specific and has no good synonyms, provide closely related terms
- Return ONLY valid JSON

Examples:
- "Accounting" → ["Bookkeeping", "Financial Management"]
- "CRM" → ["Customer Management", "Sales Management"]
- "E-commerce" → ["Online Store", "Digital Commerce"]

Respond ONLY with valid JSON in this exact format:
{{"synonyms": ["Synonym1", "Synonym2"]}}"""

    try:
        response = await retry_openai_call(
            openai_client.chat.completions.create,
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a synonym generation assistant. Respond only with valid JSON."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.4,
            response_format={"type": "json_object"}
        )
        
        if not response:
            return []
        
        result = json.loads(response.choices[0].message.content)
        synonyms = result.get("synonyms", [])
        
        # Clean and validate
        cleaned = [syn.strip() for syn in synonyms if syn and syn.strip()]
        return cleaned[:3]
        
    except Exception as e:
        print(f"    ⚠ Error generating synonyms: {e}")
        return []


async def update_label_synonyms(conn, label: str, synonyms: List[str]):
    """
    Update synonyms for a label in the database
    
    Args:
        conn: Database connection
        label: Label name
        synonyms: List of synonyms
    """
    await conn.execute("""
        UPDATE labels
        SET synonyms = $1
        WHERE label = $2
    """, synonyms, label)


async def process_all_labels():
    """
    Main function to process all labels and generate synonyms
    """
    print("=" * 80)
    print("SYNONYMS GENERATION FOR LABELS")
    print("=" * 80)
    
    conn = await asyncpg.connect(DATABASE_URL)
    print("✓ Connected to database\n")
    
    try:
        # Get all labels
        labels = await conn.fetch("SELECT label FROM labels ORDER BY label")
        total = len(labels)
        
        if total == 0:
            print("⚠ No labels found in database. Run load_supabase.py first.")
            return
        
        print(f"Found {total} labels to process\n")
        
        processed = 0
        errors = 0
        total_synonyms = 0
        
        for idx, row in enumerate(labels, 1):
            label = row['label']
            print(f"[{idx}/{total}] Processing: {label}")
            
            try:
                # Generate synonyms
                synonyms = await generate_synonyms(label)
                
                if synonyms:
                    await update_label_synonyms(conn, label, synonyms)
                    print(f"  ✓ Added {len(synonyms)} synonyms: {', '.join(synonyms)}")
                    total_synonyms += len(synonyms)
                else:
                    print(f"  ✓ No synonyms generated")
                
                processed += 1
                
            except Exception as e:
                print(f"  ✗ Error: {e}")
                errors += 1
            
            # Brief pause to avoid rate limits
            if idx % 5 == 0:
                time.sleep(0.5)
        
        print("\n" + "=" * 80)
        print("SUMMARY")
        print("=" * 80)
        print(f"Labels processed: {processed}/{total}")
        print(f"Total synonyms generated: {total_synonyms}")
        print(f"Errors: {errors}")
        
        # Show some examples
        print("\nExample labels with synonyms:")
        examples = await conn.fetch("""
            SELECT label, synonyms
            FROM labels
            WHERE array_length(synonyms, 1) > 0
            ORDER BY label
            LIMIT 10
        """)
        
        for row in examples:
            print(f"  • {row['label']}: {', '.join(row['synonyms'])}")
        
        print("=" * 80)
        
    finally:
        await conn.close()
        print("\n✓ Database connection closed")


if __name__ == "__main__":
    import asyncio
    asyncio.run(process_all_labels())
