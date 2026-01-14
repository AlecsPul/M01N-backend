"""
Backlog Repository Module
Database operations for backlog cards and prompts.
"""
from uuid import UUID, uuid4
from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from app.models.models import Card, CardPromptComment


async def add_prompt_to_existing_card(
    db: AsyncSession,
    card_id: UUID,
    prompt_text: str,
    comment_text: str = ""
) -> UUID:
    """
    Add a new prompt to an existing card and increment request count.
    Uses transaction to ensure atomicity.
    
    Args:
        db: Database session
        card_id: UUID of existing card
        prompt_text: Prompt text (required)
        comment_text: Optional comment text
    
    Returns:
        card_id of the updated card
    
    Raises:
        ValueError: If prompt_text is empty
        Exception: If card doesn't exist or transaction fails
    """
    if not prompt_text or not prompt_text.strip():
        raise ValueError("prompt_text is required and cannot be empty")
    
    try:
        result = await db.execute(
            select(Card).where(Card.id == card_id)
        )
        card = result.scalar_one_or_none()
        
        if card is None:
            raise Exception(f"Card {card_id} not found")
        
        new_prompt = CardPromptComment(
            id=uuid4(),
            card_id=card_id,
            prompt_text=prompt_text.strip(),
            comment_text=comment_text.strip() if comment_text else None
        )
        db.add(new_prompt)
        
        await db.execute(
            update(Card)
            .where(Card.id == card_id)
            .values(number_of_requests=Card.number_of_requests + 1)
        )
        
        await db.commit()
        
        return card_id
    
    except Exception as e:
        await db.rollback()
        raise Exception(f"Failed to add prompt to card: {str(e)}")


async def create_new_card_with_prompt(
    db: AsyncSession,
    title: str,
    description: str,
    prompt_text: str,
    comment_text: str = ""
) -> UUID:
    """
    Create a new card with initial prompt.
    Uses transaction to ensure atomicity.
    
    Args:
        db: Database session
        title: Card title
        description: Card description
        prompt_text: Initial prompt text (required)
        comment_text: Optional comment text
    
    Returns:
        card_id of newly created card
    
    Raises:
        ValueError: If required fields are empty
        Exception: If transaction fails
    """
    if not title or not title.strip():
        raise ValueError("title is required and cannot be empty")
    
    if not description or not description.strip():
        raise ValueError("description is required and cannot be empty")
    
    if not prompt_text or not prompt_text.strip():
        raise ValueError("prompt_text is required and cannot be empty")
    
    try:
        new_card = Card(
            id=uuid4(),
            title=title.strip(),
            description=description.strip(),
            status=1,
            number_of_requests=1,
            upvote=1,
            created_by_bexio=True
        )
        db.add(new_card)
        
        new_prompt = CardPromptComment(
            id=uuid4(),
            card_id=new_card.id,
            prompt_text=prompt_text.strip(),
            comment_text=comment_text.strip() if comment_text else None
        )
        db.add(new_prompt)
        
        await db.commit()
        
        return new_card.id
    
    except Exception as e:
        await db.rollback()
        raise Exception(f"Failed to create new card: {str(e)}")


async def create_manual_card(
    db: AsyncSession,
    title: str,
    description: str
) -> UUID:
    """
    Create a new card manually (created by developers, not from Bexio).
    This card has no associated prompts/comments and created_by_bexio = False.
    
    Args:
        db: Database session
        title: Card title
        description: Card description
    
    Returns:
        card_id of newly created card
    
    Raises:
        ValueError: If required fields are empty
        Exception: If transaction fails
    """
    if not title or not title.strip():
        raise ValueError("title is required and cannot be empty")
    
    if not description or not description.strip():
        raise ValueError("description is required and cannot be empty")
    
    try:
        new_card = Card(
            id=uuid4(),
            title=title.strip(),
            description=description.strip(),
            status=1,
            number_of_requests=0,
            upvote=1,
            created_by_bexio=False
        )
        db.add(new_card)
        
        await db.commit()
        
        return new_card.id
    
    except Exception as e:
        await db.rollback()
        raise Exception(f"Failed to create manual card: {str(e)}")


async def increment_card_requests(
    db: AsyncSession,
    card_id: UUID
) -> None:
    """
    Increment the number_of_requests counter for a card.
    
    Args:
        db: Database session
        card_id: UUID of the card
    
    Raises:
        Exception: If card doesn't exist or update fails
    """
    try:
        result = await db.execute(
            select(Card).where(Card.id == card_id)
        )
        card = result.scalar_one_or_none()
        
        if card is None:
            raise Exception(f"Card {card_id} not found")
        
        await db.execute(
            update(Card)
            .where(Card.id == card_id)
            .values(number_of_requests=Card.number_of_requests + 1)
        )
        
        await db.commit()
    
    except Exception as e:
        await db.rollback()
        raise Exception(f"Failed to increment card requests: {str(e)}")


async def get_card_by_id(
    db: AsyncSession,
    card_id: UUID
) -> Optional[Card]:
    """
    Retrieve a card by its ID.
    
    Args:
        db: Database session
        card_id: UUID of the card
    
    Returns:
        Card object or None if not found
    """
    result = await db.execute(
        select(Card).where(Card.id == card_id)
    )
    return result.scalar_one_or_none()


async def get_card_prompts(
    db: AsyncSession,
    card_id: UUID
) -> List[CardPromptComment]:
    """
    Get all prompts for a specific card.
    
    Args:
        db: Database session
        card_id: UUID of the card
    
    Returns:
        List of CardPromptComment objects
    """
    result = await db.execute(
        select(CardPromptComment)
        .where(CardPromptComment.card_id == card_id)
        .order_by(CardPromptComment.created_at.desc())
    )
    return result.scalars().all()


async def update_card_status(
    db: AsyncSession,
    card_id: UUID,
    status: int
) -> None:
    """
    Update card status.
    
    Args:
        db: Database session
        card_id: UUID of the card
        status: New status value (0 or 1)
    
    Raises:
        ValueError: If status is invalid
        Exception: If card doesn't exist or update fails
    """
    if status not in [0, 1]:
        raise ValueError("status must be 0 or 1")
    
    try:
        result = await db.execute(
            select(Card).where(Card.id == card_id)
        )
        card = result.scalar_one_or_none()
        
        if card is None:
            raise Exception(f"Card {card_id} not found")
        
        await db.execute(
            update(Card)
            .where(Card.id == card_id)
            .values(status=status)
        )
        
        await db.commit()
    
    except Exception as e:
        await db.rollback()
        raise Exception(f"Failed to update card status: {str(e)}")


async def process_incoming_request(
    db: AsyncSession,
    card_id: UUID,
    title: str,
    description: str,
    prompt_text: str,
    comment_text: str = ""
) -> UUID:
    """
    Process an incoming request: either add to existing card or create new one.
    This is the main orchestrator function for the backlog flow.
    
    Args:
        db: Database session
        card_id: UUID if match found, or UUID with all zeros if no match
        title: Generated title (used only if creating new card)
        description: Generated description (used only if creating new card)
        prompt_text: Original prompt text
        comment_text: Optional comment text
    
    Returns:
        card_id (existing or newly created)
    
    Example:
        # No match found (card_id is zero UUID)
        card_id = await process_incoming_request(
            db,
            card_id=UUID('00000000-0000-0000-0000-000000000000'),
            title="New feature request",
            description="Description here",
            prompt_text="User request",
            comment_text=""
        )
        # Returns: newly created card_id
        
        # Match found
        card_id = await process_incoming_request(
            db,
            card_id=existing_uuid,
            title="ignored",
            description="ignored",
            prompt_text="Similar request",
            comment_text=""
        )
        # Returns: existing_uuid with incremented counter
    """
    zero_uuid = UUID('00000000-0000-0000-0000-000000000000')
    
    if card_id == zero_uuid or card_id == 0:
        return await create_new_card_with_prompt(
            db,
            title=title,
            description=description,
            prompt_text=prompt_text,
            comment_text=comment_text
        )
    else:
        return await add_prompt_to_existing_card(
            db,
            card_id=card_id,
            prompt_text=prompt_text,
            comment_text=comment_text
        )
