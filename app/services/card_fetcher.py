"""
Card Fetcher Module
Read-only database operations for fetching card details.
"""
from uuid import UUID
from typing import Optional, Dict
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.models import Card


async def get_card_by_id(
    db: AsyncSession,
    card_id: UUID
) -> Optional[Dict[str, any]]:
    """
    Fetch a card by its ID.
    
    Args:
        db: Database session
        card_id: UUID of the card
    
    Returns:
        Dictionary with card data {id, title, description} or None if not found
    """
    try:
        result = await db.execute(
            select(Card).where(Card.id == card_id)
        )
        card = result.scalar_one_or_none()
        
        if card is None:
            return None
        
        return {
            "id": card.id,
            "title": card.title,
            "description": card.description
        }
    except Exception as e:
        raise Exception(f"Error fetching card {card_id}: {str(e)}")
