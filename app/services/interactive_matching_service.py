"""
Interactive Matching Service
Execute matching algorithm with composed prompt from interactive session.
"""
from typing import List, Dict, Any, Tuple
import asyncpg
from app.matching.algorithm import run_match
from app.schemas.interactive_match import SessionState
from app.services.prompt_composer import compose_final_prompt, format_for_matching_service
from app.core.openai_client import client


async def generate_embedding(text: str) -> List[float]:
    """
    Generate embedding vector for text using OpenAI.
    
    Args:
        text: Text to embed
        
    Returns:
        Embedding vector (1536 floats)
    """
    response = await client.embeddings.create(
        model="text-embedding-3-small",
        input=text[:8000]
    )
    
    return response.data[0].embedding


async def run_final_match(
    conn: asyncpg.Connection,
    state: SessionState,
    top_k: int = 30,
    top_n: int = 10
) -> Tuple[str, List[Dict[str, Any]]]:
    """
    Execute matching algorithm using composed prompt from interactive session.
    
    Args:
        conn: Database connection
        state: Interactive session state (must be valid)
        top_k: Number of candidates to consider
        top_n: Number of results to return
        
    Returns:
        Tuple of (final_prompt_text, match_results)
        
    Raises:
        ValueError: If state is not valid
    """
    if not state.is_valid:
        raise ValueError("Session state is not valid. Cannot run matching.")
    
    final_prompt_text = compose_final_prompt(state)
    
    buyer_struct = format_for_matching_service(state)
    
    buyer_embedding = await generate_embedding(final_prompt_text)
    
    matches = await run_match(
        conn,
        buyer_struct,
        buyer_embedding,
        top_k=top_k,
        top_n=top_n
    )
    
    return final_prompt_text, matches


async def get_app_names(conn: asyncpg.Connection, app_ids: List[str]) -> Dict[str, str]:
    """
    Batch fetch application names.
    
    Args:
        conn: Database connection
        app_ids: List of application UUIDs
        
    Returns:
        Dict mapping app_id -> app_name
    """
    if not app_ids:
        return {}
    
    query = """
        SELECT id, name
        FROM application
        WHERE id = ANY($1::uuid[])
    """
    
    rows = await conn.fetch(query, app_ids)
    
    return {str(row["id"]): row["name"] for row in rows}


async def run_final_match_with_names(
    conn: asyncpg.Connection,
    state: SessionState,
    top_k: int = 30,
    top_n: int = 10
) -> Dict[str, Any]:
    """
    Execute matching and enrich results with application names.
    
    Args:
        conn: Database connection
        state: Interactive session state (must be valid)
        top_k: Number of candidates to consider
        top_n: Number of results to return
        
    Returns:
        Dict with final_prompt, buyer_struct, and enriched results
        
    Raises:
        ValueError: If state is not valid
    """
    final_prompt_text, matches = await run_final_match(conn, state, top_k, top_n)
    
    app_ids = [match["app_id"] for match in matches]
    app_names = await get_app_names(conn, app_ids)
    
    results = [
        {
            "app_id": match["app_id"],
            "name": app_names.get(match["app_id"], "Unknown"),
            "similarity_percent": match["similarity_percent"]
        }
        for match in matches
    ]
    
    buyer_struct = format_for_matching_service(state)
    
    return {
        "final_prompt": final_prompt_text,
        "buyer_struct": buyer_struct,
        "results": results
    }
