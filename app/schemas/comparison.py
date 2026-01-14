"""
Comparison Schemas
Pydantic models for application comparison responses.
"""
from __future__ import annotations
from typing import List, Literal
from pydantic import BaseModel, Field, field_validator


class ComparisonRequest(BaseModel):
    """Request body for comparing two applications"""
    company_a: str = Field(..., min_length=1, description="First company name")
    company_b: str = Field(..., min_length=1, description="Second company name")
    
    @field_validator('company_a', 'company_b')
    @classmethod
    def strip_whitespace(cls, v: str) -> str:
        return v.strip()


class Highlight(BaseModel):
    """Single highlight/competitive advantage"""
    title: str = Field(..., max_length=100, description="Highlight title (max 8 words)")
    detail: str = Field(..., max_length=300, description="Highlight detail (max 30 words)")


class AttributeItem(BaseModel):
    """Attribute with ownership flag"""
    type: Literal["label", "integration", "tag"] = Field(..., description="Type of attribute")
    value: str = Field(..., description="Attribute value")
    has: bool = Field(..., description="Whether this application has this attribute")


class ApplicationComparison(BaseModel):
    """Application data for comparison"""
    name: str = Field(..., description="Application name")
    attributes: List[AttributeItem] = Field(..., description="All attributes with has flags")
    highlights: List[Highlight] = Field(..., description="Exactly 3 competitive highlights")
    
    class Config:
        json_schema_extra = {
            "example": {
                "name": "Stripe",
                "attributes": [
                    {"type": "integration", "value": "Shopify", "has": True},
                    {"type": "label", "value": "Payment Processing", "has": True},
                    {"type": "tag", "value": "fintech", "has": False}
                ],
                "highlights": [
                    {"title": "Global Payment Processing", "detail": "Accept payments in 135+ currencies with local payment methods worldwide"},
                    {"title": "Advanced Fraud Detection", "detail": "Machine learning-powered Radar blocks fraudulent transactions automatically"},
                    {"title": "Developer-Friendly APIs", "detail": "Comprehensive RESTful APIs with extensive documentation and SDKs"}
                ]
            }
        }


class ComparisonResponse(BaseModel):
    """Response containing comparison for two applications"""
    company_a: ApplicationComparison = Field(..., description="First application comparison")
    company_b: ApplicationComparison = Field(..., description="Second application comparison")

