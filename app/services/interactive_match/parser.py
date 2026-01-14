"""
Interactive Match Parser
Multi-turn prompt parser with validation and missing requirements detection.
"""
import json
from typing import Optional, Tuple, List
from app.core.openai_client import client
from app.prompts.buyer_parser_prompts import LABEL_CATALOG, TAG_CATALOG
from app.schemas.interactive_match import ParsedPromptResult, PriorState, MissingRequirements
from app.services.validation_helpers import (
    validate_parsed_data,
    deduplicate_and_normalize_tags,
    deduplicate_list
)


TRANSLATION_SYSTEM_PROMPT = """You are a professional translator. Translate the user's text to English.

Rules:
- If the text is already in English, return it as-is
- Preserve technical terms, product names, and brand names
- Keep the meaning and intent intact
- Return ONLY the translated text, no explanations"""


EXTRACTION_SYSTEM_PROMPT = """You are a business application requirements extractor. Extract structured data from the user's English description.

CRITICAL RULES:
1. Return ONLY valid JSON. No markdown, no explanations.
2. Extract only what is clearly stated in the text.
3. Use proper capitalization for all extracted values.
4. Never duplicate items.

OUTPUT STRUCTURE:
{
  "labels": ["label1", "label2"],
  "tags": ["tag1", "tag2"],
  "integrations": ["Integration1", "Integration2"]
}

FIELD DEFINITIONS:
- labels: Business function labels. Choose ONLY from the allowed catalog provided.
- tags: Short descriptive tags (e.g., "SME", "Automation", "Switzerland"). Free-form strings.
- integrations: External platform/service names (e.g., "Stripe", "Shopify", "DATEV"). Free-form strings.

EXTRACTION GUIDELINES:
- labels: Must exist in the provided catalog. Extract up to 10 most relevant.
- tags: Extract 1-10 relevant tags. Keep them concise (1-3 words).
- integrations: Extract mentioned integrations. Normalize capitalization (Stripe, PayPal, etc.). Max 10.
- If nothing found for a category, use empty array []."""


def format_extraction_prompt(english_text: str) -> str:
    """Format user prompt for extraction"""
    return f"""Extract structured data from this business application requirement:

ALLOWED LABELS (choose ONLY from these):
{json.dumps(LABEL_CATALOG)}

ALLOWED TAGS (choose from these or create similar ones):
{json.dumps(TAG_CATALOG)}

USER TEXT:
{english_text}

Return ONLY the JSON object with labels, tags, and integrations arrays."""


async def translate_to_english(user_prompt: str) -> str:
    """
    Translate user prompt to English if needed.
    
    Args:
        user_prompt: User input in any language
        
    Returns:
        English text
    """
    try:
        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": TRANSLATION_SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.2,
            max_tokens=500
        )
        
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"Translation error: {e}. Using original text.")
        return user_prompt


async def extract_structured_data(english_text: str) -> dict:
    """
    Extract labels, tags, integrations from English text.
    
    Args:
        english_text: User requirement in English
        
    Returns:
        Dict with labels, tags, integrations arrays
    """
    user_prompt = format_extraction_prompt(english_text)
    
    try:
        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": EXTRACTION_SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.3,
            max_tokens=800,
            response_format={"type": "json_object"}
        )
        
        result = json.loads(response.choices[0].message.content)
        
        return {
            "labels": result.get("labels", []),
            "tags": result.get("tags", []),
            "integrations": result.get("integrations", [])
        }
    except Exception as e:
        print(f"Extraction error: {e}")
        return {
            "labels": [],
            "tags": [],
            "integrations": []
        }


def filter_labels_from_catalog(labels: list) -> list:
    """Filter labels to only include valid catalog items"""
    return [label for label in labels if label in LABEL_CATALOG]


def merge_with_prior_state(
    current_labels: list,
    current_tags: list,
    current_integrations: list,
    prior_state: Optional[PriorState]
) -> Tuple[List[str], List[str], List[str]]:
    """
    Merge current extraction with prior state.
    
    Args:
        current_labels: Newly extracted labels
        current_tags: Newly extracted tags
        current_integrations: Newly extracted integrations
        prior_state: Previous parsing state
        
    Returns:
        Tuple of (merged_labels, merged_tags, merged_integrations)
    """
    if not prior_state:
        return current_labels, current_tags, current_integrations
    
    merged_labels = deduplicate_list(prior_state.labels + current_labels)
    merged_tags = deduplicate_list(prior_state.tags + current_tags)
    merged_integrations = deduplicate_list(prior_state.integrations + current_integrations)
    
    return merged_labels, merged_tags, merged_integrations


async def parse_user_prompt(
    user_prompt: str,
    prior_state: Optional[PriorState] = None
) -> ParsedPromptResult:
    """
    Parse user prompt into structured data with validation.
    
    Args:
        user_prompt: Natural language requirement from user
        prior_state: Optional previous parsing state for multi-turn
        
    Returns:
        ParsedPromptResult with extracted data and validation status
    """
    english_text = await translate_to_english(user_prompt)
    
    extracted = await extract_structured_data(english_text)
    
    current_labels = filter_labels_from_catalog(extracted["labels"])
    current_tags = deduplicate_and_normalize_tags(extracted["tags"])
    current_integrations = deduplicate_list(extracted["integrations"][:10])
    
    merged_labels, merged_tags, merged_integrations = merge_with_prior_state(
        current_labels,
        current_tags,
        current_integrations,
        prior_state
    )
    
    is_valid, missing = validate_parsed_data(
        merged_labels,
        merged_tags,
        merged_integrations
    )
    
    return ParsedPromptResult(
        combined_prompt_english=english_text,
        labels=merged_labels,
        tags=merged_tags,
        integrations=merged_integrations,
        is_valid=is_valid,
        missing=missing
    )
