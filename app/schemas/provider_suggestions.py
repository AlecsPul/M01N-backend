"""
Provider Suggestions Schemas
Pydantic models for provider suggestion endpoints.
"""
from typing import Optional
from pydantic import BaseModel, Field
from uuid import UUID


class ProviderSuggestionResponse(BaseModel):
    """Response schema for provider suggestion endpoint"""
    card_id: UUID = Field(..., description="ID of the backlog card")
    company_name: str = Field(..., description="Name of the suggested company")
    company_url: str = Field(..., description="Main website URL of the company")
    marketplace_url: Optional[str] = Field(None, description="Direct link to the product/service offering (optional)")
    reasoning_brief: str = Field(..., description="Brief explanation of why this provider matches (max 60 words)")
    
    class Config:
        json_schema_extra = {
            "example": {
                "card_id": "123e4567-e89b-12d3-a456-426614174000",
                "company_name": "Stripe",
                "company_url": "https://stripe.com",
                "marketplace_url": "https://marketplace.stripe.com/apps/radar",
                "reasoning_brief": "Stripe offers comprehensive payment fraud detection through Radar, matching the backlog need for secure transaction monitoring. The solution is battle-tested, scalable, and integrates seamlessly with payment workflows."
            }
        }
