"""
API Routes with Database Integration
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List
from uuid import UUID

from app.core.database import get_db
from app.models.models import Application, Card, CardPromptComment, ApplicationClick, AppTag
from app.schemas.schemas import ApplicationLinkResponse, ApplicationClickRequest, CardResponse, CardDeleteRequest, CardStatusToggleRequest, CardPromptCommentResponse, CardUpvoteRequest, MessageResponse, ClickStatsResponse, CategoryAnalyticsResponse

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


@router.get("/cards/{card_id}", response_model=CardResponse)
async def get_card(
    card_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Get a specific card by ID"""
    try:
        card_uuid = UUID(card_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid card ID format")
    
    # Find the card
    result = await db.execute(
        select(Card).where(Card.id == card_uuid)
    )
    card = result.scalar_one_or_none()
    
    if not card:
        raise HTTPException(status_code=404, detail="Card not found")
    
    return card


@router.get("/cards/{card_id}/comments", response_model=List[CardPromptCommentResponse])
async def get_card_comments(
    card_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Get all prompts and comments for a specific card"""
    try:
        card_uuid = UUID(card_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid card ID format")
    
    # Verify card exists
    card_result = await db.execute(
        select(Card).where(Card.id == card_uuid)
    )
    card = card_result.scalar_one_or_none()
    
    if not card:
        raise HTTPException(status_code=404, detail="Card not found")
    
    # Get all prompts and comments for this card
    result = await db.execute(
        select(CardPromptComment).where(CardPromptComment.card_id == card_uuid)
    )
    comments = result.scalars().all()
    
    return comments


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


@router.post("/cards/upvote", response_model=CardResponse)
async def upvote_card(
    request: CardUpvoteRequest,
    db: AsyncSession = Depends(get_db)
):
    """Increment the upvote count (number_of_requests) for a card"""
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
    
    # Increment upvote count (initialize to 0 if None)
    card.upvote = (card.upvote or 0) + 1
    
    await db.commit()
    await db.refresh(card)
    
    return card


@router.post("/application/click", response_model=ApplicationLinkResponse)
async def increment_application_click(
    request: ApplicationClickRequest,
    db: AsyncSession = Depends(get_db)
):
    """Record a click for an application (for analytics and statistics)"""
    try:
        app_uuid = UUID(request.app_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid application ID format")
    
    # Verify application exists
    result = await db.execute(
        select(Application).where(Application.id == app_uuid)
    )
    app = result.scalar_one_or_none()
    
    if not app:
        raise HTTPException(status_code=404, detail="Application not found")
    
    # Insert a new click record for analytics
    new_click = ApplicationClick(app_id=app_uuid)
    db.add(new_click)
    await db.commit()
    await db.refresh(app)
    
    return app


@router.get("/application/clicks/stats", response_model=List[ClickStatsResponse])
async def get_click_statistics(
    category: str = None,
    db: AsyncSession = Depends(get_db)
):
    """Get click statistics for applications, optionally filtered by category"""
    from sqlalchemy import func
    
    # Base query to count clicks per application
    query = select(
        Application.id,
        Application.name,
        func.count(ApplicationClick.id).label('click_count')
    ).outerjoin(
        ApplicationClick, Application.id == ApplicationClick.app_id
    )
    
    # If category filter is provided, join with AppTag
    if category:
        query = query.join(
            AppTag, Application.id == AppTag.app_id
        ).where(
            AppTag.tag == category
        )
    
    # Group by application
    query = query.group_by(Application.id, Application.name)
    
    result = await db.execute(query)
    stats = result.all()
    
    # Fetch tags for each app
    response_data = []
    for app_id, app_name, click_count in stats:
        # Get tags for this app
        tags_result = await db.execute(
            select(AppTag.tag).where(AppTag.app_id == app_id)
        )
        tags = [tag[0] for tag in tags_result.all()]
        
        response_data.append(ClickStatsResponse(
            app_id=str(app_id),
            app_name=app_name,
            click_count=click_count,
            tags=tags
        ))
    
    return response_data


@router.get("/application/clicks/category-analytics", response_model=CategoryAnalyticsResponse)
async def get_category_analytics(
    category: str = None,
    db: AsyncSession = Depends(get_db)
):
    """Get click analytics showing percentage of clicks from a specific category"""
    from sqlalchemy import func
    
    # Get total clicks across all applications
    total_clicks_result = await db.execute(
        select(func.count(ApplicationClick.id))
    )
    total_clicks = total_clicks_result.scalar() or 0
    
    if category:
        # Get clicks for apps in the specified category
        category_clicks_result = await db.execute(
            select(func.count(ApplicationClick.id))
            .join(Application, ApplicationClick.app_id == Application.id)
            .join(AppTag, Application.id == AppTag.app_id)
            .where(AppTag.tag == category)
        )
        category_clicks = category_clicks_result.scalar() or 0
        
        # Get count of apps in this category
        app_count_result = await db.execute(
            select(func.count(func.distinct(Application.id)))
            .join(AppTag, Application.id == AppTag.app_id)
            .where(AppTag.tag == category)
        )
        app_count = app_count_result.scalar() or 0
    else:
        # If no category specified, category_clicks = total_clicks
        category_clicks = total_clicks
        app_count_result = await db.execute(
            select(func.count(Application.id))
        )
        app_count = app_count_result.scalar() or 0
    
    # Calculate percentage
    percentage = (category_clicks / total_clicks * 100) if total_clicks > 0 else 0.0
    
    return CategoryAnalyticsResponse(
        category=category,
        category_clicks=category_clicks,
        total_clicks=total_clicks,
        percentage=round(percentage, 2),
        app_count=app_count
    )
