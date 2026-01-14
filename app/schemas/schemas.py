"""
Pydantic Schemas for API validation
"""
from pydantic import BaseModel, EmailStr, Field, field_serializer
from datetime import datetime
from typing import Optional, List, Any
from uuid import UUID


# User Schemas
class UserBase(BaseModel):
    """Base user schema"""
    email: EmailStr
    username: str = Field(..., min_length=3, max_length=50)


class UserCreate(UserBase):
    """Schema for creating a user"""
    password: str = Field(..., min_length=6)


class UserResponse(UserBase):
    """Schema for user response"""
    id: int
    is_active: bool
    created_at: datetime
    
    class Config:
        from_attributes = True


# Item Schemas
class ItemBase(BaseModel):
    """Base item schema"""
    title: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None


class ItemCreate(ItemBase):
    """Schema for creating an item"""
    pass


class ItemUpdate(BaseModel):
    """Schema for updating an item"""
    title: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = None
    is_active: Optional[bool] = None


class ItemResponse(ItemBase):
    """Schema for item response"""
    id: int
    is_active: bool
    created_at: datetime
    
    class Config:
        from_attributes = True


# Application Schemas
class ApplicationLinkResponse(BaseModel):
    """Schema for application link response"""
    id: UUID  # Accept UUID object, will be serialized to string
    name: str
    description: Optional[str] = None
    url: str
    image_url: Optional[str] = None
    price_text: Optional[str] = None
    stars: Optional[int] = 0  # default since not in DB
    tags: Any = []  # Accept AppTag objects, will be serialized to list of strings
    
    @field_serializer('id')
    def serialize_id(self, value: UUID) -> str:
        """Convert UUID to string for JSON response"""
        return str(value)
    
    @field_serializer('tags')
    def serialize_tags(self, value) -> List[str]:
        """Extract tag names from AppTag objects"""
        if not value:
            return []
        return [tag.tag for tag in value]
   
    
    class Config:
        from_attributes = True


# Generic Response Schemas
class MessageResponse(BaseModel):
    """Generic message response"""
    message: str


class HealthResponse(BaseModel):
    """Health check response"""
    status: str
    version: str
    database: str
