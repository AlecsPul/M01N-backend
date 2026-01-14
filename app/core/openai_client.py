"""
OpenAI Client Configuration
"""
from openai import AsyncOpenAI
from app.core.config import settings

# Initialize OpenAI client
client = AsyncOpenAI(api_key=settings.openai_api_key)


async def get_chat_completion(
    messages: list,
    model: str = "gpt-4o-mini",
    temperature: float = 0.7,
    max_tokens: int = 1000
):
    """
    Get a chat completion from OpenAI
    
    Args:
        messages: List of message dicts with 'role' and 'content'
        model: Model to use (gpt-4o, gpt-4o-mini, gpt-3.5-turbo, etc.)
        temperature: Sampling temperature (0-2)
        max_tokens: Maximum tokens to generate
        
    Returns:
        str: The generated response
        
    Example:
        messages = [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "Hello!"}
        ]
        response = await get_chat_completion(messages)
    """
    try:
        response = await client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens
        )
        return response.choices[0].message.content
    except Exception as e:
        raise Exception(f"Error calling OpenAI API: {str(e)}")


async def get_embedding(text: str, model: str = "text-embedding-3-small"):
    """
    Get an embedding from OpenAI
    
    Args:
        text: Text to embed
        model: Embedding model to use
        
    Returns:
        list: The embedding vector
    """
    try:
        response = await client.embeddings.create(
            model=model,
            input=text
        )
        return response.data[0].embedding
    except Exception as e:
        raise Exception(f"Error getting embedding: {str(e)}")


async def create_image(
    prompt: str,
    size: str = "1024x1024",
    quality: str = "standard",
    n: int = 1
):
    """
    Generate an image with DALL-E
    
    Args:
        prompt: Description of the image
        size: Image size (1024x1024, 1792x1024, 1024x1792)
        quality: Image quality (standard, hd)
        n: Number of images to generate
        
    Returns:
        list: URLs of generated images
    """
    try:
        response = await client.images.generate(
            model="dall-e-3",
            prompt=prompt,
            size=size,
            quality=quality,
            n=n
        )
        return [image.url for image in response.data]
    except Exception as e:
        raise Exception(f"Error generating image: {str(e)}")


async def normalize_to_english(text: str) -> str:
    """
    Normalize text to English using translation if needed.
    If text is already in English, returns it unchanged.
    
    Args:
        text: Input text in any language
    
    Returns:
        Text in English
    """
    try:
        messages = [
            {
                "role": "system",
                "content": "You are a translation assistant. If the input text is not in English, translate it to English. If it is already in English, return it unchanged. Return ONLY the translated/original text, no explanations."
            },
            {
                "role": "user",
                "content": text
            }
        ]
        
        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            temperature=0.3,
            max_tokens=500
        )
        
        return response.choices[0].message.content.strip()
    
    except Exception as e:
        raise Exception(f"Error normalizing text to English: {str(e)}")
