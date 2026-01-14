"""
Backlog Card Matcher Module
Finds matching cards by comparing incoming prompts against existing card prompts.
"""
import random
from typing import List, Tuple, Optional, Union
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.models.models import Card, CardPromptComment
from app.services.backlog_similarity import evaluate_similarity


MATCH_THRESHOLD_PERCENT = 60


async def get_active_cards(db: AsyncSession) -> List[UUID]:
    """
    Retrieve all active card IDs from the database.
    
    Args:
        db: Database session
    
    Returns:
        List of active card UUIDs
    """
    result = await db.execute(
        select(Card.id).where(Card.status == 1)
    )
    return [row[0] for row in result.fetchall()]


async def get_random_prompt_for_card(
    db: AsyncSession,
    card_id: UUID,
    seed: Optional[int] = None
) -> Optional[Tuple[str, str]]:
    """
    Get a random prompt-comment pair for a specific card.
    
    Args:
        db: Database session
        card_id: UUID of the card
        seed: Optional random seed for deterministic testing
    
    Returns:
        Tuple of (prompt_text, comment_text) or None if no prompts exist
    """
    result = await db.execute(
        select(CardPromptComment.prompt_text, CardPromptComment.comment_text)
        .where(CardPromptComment.card_id == card_id)
    )
    prompts = result.fetchall()
    
    if not prompts:
        return None
    
    if seed is not None:
        random.seed(seed)
    
    selected = random.choice(prompts)
    return (selected[0], selected[1] or "")


async def find_matching_card_id(
    db: AsyncSession,
    prompt_text: str,
    comment_text: str = "",
    threshold: int = MATCH_THRESHOLD_PERCENT,
    seed: Optional[int] = None
) -> Union[UUID, int]:
    """
    Find a matching card by evaluating similarity against random prompts.
    
    Algorithm:
    1. Get all active cards
    2. For each card, randomly select ONE representative prompt
    3. Evaluate similarity between incoming text and card's prompt
    4. If similarity >= threshold, return that card_id
    5. If no match found, return 0
    
    Args:
        db: Database session
        prompt_text: Incoming prompt text (any language)
        comment_text: Optional comment text (any language)
        threshold: Minimum similarity percentage for a match (default: 60)
        seed: Optional random seed for deterministic testing
    
    Returns:
        card_id (UUID) if match found, 0 otherwise
    
    Example:
        card_id = await find_matching_card_id(
            db,
            prompt_text="Necesito integrar Stripe con mi CRM",
            comment_text="Es urgente",
            threshold=60
        )
        # Returns: UUID("...") or 0
    """
    try:
        active_cards = await get_active_cards(db)
        
        if not active_cards:
            return 0
        
        for card_id in active_cards:
            card_prompt_data = await get_random_prompt_for_card(db, card_id, seed)
            
            if card_prompt_data is None:
                continue
            
            card_prompt, card_comment = card_prompt_data
            
            similarity = await evaluate_similarity(
                incoming_prompt=prompt_text,
                incoming_comment=comment_text,
                card_prompt=card_prompt + ("\n" + card_comment if card_comment else "")
            )
            
            if similarity >= threshold:
                return card_id
        
        return 0
    
    except Exception as e:
        raise Exception(f"Error finding matching card: {str(e)}")


async def find_best_matching_card(
    db: AsyncSession,
    prompt_text: str,
    comment_text: str = "",
    threshold: int = MATCH_THRESHOLD_PERCENT,
    seed: Optional[int] = None
) -> Tuple[Union[UUID, int], int]:
    """
    Find the best matching card by evaluating all active cards.
    Returns the card with highest similarity above threshold.
    
    Args:
        db: Database session
        prompt_text: Incoming prompt text (any language)
        comment_text: Optional comment text (any language)
        threshold: Minimum similarity percentage for a match (default: 50)
        seed: Optional random seed for deterministic testing
    
    Returns:
        Tuple of (card_id, similarity_percent) where card_id is UUID or 0
    
    Example:
        card_id, similarity = await find_best_matching_card(
            db,
            prompt_text="Need CRM with Stripe integration",
            threshold=50
        )
        # Returns: (UUID("..."), 78) or (0, 0)
    """
    try:
        active_cards = await get_active_cards(db)
        
        if not active_cards:
            return (0, 0)
        
        best_match_id = 0
        best_similarity = 0
        
        for card_id in active_cards:
            card_prompt_data = await get_random_prompt_for_card(db, card_id, seed)
            
            if card_prompt_data is None:
                continue
            
            card_prompt, card_comment = card_prompt_data
            
            similarity = await evaluate_similarity(
                incoming_prompt=prompt_text,
                incoming_comment=comment_text,
                card_prompt=card_prompt + ("\n" + card_comment if card_comment else "")
            )
            
            if similarity > best_similarity and similarity >= threshold:
                best_similarity = similarity
                best_match_id = card_id
        
        return (best_match_id, best_similarity)
    
    except Exception as e:
        raise Exception(f"Error finding best matching card: {str(e)}")


async def get_card_details(db: AsyncSession, card_id: UUID) -> Optional[dict]:
    """
    Get card details by ID.
    
    Args:
        db: Database session
        card_id: UUID of the card
    
    Returns:
        Dict with card details or None if not found
    """
    result = await db.execute(
        select(Card).where(Card.id == card_id)
    )
    card = result.scalar_one_or_none()
    
    if card is None:
        return None
    
    return {
        "id": str(card.id),
        "title": card.title,
        "description": card.description,
        "status": card.status,
        "number_of_requests": card.number_of_requests,
        "created_at": card.created_at.isoformat() if card.created_at else None,
        "updated_at": card.updated_at.isoformat() if card.updated_at else None
    }
