"""
OpenAI API Routes
"""
from fastapi import APIRouter, HTTPException, status
from app.openai_client import get_chat_completion, get_embedding, create_image
from app.schemas.openai_schemas import (
    ChatRequest,
    ChatResponse,
    EmbeddingRequest,
    EmbeddingResponse,
    ImageGenerationRequest,
    ImageGenerationResponse
)

router = APIRouter(prefix="/api/v1/ai", tags=["OpenAI"])


@router.post("/chat", response_model=ChatResponse)
async def chat_completion(request: ChatRequest):
    """
    Get a chat completion from OpenAI
    
    Example request:
    ```json
    {
        "messages": [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "Hello!"}
        ],
        "model": "gpt-4o-mini",
        "temperature": 0.7,
        "max_tokens": 1000
    }
    ```
    """
    try:
        messages = [msg.model_dump() for msg in request.messages]
        response = await get_chat_completion(
            messages=messages,
            model=request.model,
            temperature=request.temperature,
            max_tokens=request.max_tokens
        )
        
        return ChatResponse(
            response=response,
            model=request.model
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.post("/embedding", response_model=EmbeddingResponse)
async def get_text_embedding(request: EmbeddingRequest):
    """
    Get an embedding vector for a text
    
    Example request:
    ```json
    {
        "text": "Hello world",
        "model": "text-embedding-3-small"
    }
    ```
    """
    try:
        embedding = await get_embedding(
            text=request.text,
            model=request.model
        )
        
        return EmbeddingResponse(
            embedding=embedding,
            model=request.model
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.post("/image", response_model=ImageGenerationResponse)
async def generate_image(request: ImageGenerationRequest):
    """
    Generate an image with DALL-E 3
    
    Example request:
    ```json
    {
        "prompt": "A beautiful sunset over the ocean",
        "size": "1024x1024",
        "quality": "standard",
        "n": 1
    }
    ```
    """
    try:
        urls = await create_image(
            prompt=request.prompt,
            size=request.size,
            quality=request.quality,
            n=request.n
        )
        
        return ImageGenerationResponse(urls=urls)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )
