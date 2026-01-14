"""
Backlog Similarity Evaluation Module
Compares incoming requests against backlog card prompts using embeddings and cosine similarity.
"""
import math
import time
from typing import List, Tuple
from app.matching.algorithm import sigmoid
from app.core.openai_client import get_embedding, normalize_to_english


def cosine_similarity(vec_a: List[float], vec_b: List[float]) -> float:
    """
    Calculate cosine similarity between two vectors.
    
    Args:
        vec_a: First embedding vector
        vec_b: Second embedding vector
    
    Returns:
        Cosine similarity score in [-1, 1], typically [0, 1] for embeddings
    """
    if len(vec_a) != len(vec_b):
        raise ValueError(f"Vector dimensions do not match: {len(vec_a)} vs {len(vec_b)}")
    
    dot_product = sum(a * b for a, b in zip(vec_a, vec_b))
    norm_a = math.sqrt(sum(a * a for a in vec_a))
    norm_b = math.sqrt(sum(b * b for b in vec_b))
    
    if norm_a == 0 or norm_b == 0:
        return 0.0
    
    return dot_product / (norm_a * norm_b)


def similarity_to_percentage(similarity: float) -> int:
    """
    Convert cosine similarity to interpretable percentage using sigmoid.
    Reuses the same transformation as the marketplace matching algorithm.
    
    Args:
        similarity: Cosine similarity score in [0, 1]
    
    Returns:
        Percentage in [0, 100]
    """
    transformed = sigmoid(10 * (similarity - 0.5))
    percentage = round(100 * transformed)
    return max(0, min(100, percentage))


async def compute_embedding(text: str) -> List[float]:
    """
    Generate embedding vector for text using OpenAI.
    Reuses the same model as the marketplace matching algorithm.
    
    Args:
        text: Text to embed (should be in English)
    
    Returns:
        Embedding vector (1536 dimensions)
    """
    return await get_embedding(text)


async def evaluate_similarity(
    incoming_prompt: str,
    incoming_comment: str,
    card_prompt: str
) -> int:
    """
    Evaluate similarity between incoming request and backlog card.
    
    Process:
    1. Normalize incoming text to English
    2. Normalize card prompt to English
    3. Generate embeddings for both
    4. Calculate cosine similarity
    5. Convert to percentage (0-100)
    
    Args:
        incoming_prompt: New request prompt text
        incoming_comment: Optional comment/clarification
        card_prompt: Representative prompt of existing card
    
    Returns:
        Similarity percentage (0-100)
    
    Example:
        similarity = await evaluate_similarity(
            incoming_prompt="Necesito integrar Stripe con mi CRM",
            incoming_comment="Es urgente para mi empresa",
            card_prompt="Add Stripe payment integration to CRM module"
        )
        # Returns: 78 (high similarity)
    """
    try:
        # Combine and normalize incoming text
        combined_incoming = incoming_prompt.strip()
        if incoming_comment and incoming_comment.strip():
            combined_incoming += "\n" + incoming_comment.strip()
        
        incoming_text = await normalize_to_english(combined_incoming)
        card_text = await normalize_to_english(card_prompt)
        
        incoming_embedding = await compute_embedding(incoming_text)
        card_embedding = await compute_embedding(card_text)
        
        similarity = cosine_similarity(incoming_embedding, card_embedding)
        
        percentage = similarity_to_percentage(similarity)
        
        return percentage
    
    except Exception as e:
        raise Exception(f"Error evaluating similarity: {str(e)}")


async def batch_evaluate_similarity(
    incoming_prompt: str,
    incoming_comment: str,
    card_prompts: List[Tuple[str, str]]
) -> List[Tuple[str, int]]:
    """
    Evaluate similarity against multiple cards in batch.
    
    Args:
        incoming_prompt: New request prompt text
        incoming_comment: Optional comment/clarification
        card_prompts: List of (card_id, representative_prompt) tuples
    
    Returns:
        List of (card_id, similarity_percent) tuples, sorted by similarity desc
    
    Example:
        results = await batch_evaluate_similarity(
            incoming_prompt="Need CRM with Stripe",
            incoming_comment="",
            card_prompts=[
                ("card-123", "CRM Stripe integration"),
                ("card-456", "Email marketing automation")
            ]
        )
        # Returns: [("card-123", 85), ("card-456", 32)]
    """
    try:
        # Combine and normalize incoming text
        combined_incoming = incoming_prompt.strip()
        if incoming_comment and incoming_comment.strip():
            combined_incoming += "\n" + incoming_comment.strip()
        
        incoming_text = await normalize_to_english(combined_incoming)
        incoming_embedding = await compute_embedding(incoming_text)
        
        results = []
        
        for card_id, card_prompt in card_prompts:
            card_text = await normalize_to_english(card_prompt)
            card_embedding = await compute_embedding(card_text)
            
            similarity = cosine_similarity(incoming_embedding, card_embedding)
            percentage = similarity_to_percentage(similarity)
            
            results.append((card_id, percentage))
        
        results.sort(key=lambda x: x[1], reverse=True)
        
        return results
    
    except Exception as e:
        raise Exception(f"Error in batch similarity evaluation: {str(e)}")
