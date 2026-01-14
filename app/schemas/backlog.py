"""
Backlog API Schemas
Pydantic models for backlog endpoints.
"""
from pydantic import BaseModel, Field
from typing import Optional


class BacklogIngestRequest(BaseModel):
    """Request body for backlog ingest endpoint"""
    prompt_text: str = Field(
        ...,
        description="User's feature request or requirement",
        min_length=5,
        max_length=2000
    )
    comment_text: str = Field(
        default="",
        description="Optional additional comment or clarification",
        max_length=1000
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "prompt_text": "Necesito integrar Stripe con mi sistema CRM",
                "comment_text": "Es urgente para procesar pagos de clientes"
            }
        }


class BacklogIngestResponse(BaseModel):
    """Response body for backlog ingest endpoint (currently not used)"""
    card_id: str = Field(
        ...,
        description="ID of the card (existing or newly created)"
    )
    is_new: bool = Field(
        ...,
        description="Whether a new card was created (true) or matched existing (false)"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "card_id": "550e8400-e29b-41d4-a716-446655440000",
                "is_new": False
            }
        }
