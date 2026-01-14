"""
Highlights Generation
Generate competitive advantages/highlights for applications using OpenAI.
"""
import json
import asyncio
from typing import List, Dict, Optional
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.openai_client import client
from app.services.comparison.repository import (
    get_app_by_name,
    get_features_text,
    get_fallback_data
)


HIGHLIGHTS_SYSTEM_PROMPT = """You are an expert at analyzing software product features and identifying key competitive advantages.

Given feature descriptions for a software application, extract EXACTLY 3 key highlights that represent its strongest competitive advantages.

Output MUST be valid JSON with this exact structure:
{
  "highlights": [
    {"title": "Short Feature Name", "detail": "Brief explanation of the benefit"},
    {"title": "Another Feature", "detail": "What makes this valuable"},
    ...exactly 3 items total...
  ]
}

CRITICAL RULES:
- Output EXACTLY 3 highlights, no more, no less
- Each title: max 8 words, clear and specific
- Each detail: max 30 words, focus on value/benefit
- Base highlights ONLY on actual features mentioned in the text
- Do NOT invent capabilities not explicitly stated
- Prioritize unique, differentiating features
- Output ONLY valid JSON, no explanations"""


HIGHLIGHTS_USER_PROMPT = """Analyze these application features and extract EXACTLY 3 key competitive highlights:

{features_text}

Return JSON only."""


FALLBACK_HIGHLIGHTS = [
    {
        "title": "Standard Functionality",
        "detail": "Provides core capabilities typical for applications in this category."
    },
    {
        "title": "Integration Support",
        "detail": "Offers integration capabilities with various third-party services and platforms."
    },
    {
        "title": "Scalable Solution",
        "detail": "Built to accommodate growing business needs and increasing usage demands."
    }
]


async def retry_openai_call(func, max_attempts: int = 2):
    """Retry OpenAI call with exponential backoff"""
    for attempt in range(max_attempts):
        try:
            return await func()
        except Exception as e:
            if attempt == max_attempts - 1:
                raise
            await asyncio.sleep(1.0 * (attempt + 1))


async def generate_highlights(features_text: str) -> List[Dict[str, str]]:
    """
    Generate exactly 3 highlights from features text using OpenAI.
    
    Args:
        features_text: Application features description
        
    Returns:
        List of 3 dicts with 'title' and 'detail' keys
        
    Raises:
        Exception if OpenAI call fails after retries
    """
    if not features_text or len(features_text.strip()) < 50:
        return FALLBACK_HIGHLIGHTS
    
    async def _call():
        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": HIGHLIGHTS_SYSTEM_PROMPT},
                {"role": "user", "content": HIGHLIGHTS_USER_PROMPT.format(
                    features_text=features_text[:4000]
                )}
            ],
            temperature=0.2,
            max_tokens=800,
            response_format={"type": "json_object"}
        )
        content = response.choices[0].message.content.strip()
        return json.loads(content)
    
    try:
        result = await retry_openai_call(_call, max_attempts=2)
        highlights = result.get("highlights", [])
        
        if len(highlights) != 3:
            print(f"Warning: Expected 3 highlights, got {len(highlights)}. Using fallback.")
            return FALLBACK_HIGHLIGHTS
        
        for highlight in highlights:
            if not isinstance(highlight, dict) or "title" not in highlight or "detail" not in highlight:
                print(f"Warning: Invalid highlight structure. Using fallback.")
                return FALLBACK_HIGHLIGHTS
        
        return highlights
        
    except Exception as e:
        print(f"Error generating highlights: {str(e)}")
        return FALLBACK_HIGHLIGHTS


async def generate_highlights_from_fallback(fallback_data: Dict) -> List[Dict[str, str]]:
    """
    Generate highlights from fallback data (labels, keys, tags).
    
    Args:
        fallback_data: Dict with labels, integration_keys, tags
        
    Returns:
        List of 3 highlight dicts
    """
    labels = fallback_data.get("labels", [])
    integration_keys = fallback_data.get("integration_keys", [])
    tags = fallback_data.get("tags", [])
    
    if not labels and not integration_keys and not tags:
        return FALLBACK_HIGHLIGHTS
    
    combined_text = f"""
    Categories: {', '.join(labels[:10])}
    Integrations: {', '.join(integration_keys[:10])}
    Tags: {', '.join(tags[:10])}
    """
    
    if len(combined_text.strip()) < 50:
        return FALLBACK_HIGHLIGHTS
    
    try:
        return await generate_highlights(combined_text)
    except:
        return FALLBACK_HIGHLIGHTS


async def get_highlights_for_company(db: AsyncSession, company_name: str) -> List[Dict[str, str]]:
    """
    Main function to get highlights for a company.
    
    Args:
        db: Database session
        company_name: Company name to lookup
        
    Returns:
        List of exactly 3 highlight dicts with 'title' and 'detail' keys
    """
    app_data = await get_app_by_name(db, company_name)
    
    if not app_data:
        print(f"Company '{company_name}' not found in database")
        return FALLBACK_HIGHLIGHTS
    
    app_id = app_data["app_id"]
    features_text = await get_features_text(db, app_id)
    
    if features_text and len(features_text.strip()) >= 50:
        return await generate_highlights(features_text)
    
    print(f"Features text unavailable for '{company_name}', trying fallback data")
    fallback_data = await get_fallback_data(db, app_id)
    
    return await generate_highlights_from_fallback(fallback_data)
