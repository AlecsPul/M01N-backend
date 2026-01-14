"""
Matching Algorithm for Buyer Requirements vs Applications
Uses vector similarity + label/integration overlap for hybrid scoring.
"""
import math
from typing import List, Dict, Optional, Any, Tuple
import asyncpg


def sigmoid(x: float) -> float:
    """
    Sigmoid function for score normalization.
    Maps any real number to (0, 1) range.
    """
    return 1 / (1 + math.exp(-x))


def overlap_ratio(list_a: List[str], list_b: List[str]) -> float:
    """
    Calculate overlap ratio between two lists.
    Returns 0.0 if list_a is empty, otherwise intersection_size / len(list_a).
    
    Args:
        list_a: Buyer requirements (denominator)
        list_b: App features
    
    Returns:
        Ratio in [0.0, 1.0]
    """
    if not list_a:
        return 0.1
    
    set_a = set(s.lower().strip() for s in list_a)
    set_b = set(s.lower().strip() for s in list_b)
    
    intersection = set_a & set_b
    return len(intersection) / len(set_a)


def normalize_integration_key(key: str) -> str:
    """
    Normalize integration key to Title Case and trim whitespace.
    
    Args:
        key: Raw integration string
    
    Returns:
        Normalized string
    """
    return key.strip().title()


def extract_price_from_text(price_text: Optional[str]) -> Optional[float]:
    """
    Extract numeric price from text format.
    Handles formats like: "CHF 50", "50 CHF/mes", "CHF 50.00", "Gratis", etc.
    
    Args:
        price_text: Price text from database (e.g., "CHF 50", "Gratis")
    
    Returns:
        Float price value or None if not extractable or free
    """
    if not price_text:
        return None
    
    price_lower = price_text.lower().strip()
    
    # Check for free indicators
    free_keywords = ['gratis', 'free', 'kostenlos', 'gratuit']
    if any(keyword in price_lower for keyword in free_keywords):
        return 0.0
    
    # Extract numeric values using regex
    import re
    # Match numbers with optional decimal point
    numbers = re.findall(r'\d+(?:\.\d+)?', price_text)
    
    if numbers:
        # Return the first number found (usually the price)
        return float(numbers[0])
    
    return None


def is_within_budget(price_text: Optional[str], price_max: Optional[float]) -> bool:
    """
    Check if app price is within buyer's budget.
    
    Args:
        price_text: App price text from database
        price_max: Maximum price from buyer constraints (None = no limit)
    
    Returns:
        True if within budget or no price constraint exists, False otherwise
    """
    # If buyer has no price constraint, always return True
    if price_max is None:
        return True
    
    # Extract numeric price from text
    app_price = extract_price_from_text(price_text)
    
    # If we can't extract price, be optimistic (don't filter out)
    if app_price is None:
        return True
    
    # Compare: app is within budget if price <= max
    return app_price <= price_max


async def get_vector_candidates(
    conn: asyncpg.Connection,
    buyer_embedding: List[float],
    top_k: int
) -> List[Dict[str, Any]]:
    """
    Retrieve top K candidates by vector similarity using cosine distance.
    
    Args:
        conn: Database connection
        buyer_embedding: Query embedding vector (1536 floats)
        top_k: Number of candidates to retrieve
    
    Returns:
        List of dicts with app_search_id, app_id, and cosine_similarity
    """
    # Convert embedding to pgvector format
    embedding_str = '[' + ','.join(map(str, buyer_embedding)) + ']'
    
    query = """
        SELECT 
            s.id as app_search_id,
            s.app_id,
            a.price_text,
            1 - (s.embedding <=> $1::vector) as cosine_similarity
        FROM application_search s
        INNER JOIN application a ON s.app_id = a.id
        WHERE s.embedding IS NOT NULL
        ORDER BY s.embedding <=> $1::vector
        LIMIT $2
    """
    
    rows = await conn.fetch(query, embedding_str, top_k)
    
    return [
        {
            "app_search_id": str(row["app_search_id"]),
            "app_id": str(row["app_id"]),
            "price_text": row["price_text"],
            "cosine_similarity": float(row["cosine_similarity"])
        }
        for row in rows
    ]


async def get_labels_for_apps(
    conn: asyncpg.Connection,
    app_search_ids: List[str]
) -> Dict[str, List[str]]:
    """
    Batch fetch labels for multiple apps.
    
    Args:
        conn: Database connection
        app_search_ids: List of app_search_id UUIDs
    
    Returns:
        Dict mapping app_search_id -> list of labels
    """
    if not app_search_ids:
        return {}
    
    query = """
        SELECT app_search_id, label
        FROM application_labels
        WHERE app_search_id = ANY($1::uuid[])
    """
    
    rows = await conn.fetch(query, app_search_ids)
    
    result = {app_id: [] for app_id in app_search_ids}
    for row in rows:
        app_id = str(row["app_search_id"])
        result[app_id].append(row["label"])
    
    return result


async def get_integrations_for_apps(
    conn: asyncpg.Connection,
    app_search_ids: List[str]
) -> Dict[str, List[str]]:
    """
    Batch fetch integration keys for multiple apps.
    
    Args:
        conn: Database connection
        app_search_ids: List of app_search_id UUIDs
    
    Returns:
        Dict mapping app_search_id -> list of integration_keys
    """
    if not app_search_ids:
        return {}
    
    query = """
        SELECT app_search_id, integration_key
        FROM application_integration_keys
        WHERE app_search_id = ANY($1::uuid[])
    """
    
    rows = await conn.fetch(query, app_search_ids)
    
    result = {app_id: [] for app_id in app_search_ids}
    for row in rows:
        app_id = str(row["app_search_id"])
        result[app_id].append(row["integration_key"])
    
    return result


async def get_tags_for_apps(
    conn: asyncpg.Connection,
    app_ids: List[str]
) -> Dict[str, List[str]]:
    """
    Batch fetch tags for multiple apps.
    Note: apps_tags uses app_id (from application table), not app_search_id.
    
    Args:
        conn: Database connection
        app_ids: List of app_id UUIDs from application table
    
    Returns:
        Dict mapping app_id -> list of tags
    """
    if not app_ids:
        return {}
    
    # Check if apps_tags table exists (it may not be in all schemas)
    try:
        query = """
            SELECT app_id, tag
            FROM apps_tags
            WHERE app_id = ANY($1::uuid[])
        """
        
        rows = await conn.fetch(query, app_ids)
        
        result = {app_id: [] for app_id in app_ids}
        for row in rows:
            app_id = str(row["app_id"])
            result[app_id].append(row["tag"])
        
        return result
    except Exception:
        # If table doesn't exist or query fails, return empty dict
        return {app_id: [] for app_id in app_ids}


async def get_label_synonyms(
    conn: asyncpg.Connection,
    labels: List[str]
) -> Dict[str, List[str]]:
    """
    Get synonyms for given labels from the database.
    
    Args:
        conn: Database connection
        labels: List of label names
    
    Returns:
        Dict mapping label -> list of synonyms (including the label itself)
    """
    if not labels:
        return {}
    
    # Normalize labels for case-insensitive matching
    labels_lower = [label.lower() for label in labels]
    
    query = """
        SELECT label, synonyms
        FROM labels
        WHERE LOWER(label) = ANY($1::text[])
    """
    
    rows = await conn.fetch(query, labels_lower)
    
    result = {}
    for row in rows:
        label_name = row["label"].lower()
        synonyms_list = [label_name]  # Include the label itself
        
        # Add synonyms if they exist
        if row["synonyms"]:
            # synonyms is stored as TEXT[] array in DB
            synonyms_list.extend([s.lower() for s in row["synonyms"]])
        
        result[label_name] = synonyms_list
    
    return result


def check_must_have_requirements(
    buyer_struct: Dict[str, Any],
    app_labels: List[str],
    app_integrations: List[str],
    app_tags: List[str],
    label_synonyms: Dict[str, List[str]] = None
) -> bool:
    """
    Check if app meets all must-have requirements.
    Now considers label synonyms and tags when checking required labels/tags.
    
    Args:
        buyer_struct: Buyer requirements structure
        app_labels: Labels assigned to the app
        app_integrations: Integration keys of the app
        app_tags: Tags assigned to the app
        label_synonyms: Dict mapping labels to their synonyms (optional)
    
    Returns:
        True if all must-have requirements are met, False otherwise
    """
    labels_must = buyer_struct.get("labels_must", [])
    tag_must = buyer_struct.get("tag_must", [])
    integration_required = buyer_struct.get("integration_required", [])
    
    # Check required labels (with synonyms support)
    if labels_must:
        app_labels_lower = set(label.lower() for label in app_labels)
        
        for required_label in labels_must:
            required_lower = required_label.lower()
            
            # Check if the exact label exists
            if required_lower in app_labels_lower:
                continue
            
            # If synonyms are provided, check if any synonym matches
            if label_synonyms and required_lower in label_synonyms:
                synonyms = label_synonyms[required_lower]
                if any(syn in app_labels_lower for syn in synonyms):
                    continue
            
            # No match found (neither exact nor synonym)
            return False
    
    # Check required tags (case-insensitive comparison)
    if tag_must:
        app_tags_lower = set(tag.lower() for tag in app_tags)
        
        for required_tag in tag_must:
            if required_tag.lower() not in app_tags_lower:
                return False
    
    # Check required integrations (normalized comparison)
    if integration_required:
        app_integrations_normalized = set(
            normalize_integration_key(integ).lower() 
            for integ in app_integrations
        )
        for required_integ in integration_required:
            normalized_required = normalize_integration_key(required_integ).lower()
            if normalized_required not in app_integrations_normalized:
                return False
    
    return True


def calculate_hybrid_score(
    cosine_similarity: float,
    buyer_struct: Dict[str, Any],
    app_labels: List[str],
    app_integrations: List[str],
    app_tags: List[str]
) -> float:
    """
    Calculate hybrid score combining vector similarity and feature overlap.
    
    Weights:
    - 60% embedding similarity
    - 15% nice-to-have labels overlap
    - 10% nice-to-have tags overlap
    - 15% nice-to-have integrations overlap
    
    Args:
        cosine_similarity: Vector similarity score [0, 1]
        buyer_struct: Buyer requirements
        app_labels: App labels
        app_integrations: App integration keys
        app_tags: App tags
    
    Returns:
        Hybrid score in [0, 1] range
    """
    labels_nice = buyer_struct.get("labels_nice", [])
    tag_nice = buyer_struct.get("tag_nice", [])
    integration_nice = buyer_struct.get("integration_nice", [])
    
    # Normalize integrations for comparison
    app_integrations_normalized = [
        normalize_integration_key(integ) 
        for integ in app_integrations
    ]
    integration_nice_normalized = [
        normalize_integration_key(integ)
        for integ in integration_nice
    ]
    
    # Calculate overlap ratios
    labels_overlap = overlap_ratio(labels_nice, app_labels)
    tags_overlap = overlap_ratio(tag_nice, app_tags)
    integrations_overlap = overlap_ratio(
        integration_nice_normalized, 
        app_integrations_normalized
    )
    
    # Weighted hybrid score
    score = (
        (0.60 * cosine_similarity +
        0.15 * labels_overlap +
        0.10 * tags_overlap +
        0.15 * integrations_overlap)*0.3 +0.7
    )
    
    return score


def score_to_percentage(score: float) -> int:
    """
    Convert hybrid score to interpretable percentage using sigmoid.
    Maps [0, 1] score to [0, 100] percentage with sigmoid transformation.
    
    Args:
        score: Hybrid score in [0, 1]
    
    Returns:
        Percentage in [0, 100]
    """
    # Sigmoid transformation centered at 0.5
    # Multiplier 10 controls steepness
    transformed = sigmoid(10 * (score - 0.5))
    percentage = round(100 * transformed)
    
    # Clamp to [0, 100]
    return max(0, min(100, percentage))


async def run_match(
    conn: asyncpg.Connection,
    buyer_struct: Dict[str, Any],
    buyer_embedding: List[float],
    top_k: int = 30,
    top_n: int = 10
) -> List[Dict[str, Any]]:
    """
    Main matching algorithm: rank applications by similarity to buyer requirements.
    
    Algorithm:
    1. Retrieve top K candidates by vector similarity (cosine distance)
    2. Batch fetch labels and integrations for candidates
    3. Filter out apps that don't meet must-have requirements
    4. Calculate hybrid score (embedding + labels + integrations)
    5. Convert scores to percentages
    6. Return top N results
    
    Args:
        conn: Async database connection
        buyer_struct: Parsed buyer requirements dict with:
            - buyer_text: str
            - labels_must: List[str]
            - labels_nice: List[str]
            - tag_must: List[str]
            - tag_nice: List[str]
            - integration_required: List[str]
            - integration_nice: List[str]
            - constraints: {"price_max": float|None}
            - notes: str
        buyer_embedding: Query embedding vector (1536 floats)
        top_k: Number of candidates to retrieve from vector search
        top_n: Number of final results to return
    
    Returns:
        List of dicts with app_id and similarity_percent, sorted by similarity desc
    
    Raises:
        ValueError: If all arrays (labels, tags, integrations) are empty
    """
    # Step 0: Validate that buyer has at least some requirements
    labels_must = buyer_struct.get("labels_must", [])
    labels_nice = buyer_struct.get("labels_nice", [])
    tag_must = buyer_struct.get("tag_must", [])
    tag_nice = buyer_struct.get("tag_nice", [])
    integration_required = buyer_struct.get("integration_required", [])
    integration_nice = buyer_struct.get("integration_nice", [])
    
    has_labels = bool(labels_must or labels_nice)
    has_tags = bool(tag_must or tag_nice)
    has_integrations = bool(integration_required or integration_nice)
    
    if not (has_labels or has_tags or has_integrations):
        raise ValueError(
            "Invalid buyer requirements: at least one of labels, tags, or integrations must be specified. "
            "Cannot match applications without any criteria."
        )
    
    # Step 1: Vector search for top K candidates
    candidates = await get_vector_candidates(conn, buyer_embedding, top_k)
    
    if not candidates:
        return []
    
    # Extract app_search_ids for batch queries
    app_search_ids = [c["app_search_id"] for c in candidates]
    app_ids = [c["app_id"] for c in candidates]
    
    # Step 2: Batch fetch labels, integrations, and tags
    labels_map = await get_labels_for_apps(conn, app_search_ids)
    integrations_map = await get_integrations_for_apps(conn, app_search_ids)
    tags_map = await get_tags_for_apps(conn, app_ids)
    
    # Step 2.5: Get synonyms for must-have labels
    labels_must = buyer_struct.get("labels_must", [])
    label_synonyms = await get_label_synonyms(conn, labels_must)
    
    # Step 3: Score and filter candidates
    scored_results = []
    
    for candidate in candidates:
        app_search_id = candidate["app_search_id"]
        app_id = candidate["app_id"]
        price_text = candidate.get("price_text")
        cosine_sim = candidate["cosine_similarity"]
        
        app_labels = labels_map.get(app_search_id, [])
        app_integrations = integrations_map.get(app_search_id, [])
        app_tags = tags_map.get(app_id, [])
        
        # Filter: Check must-have requirements (with synonyms and tags)
        meets_requirements = check_must_have_requirements(
            buyer_struct,
            app_labels,
            app_integrations,
            app_tags,
            label_synonyms
        )
        
        # Filter: Check price constraint
        price_max_raw = buyer_struct.get("constraints", {}).get("price_max")
        # Process price_max: if it's a string with "gratis"/"gratuito", convert to 0.0
        if isinstance(price_max_raw, str):
            price_max = extract_price_from_text(price_max_raw)
        else:
            price_max = price_max_raw
        within_budget = is_within_budget(price_text, price_max)
        
        if not meets_requirements or not within_budget:
            # Strategy: Assign very low score instead of completely discarding
            # This allows some visibility but ranks them at the bottom
            similarity_percent = 5
        else:
            # Calculate hybrid score
            hybrid_score = calculate_hybrid_score(
                cosine_sim,
                buyer_struct,
                app_labels,
                app_integrations,
                app_tags
            )
            
            # Convert to percentage
            similarity_percent = score_to_percentage(hybrid_score)
        
        scored_results.append({
            "app_id": app_id,
            "similarity_percent": similarity_percent
        })
    
    # Step 4: Sort by similarity percentage (descending)
    scored_results.sort(key=lambda x: x["similarity_percent"], reverse=True)
    
    # Step 5: Return top N
    return scored_results[:top_n]


# Example usage
async def example_usage():
    """Example of how to use the matching algorithm."""
    import os
    from dotenv import load_dotenv
    
    load_dotenv()
    DATABASE_URL = os.getenv("DATABASE_URL")
    
    # Example buyer structure (from parser)
    buyer_struct = {
        "buyer_text": "Necesito un CRM con integración a Stripe",
        "labels_must": ["CRM"],
        "labels_nice": ["Analytics", "Reporting"],
        "integration_required": ["Stripe"],
        "integration_nice": ["Zapier"],
        "constraints": {"price_max": 100.0},
        "notes": ""
    }
    
    # Example embedding (in real usage, get from OpenAI)
    buyer_embedding = [0.01] * 1536  # Placeholder
    
    # Run matching
    conn = await asyncpg.connect(DATABASE_URL)
    try:
        results = await run_match(
            conn,
            buyer_struct,
            buyer_embedding,
            top_k=30,
            top_n=10
        )
        
        print("Top matches:")
        for i, result in enumerate(results, 1):
            print(f"{i}. App ID: {result['app_id']}, "
                  f"Similarity: {result['similarity_percent']}%")
    finally:
        await conn.close()


if __name__ == "__main__":
    import asyncio
    asyncio.run(example_usage())
