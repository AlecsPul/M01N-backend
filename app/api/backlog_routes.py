"""
Backlog API Routes
Endpoints for backlog card management and request ingestion.
"""
from fastapi import APIRouter, HTTPException, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID

from app.core.database import get_db
from app.schemas.backlog import BacklogIngestRequest, BacklogIngestResponse
from app.services.backlog_matcher import find_matching_card_id
from app.services.backlog_card_generation import generate_card_title_description
from app.services.backlog_repository import process_incoming_request


router = APIRouter(prefix="/api/v1/backlog", tags=["Backlog"])


@router.post(
    "/ingest",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Ingest new backlog request",
    description="""
    Process an incoming feature request or requirement.
    
    Flow:
    1. Searches for similar existing cards using AI similarity matching
    2. If match found (≥50% similarity): adds request to existing card
    3. If no match: generates title/description and creates new card
    
    All processing happens in English internally regardless of input language.
    """
)
async def ingest_backlog_request(
    request: BacklogIngestRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Ingest a backlog request and either match to existing card or create new one.
    
    Currently returns 204 No Content, but structured to easily return card_id later.
    To enable response, change status_code and uncomment return statement.
    """
    try:
        matched_card_id = await find_matching_card_id(
            db=db,
            prompt_text=request.prompt_text,
            comment_text=request.comment_text,
            threshold=50
        )
        
        is_new_card = matched_card_id == 0
        
        if is_new_card:
            title, description = await generate_card_title_description(
                prompt_text=request.prompt_text,
                comment_text=request.comment_text
            )
            
            card_id = await process_incoming_request(
                db=db,
                card_id=UUID('00000000-0000-0000-0000-000000000000'),
                title=title,
                description=description,
                prompt_text=request.prompt_text,
                comment_text=request.comment_text
            )
        else:
            card_id = await process_incoming_request(
                db=db,
                card_id=matched_card_id,
                title="",
                description="",
                prompt_text=request.prompt_text,
                comment_text=request.comment_text
            )
        
        # To enable response later, uncomment:
        # return BacklogIngestResponse(
        #     card_id=str(card_id),
        #     is_new=is_new_card
        # )
        
        return None
    
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid input: {str(e)}"
        )
    
    except Exception as e:
        error_msg = str(e).lower()
        if "openai" in error_msg or "api" in error_msg or "embedding" in error_msg:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"External service error: {str(e)}"
            )
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process backlog request: {str(e)}"
        )


@router.get(
    "/health",
    summary="Health check for backlog service"
)
async def health_check():
    """Health check endpoint for backlog service"""
    return {
        "status": "healthy",
        "service": "backlog",
        "endpoints": ["/ingest"]
    }
