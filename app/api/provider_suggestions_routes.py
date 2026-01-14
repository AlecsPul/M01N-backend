"""
Provider Suggestions API Routes
Endpoint for finding external provider suggestions for backlog cards.
"""
from fastapi import APIRouter, HTTPException, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID

from app.core.database import get_db
from app.schemas.provider_suggestions import ProviderSuggestionResponse
from app.services.card_fetcher import get_card_by_id
from app.services.provider_suggestions.tavily_service import suggest_provider_with_tavily


router = APIRouter(prefix="/api/v1/backlog", tags=["Provider Suggestions"])


@router.post(
    "/{card_id}/suggest-provider",
    status_code=status.HTTP_200_OK,
    response_model=ProviderSuggestionResponse,
    summary="Get external provider suggestion for a backlog card",
    description="""
    Given a backlog card ID, fetches the card details and returns a suggestion
    for an external provider/company that offers a matching solution.
    
    Uses Tavily Search API for real web search:
    - Generates optimized search queries from card description
    - Searches the web for relevant software providers
    - Ranks results by relevance and keyword matching
    - Returns the best matching company with reasoning
    
    Requires TAVILY_API_KEY environment variable.
    Get free API key at: https://tavily.com
    """
)
async def suggest_provider_for_card(
    card_id: UUID,
    db: AsyncSession = Depends(get_db)
) -> ProviderSuggestionResponse:
    """
    Get external provider suggestion for a backlog card.
    
    Args:
        card_id: UUID of the backlog card
        db: Database session (injected)
    
    Returns:
        ProviderSuggestionResponse with company details and reasoning
    
    Raises:
        404: Card not found
        502: Error with web search or processing suggestion
    """
    # Fetch card from database
    card = await get_card_by_id(db, card_id)
    
    if card is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Card with ID {card_id} not found"
        )
    
    # Get provider suggestion using Tavily web search
    try:
        suggestion = await suggest_provider_with_tavily(
            card_title=card["title"],
            card_description=card["description"]
        )
        
        # Build response
        return ProviderSuggestionResponse(
            card_id=card_id,
            company_name=suggestion["company_name"],
            company_url=suggestion["company_url"],
            marketplace_url=suggestion["marketplace_url"],
            reasoning_brief=suggestion["reasoning_brief"]
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Error generating provider suggestion: {str(e)}"
        )
