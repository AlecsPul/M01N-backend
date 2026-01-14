"""
API Routes with Database Integration
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List
from uuid import UUID

from app.core.database import get_db
from app.models.models import Application, Card
from app.schemas.schemas import ApplicationLinkResponse, CardResponse, CardDeleteRequest, CardStatusToggleRequest, MessageResponse

router = APIRouter(prefix="/api/v1", tags=["application"])


@router.get("/application/links", response_model=List[ApplicationLinkResponse])
async def get_application_links(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db)
):
    """Get all application links (id, name, and link only)"""
    result = await db.execute(
        select(Application).offset(skip).limit(limit)
    )
    application = result.scalars().all()
    return application


@router.get("/cards", response_model=List[CardResponse])
async def get_all_cards(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db)
):
    """Get all cards from the database"""
    result = await db.execute(
        select(Card).offset(skip).limit(limit)
    )
    cards = result.scalars().all()
    return cards


@router.post("/dropcard", response_model=MessageResponse)
async def drop_card(
    request: CardDeleteRequest,
    db: AsyncSession = Depends(get_db)
):
    """Delete a card from the database"""
    try:
        card_uuid = UUID(request.card_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid card ID format")
    
    # Find the card
    result = await db.execute(
        select(Card).where(Card.id == card_uuid)
    )
    card = result.scalar_one_or_none()
    
    if not card:
        raise HTTPException(status_code=404, detail="Card not found")
    
    # Delete the card
    await db.delete(card)
    await db.commit()
    
    return MessageResponse(message=f"Card '{card.title}' deleted successfully")


@router.post("/cards/toggle-status", response_model=CardResponse)
async def toggle_card_status(
    request: CardStatusToggleRequest,
    db: AsyncSession = Depends(get_db)
):
    """Toggle card status between 0 (not completed) and 1 (completed)"""
    try:
        card_uuid = UUID(request.card_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid card ID format")
    
    # Find the card
    result = await db.execute(
        select(Card).where(Card.id == card_uuid)
    )
    card = result.scalar_one_or_none()
    
    if not card:
        raise HTTPException(status_code=404, detail="Card not found")
    
    # Toggle status between 0 and 1
    card.status = 1 if card.status == 0 else 0
    
    await db.commit()
    await db.refresh(card)
    
    return card
