"""
Backlog Card Generation Module
Generates concise titles and descriptions for new backlog cards using OpenAI.
"""
import json
from typing import Tuple, List
from app.core.openai_client import client, normalize_to_english


SYSTEM_PROMPT = """You are a technical product manager creating backlog cards. Your task is to generate a concise title and description for a feature request card.

CRITICAL RULES:
1. Output ONLY valid JSON. No markdown, no explanations, no extra text.
2. Title MUST be under 10 words (strict limit).
3. Description MUST be under 600 words (strict limit).
4. Always output in English, regardless of input language.
5. Title should be clear, actionable, and specific.
6. Description should capture the core requirement, user need, and any important context.

OUTPUT FORMAT:
{
  "title": "string (max 10 words)",
  "description": "string (max 600 words)"
}

EXAMPLES:
Input: "Necesito integrar Stripe con mi CRM" / "Es urgente para mi empresa"
Output:
{
  "title": "Add Stripe payment integration to CRM",
  "description": "Integrate Stripe payment processing into the existing CRM system. This integration is urgent for business operations and should enable payment collection directly within the CRM workflow."
}

Input: "Need analytics dashboard" / "Want to track sales metrics"
Output:
{
  "title": "Build sales analytics dashboard",
  "description": "Create an analytics dashboard to track and visualize sales metrics. The dashboard should provide insights into sales performance and key business indicators."
}"""


async def generate_card_title_description(
    prompt_text: str,
    comment_text: str = ""
) -> Tuple[str, str]:
    """
    Generate a title and description for a backlog card using OpenAI.
    
    Args:
        prompt_text: Main prompt text (any language)
        comment_text: Optional comment/clarification (any language)
    
    Returns:
        Tuple of (title, description) both in English
    
    Raises:
        Exception: If generation fails after retries
    
    Example:
        title, desc = await generate_card_title_description(
            prompt_text="Necesito un CRM con Stripe",
            comment_text="Es urgente"
        )
        # Returns: ("Add Stripe CRM integration", "Integrate Stripe...")
    """
    combined_text = prompt_text.strip()
    if comment_text and comment_text.strip():
        combined_text += "\n" + comment_text.strip()
    
    normalized_text = await normalize_to_english(combined_text)
    
    user_prompt = f"""Generate a title and description for this feature request:

REQUEST:
{normalized_text}

Output the JSON now:"""
    
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_prompt}
    ]
    
    for attempt in range(3):
        try:
            response = await client.chat.completions.create(
                model="gpt-4o-mini",
                messages=messages,
                temperature=0.2,
                max_tokens=800,
                response_format={"type": "json_object"}
            )
            
            content = response.choices[0].message.content.strip()
            data = json.loads(content)
            
            title = data.get("title", "").strip()
            description = data.get("description", "").strip()
            
            is_valid, validation_error = validate_output(title, description)
            
            if is_valid:
                return (title, description)
            
            if attempt < 2:
                messages.append({"role": "assistant", "content": content})
                messages.append({
                    "role": "user",
                    "content": f"ERROR: {validation_error}. Please fix and output valid JSON again."
                })
                continue
            
            return apply_fallback(title, description, normalized_text)
        
        except json.JSONDecodeError as e:
            if attempt < 2:
                messages.append({
                    "role": "user",
                    "content": f"Invalid JSON: {str(e)}. Output valid JSON only."
                })
                continue
            
            return generate_fallback(normalized_text)
        
        except Exception as e:
            if attempt < 2:
                continue
            raise Exception(f"Failed to generate card after {attempt + 1} attempts: {str(e)}")
    
    return generate_fallback(normalized_text)


def validate_output(title: str, description: str) -> Tuple[bool, str]:
    """
    Validate generated title and description.
    
    Args:
        title: Generated title
        description: Generated description
    
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not title:
        return (False, "Title is empty")
    
    if not description:
        return (False, "Description is empty")
    
    title_words = len(title.split())
    if title_words > 10:
        return (False, f"Title has {title_words} words (max 10)")
    
    description_words = len(description.split())
    if description_words > 600:
        return (False, f"Description has {description_words} words (max 600)")
    
    return (True, "")


def apply_fallback(title: str, description: str, normalized_text: str) -> Tuple[str, str]:
    """
    Apply fallback fixes to invalid output.
    
    Args:
        title: Generated title (possibly invalid)
        description: Generated description (possibly invalid)
        normalized_text: Original normalized input text
    
    Returns:
        Tuple of (fixed_title, fixed_description)
    """
    if not title:
        title = "New feature request"
    
    title_words = title.split()
    if len(title_words) > 10:
        title = " ".join(title_words[:10])
    
    if not description:
        description = normalized_text[:600] if len(normalized_text) <= 600 else normalized_text[:597] + "..."
    else:
        description_words = description.split()
        if len(description_words) > 600:
            description = " ".join(description_words[:600])
    
    return (title, description)


def generate_fallback(normalized_text: str) -> Tuple[str, str]:
    """
    Generate conservative fallback title and description.
    
    Args:
        normalized_text: Normalized input text
    
    Returns:
        Tuple of (title, description)
    """
    first_line = normalized_text.split("\n")[0] if "\n" in normalized_text else normalized_text
    
    title_words = first_line.split()[:8]
    title = " ".join(title_words) + " request"
    
    if len(title.split()) > 10:
        title = " ".join(title.split()[:10])
    
    description = normalized_text
    if len(description.split()) > 600:
        description = " ".join(description.split()[:600])
    
    return (title, description)


async def generate_multiple_variants(
    prompt_text: str,
    comment_text: str = "",
    variants: int = 3
) -> List[Tuple[str, str]]:
    """
    Generate multiple title/description variants for selection.
    
    Args:
        prompt_text: Main prompt text
        comment_text: Optional comment
        variants: Number of variants to generate (default: 3)
    
    Returns:
        List of (title, description) tuples
    """
    results = []
    
    for _ in range(variants):
        try:
            title, description = await generate_card_title_description(
                prompt_text,
                comment_text
            )
            results.append((title, description))
        except Exception:
            continue
    
    if not results:
        combined = prompt_text + ("\n" + comment_text if comment_text else "")
        normalized = await normalize_to_english(combined)
        results.append(generate_fallback(normalized))
    
    return results
