"""
OpenAI API Schemas
"""
from pydantic import BaseModel, Field
from typing import List, Optional, Literal


class Message(BaseModel):
    """Chat message schema"""
    role: Literal["system", "user", "assistant"]
    content: str


class ChatRequest(BaseModel):
    """Chat completion request schema"""
    messages: List[Message]
    model: str = Field(default="gpt-4o-mini", description="Model to use")
    temperature: float = Field(default=0.7, ge=0, le=2, description="Sampling temperature")
    max_tokens: int = Field(default=1000, gt=0, description="Maximum tokens to generate")


class ChatResponse(BaseModel):
    """Chat completion response schema"""
    response: str
    model: str
    tokens_used: Optional[int] = None


class EmbeddingRequest(BaseModel):
    """Embedding request schema"""
    text: str = Field(..., min_length=1)
    model: str = Field(default="text-embedding-3-small")


class EmbeddingResponse(BaseModel):
    """Embedding response schema"""
    embedding: List[float]
    model: str


class ImageGenerationRequest(BaseModel):
    """Image generation request schema"""
    prompt: str = Field(..., min_length=1, max_length=4000)
    size: Literal["1024x1024", "1792x1024", "1024x1792"] = "1024x1024"
    quality: Literal["standard", "hd"] = "standard"
    n: int = Field(default=1, ge=1, le=10)


class ImageGenerationResponse(BaseModel):
    """Image generation response schema"""
    urls: List[str]
    model: str = "dall-e-3"
