"""
Matching API Routes
Endpoints for application matching based on buyer requirements.
"""
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
import os

from app.services.matching_service import MatchingService
from app.core.config import settings

router = APIRouter(prefix="/api/v1/matching", tags=["Matching"])

# Initialize matching service
matching_service = MatchingService(
    database_url=settings.database_url,
    openai_api_key=settings.openai_api_key
)


class MatchRequest(BaseModel):
    """Request body for matching endpoint"""
    buyer_prompt: str = Field(
        ...,
        description="Natural language description of buyer requirements",
        min_length=10,
        max_length=2000
    )
    top_k: int = Field(
        default=30,
        description="Number of candidates to consider (vector search)",
        ge=10,
        le=100
    )
    top_n: int = Field(
        default=10,
        description="Number of results to return",
        ge=1,
        le=50
    )


class BuyerStructure(BaseModel):
    """Parsed buyer requirements structure"""
    buyer_text: str
    labels_must: List[str]
    labels_nice: List[str]
    integration_required: List[str]
    integration_nice: List[str]
    constraints: Dict[str, Any]
    notes: str


class MatchResult(BaseModel):
    """Single matching result"""
    app_id: str
    name: str
    similarity_percent: int


class MatchResponse(BaseModel):
    """Response body for matching endpoint"""
    buyer_struct: BuyerStructure
    results: List[MatchResult]


@router.post("/match", response_model=MatchResponse, status_code=status.HTTP_200_OK)
async def match_applications(request: MatchRequest):
    """
    Match buyer requirements with applications in the marketplace.
    
    This endpoint:
    1. Parses natural language requirements using OpenAI
    2. Generates semantic embeddings
    3. Runs hybrid matching algorithm (vector similarity + features)
    4. Returns ranked list of matching applications
    
    Example request:
    ```json
    {
        "buyer_prompt": "Necesito un CRM que se integre con Stripe",
        "top_k": 30,
        "top_n": 10
    }
    ```
    
    Example response:
    ```json
    {
        "buyer_struct": {
            "buyer_text": "Necesito un CRM que se integre con Stripe",
            "labels_must": ["CRM"],
            "labels_nice": [],
            "integration_required": ["Stripe"],
            "integration_nice": [],
            "constraints": {"price_max": null},
            "notes": ""
        },
        "results": [
            {
                "app_id": "uuid-here",
                "name": "Example CRM",
                "similarity_percent": 85
            }
        ]
    }
    ```
    """
    try:
        result = await matching_service.match_buyer_to_apps(
            buyer_prompt=request.buyer_prompt,
            top_k=request.top_k,
            top_n=request.top_n
        )
        
        return result
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Matching failed: {str(e)}"
        )


@router.get("/health")
async def health_check():
    """Health check endpoint for matching service"""
    return {
        "status": "healthy",
        "service": "matching",
        "openai_configured": bool(settings.openai_api_key),
        "database_configured": bool(settings.database_url)
    }
