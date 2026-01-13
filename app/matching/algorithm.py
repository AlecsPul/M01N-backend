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
            1 - (s.embedding <=> $1::vector) as cosine_similarity
        FROM application_search s
        WHERE s.embedding IS NOT NULL
        ORDER BY s.embedding <=> $1::vector
        LIMIT $2
    """
    
    rows = await conn.fetch(query, embedding_str, top_k)
    
    return [
        {
            "app_search_id": str(row["app_search_id"]),
            "app_id": str(row["app_id"]),
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
    label_synonyms: Dict[str, List[str]] = None
) -> bool:
    """
    Check if app meets all must-have requirements.
    Now considers label synonyms when checking required labels.
    
    Args:
        buyer_struct: Buyer requirements structure
        app_labels: Labels assigned to the app
        app_integrations: Integration keys of the app
        label_synonyms: Dict mapping labels to their synonyms (optional)
    
    Returns:
        True if all must-have requirements are met, False otherwise
    """
    labels_must = buyer_struct.get("labels_must", [])
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
    app_integrations: List[str]
) -> float:
    """
    Calculate hybrid score combining vector similarity and feature overlap.
    
    Weights:
    - 80% embedding similarity
    - 15% nice-to-have labels overlap
    - 5% nice-to-have integrations overlap
    
    Args:
        cosine_similarity: Vector similarity score [0, 1]
        buyer_struct: Buyer requirements
        app_labels: App labels
        app_integrations: App integration keys
    
    Returns:
        Hybrid score in [0, 1] range
    """
    labels_nice = buyer_struct.get("labels_nice", [])
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
    integrations_overlap = overlap_ratio(
        integration_nice_normalized, 
        app_integrations_normalized
    )
    
    # Weighted hybrid score
    score = (
        (0.60 * cosine_similarity +
        0.15 * labels_overlap +
        0.25 * integrations_overlap)*0.3 +0.7
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
            - integration_required: List[str]
            - integration_nice: List[str]
            - constraints: {"price_max": float|None}
            - notes: str
        buyer_embedding: Query embedding vector (1536 floats)
        top_k: Number of candidates to retrieve from vector search
        top_n: Number of final results to return
    
    Returns:
        List of dicts with app_id and similarity_percent, sorted by similarity desc
    """
    # Step 1: Vector search for top K candidates
    candidates = await get_vector_candidates(conn, buyer_embedding, top_k)
    
    if not candidates:
        return []
    
    # Extract app_search_ids for batch queries
    app_search_ids = [c["app_search_id"] for c in candidates]
    
    # Step 2: Batch fetch labels and integrations
    labels_map = await get_labels_for_apps(conn, app_search_ids)
    integrations_map = await get_integrations_for_apps(conn, app_search_ids)
    
    # Step 2.5: Get synonyms for must-have labels
    labels_must = buyer_struct.get("labels_must", [])
    label_synonyms = await get_label_synonyms(conn, labels_must)
    
    # Step 3: Score and filter candidates
    scored_results = []
    
    for candidate in candidates:
        app_search_id = candidate["app_search_id"]
        app_id = candidate["app_id"]
        cosine_sim = candidate["cosine_similarity"]
        
        app_labels = labels_map.get(app_search_id, [])
        app_integrations = integrations_map.get(app_search_id, [])
        
        # Filter: Check must-have requirements (with synonyms)
        meets_requirements = check_must_have_requirements(
            buyer_struct,
            app_labels,
            app_integrations,
            label_synonyms
        )
        
        if not meets_requirements:
            # Strategy: Assign very low score instead of completely discarding
            # This allows some visibility but ranks them at the bottom
            similarity_percent = 5
        else:
            # Calculate hybrid score
            hybrid_score = calculate_hybrid_score(
                cosine_sim,
                buyer_struct,
                app_labels,
                app_integrations
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
