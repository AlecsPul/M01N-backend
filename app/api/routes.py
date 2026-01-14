"""
API Routes with Database Integration
"""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List

from app.core.database import get_db
from app.models.models import Application, Card
from app.schemas.schemas import ApplicationLinkResponse, CardResponse

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
