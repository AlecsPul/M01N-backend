"""
Interactive Match Questioning
Question generation and session management for interactive matching.
"""
import json
import hashlib
from typing import Optional, Union
from pydantic import BaseModel, Field
from app.core.openai_client import client
from app.prompts.buyer_parser_prompts import LABEL_CATALOG
from app.services.interactive_match.parser import parse_user_prompt
from app.schemas.interactive_match import (
    PriorState,
    ParsedPromptResult,
    SessionState,
    AccumulatedData,
    Turn,
    MissingRequirements
)
from app.services.validation_helpers import validate_parsed_data
from app.services.session_manager import (
    create_turn,
    update_accumulated_data
)


def _stable_seed(text: str) -> int:
    """Generate deterministic seed from text using sha256"""
    return int(hashlib.sha256(text.encode('utf-8')).hexdigest()[:8], 16)


def _choose_variant(seed: int, variants: list) -> any:
    """Deterministically select variant based on seed"""
    return variants[seed % len(variants)]


# Integration examples variants
INTEGRATION_EXAMPLES_VARIANTS = [
    ["Stripe", "DATEV", "Shopify", "Zapier", "PayPal", "banks"],
    ["Salesforce", "QuickBooks", "Slack", "Google Workspace", "Microsoft Teams", "Mailchimp"],
    ["SAP", "HubSpot", "Xero", "Trello", "Asana", "Dropbox"],
    ["Zoho", "FreshBooks", "Monday.com", "Notion", "Airtable", "AWS"],
    ["Oracle", "Pipedrive", "Jira", "Confluence", "GitHub", "GitLab"]
]


# Tag context examples variants
TAG_CONTEXT_EXAMPLES_VARIANTS = [
    ["industry", "company size", "region", "business model"],
    ["sector", "team size", "location", "market segment"],
    ["vertical", "organization type", "country", "customer type"],
    ["domain", "company stage", "geography", "use case"]
]


class SessionQuestion(BaseModel):
    """Next question to ask the user"""
    question: str = Field(..., description="Question to ask user")
    state: SessionState = Field(..., description="Current session state")


class SessionComplete(BaseModel):
    """Session completed with valid requirements"""
    state: SessionState = Field(..., description="Final session state")
    is_complete: bool = Field(True, description="Always true for complete sessions")


SessionResult = Union[SessionQuestion, SessionComplete]


QUESTION_GENERATION_SYSTEM_PROMPT = """You are an assistant helping to clarify business software requirements.

Your task: Generate ONE targeted question to help the user specify missing information.

Rules:
- Ask in English, concise and direct
- Make the question natural and conversational
- Focus on extracting the specific missing information mentioned
- Don't ask multiple questions at once
- Output ONLY valid JSON: {"question": "your question here"}"""


async def generate_question_with_ai(
    missing: dict,
    accumulated: AccumulatedData
) -> str:
    """
    Generate a targeted question using OpenAI based on what's missing.
    
    Args:
        missing: Dict with labels_needed, tags_needed, integrations_needed
        accumulated: Current accumulated data
        
    Returns:
        Question string
    """
    labels_needed = missing.get("labels_needed", 0)
    tags_needed = missing.get("tags_needed", 0)
    integrations_needed = missing.get("integrations_needed", 0)
    
    # Generate seed from accumulated data to vary examples
    seed_text = f"{accumulated.labels}{accumulated.tags}{accumulated.integrations}"
    seed = _stable_seed(seed_text) if seed_text else 0
    
    if labels_needed > 0:
        # Vary which labels to show as examples
        start_idx = (seed % max(1, len(LABEL_CATALOG) - 8))
        sample_labels = LABEL_CATALOG[start_idx:start_idx + 8]
        if len(sample_labels) < 8:
            sample_labels = LABEL_CATALOG[:8]
        
        context = f"""The user needs {labels_needed} more functional labels for their business application.

Current labels: {accumulated.labels}

Available label options (sample): {sample_labels}

Generate a question asking what main functions/features they need. Mention 3-4 examples from the available labels but allow free text."""
    
    elif integrations_needed > 0:
        # Vary integration examples
        integration_examples = _choose_variant(seed, INTEGRATION_EXAMPLES_VARIANTS)
        examples_text = ", ".join(integration_examples)
        
        context = f"""The user needs to specify at least {integrations_needed} integration(s) with external tools/platforms.

Current integrations: {accumulated.integrations}

Generate a question asking which external services or platforms their application must integrate with. Mention common examples like {examples_text}."""
    
    elif tags_needed > 0:
        # Vary tag context examples
        tag_examples = _choose_variant(seed, TAG_CONTEXT_EXAMPLES_VARIANTS)
        examples_text = ", ".join(tag_examples)
        
        context = f"""The user needs {tags_needed} more tag(s) for business context.

Current tags: {accumulated.tags}

Generate a question asking about their business context - {examples_text}. Ask for short keywords."""
    
    else:
        return "Can you provide any additional details about your requirements?"
    
    try:
        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": QUESTION_GENERATION_SYSTEM_PROMPT},
                {"role": "user", "content": context}
            ],
            temperature=0.3,
            max_tokens=200,
            response_format={"type": "json_object"}
        )
        
        result = json.loads(response.choices[0].message.content)
        return result.get("question", "What other requirements do you have?")
    
    except Exception as e:
        print(f"Question generation error: {e}")
        # Fallback with varied examples
        if labels_needed > 0:
            start_idx = (seed % max(1, len(LABEL_CATALOG) - 4))
            sample = LABEL_CATALOG[start_idx:start_idx + 4]
            return f"What main functions do you need? (e.g., {', '.join(sample)})"
        elif integrations_needed > 0:
            integration_examples = _choose_variant(seed, INTEGRATION_EXAMPLES_VARIANTS)
            return f"Which external tools must it integrate with? (e.g., {', '.join(integration_examples[:3])})"
        else:
            tag_examples = _choose_variant(seed, TAG_CONTEXT_EXAMPLES_VARIANTS)
            return f"Can you describe your business context? (e.g., {', '.join(tag_examples[:3])})"


async def start_session(initial_prompt: str) -> SessionResult:
    """
    Start a new interactive matching session.
    
    Args:
        initial_prompt: User's initial requirement description
        
    Returns:
        SessionQuestion if more info needed, SessionComplete if already valid
    """
    parsed = await parse_user_prompt(initial_prompt, prior_state=None)
    
    accumulated = AccumulatedData(
        labels=parsed.labels,
        tags=parsed.tags,
        integrations=parsed.integrations
    )
    
    turn = create_turn(initial_prompt, parsed)
    
    state = SessionState(
        turns=[turn],
        accumulated=accumulated,
        missing=parsed.missing,
        is_valid=parsed.is_valid
    )
    
    if parsed.is_valid:
        return SessionComplete(state=state)
    
    question = await generate_question_with_ai(
        missing=parsed.missing.dict(),
        accumulated=accumulated
    )
    
    return SessionQuestion(question=question, state=state)


async def continue_session(
    state: SessionState,
    user_answer: str
) -> SessionResult:
    """
    Continue an existing session with user's answer.
    
    Args:
        state: Current session state
        user_answer: User's response to the previous question
        
    Returns:
        SessionQuestion if more info needed, SessionComplete if now valid
    """
    prior = PriorState(
        labels=state.accumulated.labels,
        tags=state.accumulated.tags,
        integrations=state.accumulated.integrations,
        combined_prompt_english=""
    )
    
    parsed = await parse_user_prompt(user_answer, prior_state=prior)
    
    accumulated = update_accumulated_data(state.accumulated, parsed)
    
    is_valid, missing = validate_parsed_data(
        accumulated.labels,
        accumulated.tags,
        accumulated.integrations
    )
    
    turn = create_turn(user_answer, parsed)
    
    updated_state = SessionState(
        turns=state.turns + [turn],
        accumulated=accumulated,
        missing=missing,
        is_valid=is_valid
    )
    
    if is_valid:
        return SessionComplete(state=updated_state)
    
    question = await generate_question_with_ai(
        missing=missing.dict(),
        accumulated=accumulated
    )
    
    return SessionQuestion(question=question, state=updated_state)


def is_session_complete(result: SessionResult) -> bool:
    """
    Check if session result is complete.
    
    Args:
        result: SessionResult (either question or complete)
        
    Returns:
        True if SessionComplete, False if SessionQuestion
    """
    return isinstance(result, SessionComplete)


def get_state(result: SessionResult) -> SessionState:
    """
    Extract state from session result.
    
    Args:
        result: SessionResult
        
    Returns:
        SessionState
    """
    return result.state


def get_question(result: SessionResult) -> Optional[str]:
    """
    Extract question from session result if available.
    
    Args:
        result: SessionResult
        
    Returns:
        Question string or None if complete
    """
    if isinstance(result, SessionQuestion):
        return result.question
    return None
